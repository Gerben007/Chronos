"""CLI entry point for the Chronos ingest tick.

Run as `python -m chronos_ingest tick` from cron.

Layout: files live in `NEXTCLOUD_ROOT_PATH` (default `/Chronos`) in a
folder tree like:

    Chronos/
      Cycle 1/
        1. Foundations (Grammar Stage)/
          Week 5/
            abraham.pdf
      Cycle 2/
        2. Essentials (Dialectic Stage)/
          Week 3/
            ...

Files stay where they are. The DB tracks state. A re-run skips files
already processed/quarantined; only `status='pending'` (or unknown
paths) get worked on. Cycle / stage / week are derived from the folder
path and supplied to the classifier as authoritative hints.

One tick:
  1. Recursive PROPFIND under the root.
  2. For every new file:
     a. Upsert as pending in SQLite.
     b. Download to scratch.
     c. Scan + sanitise (ClamAV + pikepdf + Pillow).
     d. Unsafe → mark quarantined in DB; file stays in place.
     e. Extract text/metadata.
     f. Budget-gated Haiku classification.
     g. Create OCS public read-only share link.
     h. Record summary + cc_cycle/week + age + links.
     i. Mark processed (needs_review if any link below 0.7 confidence).
"""

from __future__ import annotations

import argparse
import logging
import sys
import tempfile
import time
from pathlib import Path

from chronos_ingest import budget, classify, db, extract, rebuild, scan
from chronos_ingest.config import Settings, get_settings
from chronos_ingest.nextcloud import (
    NextcloudClient,
    classify_filetype,
    parse_path_metadata,
)


log = logging.getLogger("chronos_ingest")


# Approx upper bound for a single classification call.
ESTIMATED_CALL_COST_USD = 0.01


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
    """Returns: 'processed' | 'quarantined' | 'failed' | 'skipped'."""
    file_type = classify_filetype(name)
    if file_type is None:
        log.info("skipping unsupported type: %s", remote_path)
        return "skipped"

    # Idempotency: if we already have a terminal status for this path, skip.
    with db.connect(settings.sqlite_path) as conn:
        existing = db.get_file_by_path(conn, remote_path)
    if existing is not None and existing.status in (
        "processed", "needs_review", "quarantined", "failed"
    ):
        return "skipped"

    # Stage 0: upsert as pending so a death in mid-tick is recoverable.
    with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
        file_id = db.upsert_file_pending(
            conn,
            nextcloud_path=remote_path,
            file_type=file_type,
            title=Path(name).stem,
            size_bytes=size,
        )

    meta = parse_path_metadata(remote_path)

    local = scratch_dir / name
    try:
        nc.download_to_path(remote_path, local)
    except Exception as e:  # noqa: BLE001
        log.exception("download failed for %s", remote_path)
        with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
            db.fail_file(conn, file_id=file_id, error_message=f"download: {e}")
        return "failed"

    # Stage 1: scan + sanitise.
    sresult = scan.scan_file(
        local,
        clamav_socket=settings.clamav_socket,
        skip=settings.skip_virus_scan,
    )
    with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
        db.update_scan(
            conn,
            file_id=file_id,
            scan_result=sresult.result,
            scan_signatures=",".join(sresult.signatures) or None,
        )
    if not sresult.is_clean:
        with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
            db.quarantine_file(conn, file_id=file_id, error_message=sresult.notes)
        log.warning("quarantined: %s (%s)", remote_path, sresult.result)
        return "quarantined"

    # Stage 2: extract.
    eresult = extract.extract(local, file_type=file_type)
    with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
        db.update_extract(
            conn,
            file_id=file_id,
            extracted_text=eresult.text,
            duration_seconds=eresult.duration_seconds,
        )

    # Stage 3: classify (budget-gated).
    if anthropic_client is None:
        log.info("no anthropic client; leaving %s pending", remote_path)
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
            path_cycle=meta.cycle,
            path_stage=meta.stage,
            path_week=meta.week,
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

    # Stage 4: moderation gate.
    if result.moderation_flag:
        with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
            # Path-derived metadata still beats Haiku's if both present.
            db.update_classification(
                conn,
                file_id=file_id,
                ai_summary_en=result.summary_en,
                cc_cycle=meta.cycle or result.cc_cycle,
                cc_week=meta.week or result.cc_week,
                age_min=result.age_min,
                age_max=result.age_max,
                moderation_flag=1,
                public_url=None,
            )
            db.quarantine_file(conn, file_id=file_id, error_message="moderation flag")
        log.warning("quarantined (moderation): %s", remote_path)
        return "quarantined"

    # Stage 5: create the public share link.
    public_url: str | None = None
    try:
        public_url = nc.create_public_share(remote_path)
    except Exception:  # noqa: BLE001
        log.exception("share-link creation failed for %s", remote_path)

    needs_review_any = False
    with db.connect(settings.sqlite_path) as conn, db.transaction(conn):
        db.update_classification(
            conn,
            file_id=file_id,
            ai_summary_en=result.summary_en,
            cc_cycle=meta.cycle or result.cc_cycle,
            cc_week=meta.week or result.cc_week,
            age_min=result.age_min,
            age_max=result.age_max,
            moderation_flag=0,
            public_url=public_url,
        )
        for sugg in result.links:
            entry_id = db.get_entry_id_by_slug(conn, sugg.entry_slug)
            if entry_id is None:
                continue
            review = sugg.needs_review
            needs_review_any = needs_review_any or review
            db.upsert_link(
                conn,
                entry_id=entry_id,
                file_id=file_id,
                confidence=sugg.confidence,
                source="auto",
                reason=sugg.reason,
                needs_review=review,
            )
        db.mark_processed(conn, file_id=file_id, needs_review=needs_review_any)

    log.info(
        "processed: %s (links=%d, %s)",
        remote_path,
        len(result.links),
        "review" if needs_review_any else "auto",
    )
    return "processed"


