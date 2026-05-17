"""CLI entry point for the Chronos ingest tick.

Run as `python -m chronos_ingest` or `chronos-ingest tick` from cron.

One tick:
  1. List the Nextcloud inbox.
  2. For each new file:
     a. Upsert as pending in SQLite.
     b. Download to a scratch dir.
     c. Scan (ClamAV + sanitise PDFs/images).
     d. If unsafe → move to NC quarantine + mark quarantined.
     e. Extract text/metadata.
     f. Budget-gated Haiku classification.
     g. Create an OCS public-read share link.
     h. Insert links, summary, share URL.
     i. Move file in NC to _processed/.
     j. Mark processed (needs_review if any links below auto-threshold).

The tick is idempotent: if it dies mid-file, the next run resumes from
`status='pending'`. Re-running won't duplicate links thanks to the
(entry_id, file_id) unique constraint.
"""

from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from pathlib import Path

from chronos_ingest import budget, classify, db, extract, scan
from chronos_ingest.config import Settings, get_settings
from chronos_ingest.nextcloud import NextcloudClient, classify_filetype


log = logging.getLogger("chronos_ingest")


# Approx upper bound for a single classification call: 6k input + 1k output
# at Haiku rates. Used as a budget-check estimate before each call.
ESTIMATED_CALL_COST_USD = 0.01


# ── Per-file processing ────────────────────────────────────────────────


def process_one_file(
    *,
    settings: Settings,
    nc: NextcloudClient,
    anthropic_client: object | None,
    remote_path: str,
    name: str,
    size: int,
    scratch_dir: Path,
) -> str:
    """Returns a short status string for logging: 'processed', 'quarantined', 'failed', 'skipped'."""
    file_type = classify_filetype(name)
    if file_type is None:
        log.info("skipping unsupported type: %s", name)
        return "skipped"

    with db.connect(settings.sqlite_path) as conn:
        with db.transaction(conn):
            file_id = db.upsert_file_pending(
                conn,
                nextcloud_path=remote_path,
                file_type=file_type,
                title=Path(name).stem,
                size_bytes=size,
            )

    local = scratch_dir / name
    try:
        nc.download_to_path(remote_path, local)
    except Exception as e:  # noqa: BLE001
        log.exception("download failed for %s", remote_path)
        with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
            db.fail_file(conn, file_id=file_id, error_message=f"download: {e}")
        return "failed"

    # Scan + sanitise.
    sresult = scan.scan_file(local, clamav_socket=settings.clamav_socket)
    with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
        db.update_scan(
            conn,
            file_id=file_id,
            scan_result=sresult.result,
            scan_signatures=",".join(sresult.signatures) or None,
        )

    if not sresult.is_clean:
        # Move to quarantine and stop.
        try:
            dest = f"{settings.nextcloud_quarantine_path.rstrip('/')}/{name}"
            nc.move(remote_path, dest, overwrite=True)
        except Exception:  # noqa: BLE001
            log.exception("could not move %s to quarantine", remote_path)
        with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
            db.quarantine_file(conn, file_id=file_id, error_message=sresult.notes)
        log.warning("quarantined: %s (%s)", remote_path, sresult.result)
        return "quarantined"

    # Extract.
    eresult = extract.extract(local, file_type=file_type)
    with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
        db.update_extract(
            conn,
            file_id=file_id,
            extracted_text=eresult.text,
            duration_seconds=eresult.duration_seconds,
        )

    # Classify (budget-gated; absent client → skip, leave pending).
    if anthropic_client is None:
        log.info("no anthropic client configured; leaving %s pending", remote_path)
        return "skipped"
    if not budget.may_call(
        settings.sqlite_path, ESTIMATED_CALL_COST_USD, settings.daily_haiku_budget_usd
    ):
        log.warning("daily budget hit — pausing ingest for today")
        return "skipped"

    with db.connect(settings.sqlite_path) as conn:
        entries = db.list_entries_minimal(conn)

    try:
        result = classify.classify_file(
            anthropic_client=anthropic_client,
            model=settings.anthropic_model,
            title=Path(name).stem,
            file_type=file_type,
            size_bytes=size,
            extracted_text=eresult.text,
            filename=name,
            entries=entries,
        )
    except Exception as e:  # noqa: BLE001
        log.exception("classify failed for %s", remote_path)
        with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
            db.fail_file(conn, file_id=file_id, error_message=f"classify: {e}")
        return "failed"

    budget.record(
        settings.sqlite_path,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=result.cost_usd,
    )

    # If moderation flagged it, quarantine it (defence in depth — clean
    # bits but unsuitable content).
    if result.moderation_flag:
        try:
            dest = f"{settings.nextcloud_quarantine_path.rstrip('/')}/{name}"
            nc.move(remote_path, dest, overwrite=True)
        except Exception:  # noqa: BLE001
            log.exception("could not move %s to quarantine (moderation)", remote_path)
        with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
            db.update_classification(
                conn,
                file_id=file_id,
                ai_summary_en=result.summary_en,
                cc_cycle=result.cc_cycle,
                cc_week=result.cc_week,
                age_min=result.age_min,
                age_max=result.age_max,
                moderation_flag=1,
                public_url=None,
            )
            db.quarantine_file(conn, file_id=file_id, error_message="moderation flag")
        log.warning("quarantined (moderation): %s", remote_path)
        return "quarantined"

    # Create a read-only share link AFTER we know the file is staying.
    public_url: str | None = None
    try:
        public_url = nc.create_public_share(remote_path)
    except Exception:  # noqa: BLE001
        log.exception("share-link creation failed for %s", remote_path)

    # Map entry slug → id for link rows.
    needs_review_any = False
    with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
        db.update_classification(
            conn,
            file_id=file_id,
            ai_summary_en=result.summary_en,
            cc_cycle=result.cc_cycle,
            cc_week=result.cc_week,
            age_min=result.age_min,
            age_max=result.age_max,
            moderation_flag=0,
            public_url=public_url,
        )
        for sugg in result.links:
            entry_id = db.get_entry_id_by_slug(conn, sugg.entry_slug)
            if entry_id is None:
                continue
            needs_review = sugg.needs_review
            needs_review_any = needs_review_any or needs_review
            db.upsert_link(
                conn,
                entry_id=entry_id,
                file_id=file_id,
                confidence=sugg.confidence,
                source="auto",
                reason=sugg.reason,
                needs_review=needs_review,
            )

    # Move file to _processed/ in Nextcloud.
    try:
        dest = f"{settings.nextcloud_processed_path.rstrip('/')}/{name}"
        nc.move(remote_path, dest, overwrite=True)
    except Exception:  # noqa: BLE001
        log.exception("could not move %s to processed", remote_path)

    with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
        db.mark_processed(conn, file_id=file_id, needs_review=needs_review_any)

    log.info(
        "processed: %s (%d links, %s)",
        remote_path,
        len(result.links),
        "review needed" if needs_review_any else "auto",
    )
    return "processed"


# ── Tick orchestration ────────────────────────────────────────────────


def run_tick(settings: Settings, *, anthropic_client: object | None = None) -> dict[str, int]:
    """Single ingest tick. Returns a per-status count."""
    counts: dict[str, int] = {
        "processed": 0,
        "quarantined": 0,
        "failed": 0,
        "skipped": 0,
    }
    with (
        NextcloudClient(
            base_url=settings.nextcloud_url,
            username=settings.nextcloud_user,
            app_password=settings.nextcloud_app_password,
        ) as nc,
        tempfile.TemporaryDirectory(prefix="chronos-ingest-") as tmp,
    ):
        scratch = Path(tmp)
        try:
            files = nc.list_dir(settings.nextcloud_inbox_path)
        except Exception:  # noqa: BLE001
            log.exception("inbox listing failed")
            return counts

        for f in files:
            try:
                status = process_one_file(
                    settings=settings,
                    nc=nc,
                    anthropic_client=anthropic_client,
                    remote_path=f.path,
                    name=f.name,
                    size=f.size,
                    scratch_dir=scratch,
                )
            except Exception as e:  # noqa: BLE001
                log.exception("unhandled error processing %s", f.path)
                with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
                    db.record_failed_import(
                        conn,
                        nextcloud_path=f.path,
                        error_message=f"{type(e).__name__}: {e}",
                    )
                counts["failed"] += 1
                continue
            counts[status] = counts.get(status, 0) + 1
    return counts


def _build_anthropic_client(settings: Settings) -> object | None:
    """Returns an Anthropic SDK client, or None if no key is set.

    Imported lazily so the binary can run on hosts without the SDK
    (e.g. for `--list-only`).
    """
    if not settings.anthropic_api_key:
        return None
    try:
        from anthropic import Anthropic  # type: ignore[import-not-found]
    except ImportError:
        log.error("anthropic SDK not installed but ANTHROPIC_API_KEY set")
        return None
    return Anthropic(api_key=settings.anthropic_api_key)


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chronos-ingest")
    parser.add_argument(
        "command", choices=["tick", "list"], help="tick=process inbox, list=preview inbox"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    settings = get_settings()

    if args.command == "list":
        with NextcloudClient(
            base_url=settings.nextcloud_url,
            username=settings.nextcloud_user,
            app_password=settings.nextcloud_app_password,
        ) as nc:
            files = nc.list_dir(settings.nextcloud_inbox_path)
            for f in files:
                print(f"{f.path}\t{f.size}\t{f.content_type}")
        return 0

    counts = run_tick(settings, anthropic_client=_build_anthropic_client(settings))
    log.info("tick complete: %s", counts)
    return 0


if __name__ == "__main__":
    sys.exit(cli())