def run_tick(settings: Settings, *, anthropic_client: object | None = None) -> dict[str, int]:
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
            files = nc.list_tree(settings.nextcloud_root_path)
        except Exception:  # noqa: BLE001
            log.exception("tree listing failed for %s", settings.nextcloud_root_path)
            return counts

        log.info("found %d files under %s", len(files), settings.nextcloud_root_path)
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


def _maybe_rebuild_resources(settings: Settings, processed_count: int) -> None:
    """Re-exports resources.json if the tick processed at least one file."""
    if processed_count <= 0:
        return
    try:
        data = rebuild.export_resources(settings.sqlite_path)
        out = settings.resources_output_path
        out.parent.mkdir(parents=True, exist_ok=True)
        import json as _json
        out.write_text(_json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        total = sum(len(v) for v in data.values())
        log.info("rebuild: %d resources across %d entries → %s", total, len(data), out)
    except Exception:  # noqa: BLE001
        log.exception("rebuild step failed")


def run_loop(settings: Settings, *, anthropic_client: object | None = None) -> None:
    """Forever-loop: tick, rebuild, sleep. Designed to be the container's PID 1.

    No signal handling — letting docker stop send SIGTERM is enough; the loop
    interrupts at the next sleep boundary.
    """
    interval = max(60, int(settings.tick_interval_seconds))
    log.info("loop mode starting (interval=%ds)", interval)
    while True:
        try:
            counts = run_tick(settings, anthropic_client=anthropic_client)
            log.info("tick complete: %s", counts)
            _maybe_rebuild_resources(settings, counts.get("processed", 0))
        except Exception:  # noqa: BLE001
            log.exception("tick failed; will retry next interval")
        time.sleep(interval)


def _build_anthropic_client(settings: Settings) -> object | None:
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
        "command",
        choices=["tick", "loop", "list"],
        help="tick=single pass; loop=forever poll; list=preview tree",
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
            files = nc.list_tree(settings.nextcloud_root_path)
            for f in files:
                meta = parse_path_metadata(f.path)
                hint = f"cycle={meta.cycle} stage={meta.stage} week={meta.week}"
                print(f"{f.path}\t{f.size}\t{hint}")
        return 0

    client = _build_anthropic_client(settings)
    if args.command == "loop":
        run_loop(settings, anthropic_client=client)
        return 0

    counts = run_tick(settings, anthropic_client=client)
    log.info("tick complete: %s", counts)
    _maybe_rebuild_resources(settings, counts.get("processed", 0))
    return 0


if __name__ == "__main__":
    sys.exit(cli())
