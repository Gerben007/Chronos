"""SQLite writer for the Chronos ingest pipeline.

The web container reads the same DB read-only; this module is the *only*
writer. Every query is parameterised (no string concat); every file
operation runs in a single transaction; upserts key on `nextcloud_path`
so a retried tick never duplicates rows.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


# ── Connection ─────────────────────────────────────────────────────────


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Opens a connection in WAL mode with foreign keys enforced.

    The DB file must already exist (run migrations first).
    """
    c = sqlite3.connect(db_path, isolation_level=None)
    c.row_factory = sqlite3.Row
    try:
        c.execute("PRAGMA journal_mode = WAL;")
        c.execute("PRAGMA foreign_keys = ON;")
        c.execute("PRAGMA synchronous = NORMAL;")
        yield c
    finally:
        c.close()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """BEGIN/COMMIT wrapper; rolls back on exception."""
    conn.execute("BEGIN")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def _now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S")


# ── Files ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FileRow:
    id: int
    nextcloud_path: str
    file_type: str
    title: str
    status: str
    public_url: str | None
    size_bytes: int | None
    extracted_text: str | None
    ai_summary_en: str | None
    ai_summary_af: str | None
    cc_cycle: int | None
    cc_week: int | None
    scan_result: str | None
    moderation_flag: int


def upsert_file_pending(
    conn: sqlite3.Connection,
    *,
    nextcloud_path: str,
    file_type: str,
    title: str,
    size_bytes: int | None = None,
) -> int:
    """Inserts (or no-ops) a file row in `pending` state.

    Idempotent on `nextcloud_path` — a retried tick returns the existing id.
    Returns the file id.
    """
    row = conn.execute(
        "SELECT id FROM files WHERE nextcloud_path = ?",
        (nextcloud_path,),
    ).fetchone()
    if row is not None:
        return int(row["id"])
    cur = conn.execute(
        """
        INSERT INTO files (nextcloud_path, file_type, title, size_bytes, status)
        VALUES (?, ?, ?, ?, 'pending')
        """,
        (nextcloud_path, file_type, title, size_bytes),
    )
    return int(cur.lastrowid)


def get_file_by_path(conn: sqlite3.Connection, nextcloud_path: str) -> FileRow | None:
    row = conn.execute(
        "SELECT * FROM files WHERE nextcloud_path = ?",
        (nextcloud_path,),
    ).fetchone()
    return _file_row(row) if row else None


def list_pending(conn: sqlite3.Connection, limit: int = 50) -> list[FileRow]:
    rows = conn.execute(
        "SELECT * FROM files WHERE status = 'pending' ORDER BY id LIMIT ?",
        (limit,),
    ).fetchall()
    return [_file_row(r) for r in rows]


def update_scan(
    conn: sqlite3.Connection,
    *,
    file_id: int,
    scan_result: str,
    scan_signatures: str | None,
) -> None:
    conn.execute(
        "UPDATE files SET scan_result = ?, scan_signatures = ? WHERE id = ?",
        (scan_result, scan_signatures, file_id),
    )


def quarantine_file(
    conn: sqlite3.Connection,
    *,
    file_id: int,
    error_message: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE files
        SET status = 'quarantined',
            processed_at = ?,
            error_message = ?
        WHERE id = ?
        """,
        (_now(), error_message, file_id),
    )


def fail_file(
    conn: sqlite3.Connection,
    *,
    file_id: int,
    error_message: str,
) -> None:
    conn.execute(
        """
        UPDATE files
        SET status = 'failed',
            processed_at = ?,
            error_message = ?
        WHERE id = ?
        """,
        (_now(), error_message, file_id),
    )


def update_extract(
    conn: sqlite3.Connection,
    *,
    file_id: int,
    extracted_text: str | None,
    duration_seconds: int | None = None,
) -> None:
    conn.execute(
        "UPDATE files SET extracted_text = ?, duration_seconds = ? WHERE id = ?",
        (extracted_text, duration_seconds, file_id),
    )


def update_classification(
    conn: sqlite3.Connection,
    *,
    file_id: int,
    ai_summary_en: str | None,
    cc_cycle: int | None,
    cc_week: int | None,
    age_min: int | None,
    age_max: int | None,
    moderation_flag: int,
    public_url: str | None,
) -> None:
    """Writes Haiku classification output back to the file row."""
    conn.execute(
        """
        UPDATE files
        SET ai_summary_en = ?,
            cc_cycle = ?,
            cc_week = ?,
            age_min = ?,
            age_max = ?,
            moderation_flag = ?,
            public_url = ?
        WHERE id = ?
        """,
        (
            ai_summary_en,
            cc_cycle,
            cc_week,
            age_min,
            age_max,
            moderation_flag,
            public_url,
            file_id,
        ),
    )


def mark_processed(
    conn: sqlite3.Connection,
    *,
    file_id: int,
    needs_review: bool = False,
) -> None:
    status = "needs_review" if needs_review else "processed"
    conn.execute(
        "UPDATE files SET status = ?, processed_at = ? WHERE id = ?",
        (status, _now(), file_id),
    )


# ── Links (file ↔ entry) ───────────────────────────────────────────────


def upsert_link(
    conn: sqlite3.Connection,
    *,
    entry_id: int,
    file_id: int,
    confidence: float,
    source: str,
    reason: str | None,
    needs_review: bool,
) -> int:
    """Idempotent on (entry_id, file_id). Updates confidence/reason on conflict."""
    row = conn.execute(
        "SELECT id FROM links WHERE entry_id = ? AND file_id = ?",
        (entry_id, file_id),
    ).fetchone()
    if row is not None:
        conn.execute(
            """
            UPDATE links
            SET confidence = ?, source = ?, reason = ?, needs_review = ?
            WHERE id = ?
            """,
            (confidence, source, reason, 1 if needs_review else 0, row["id"]),
        )
        return int(row["id"])
    cur = conn.execute(
        """
        INSERT INTO links (entry_id, file_id, confidence, source, reason, needs_review)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (entry_id, file_id, confidence, source, reason, 1 if needs_review else 0),
    )
    return int(cur.lastrowid)


def confirm_link(
    conn: sqlite3.Connection,
    *,
    link_id: int,
    confirmed_by: str,
) -> None:
    conn.execute(
        """
        UPDATE links
        SET needs_review = 0,
            confirmed_at = ?,
            confirmed_by = ?
        WHERE id = ?
        """,
        (_now(), confirmed_by, link_id),
    )


def reject_link(conn: sqlite3.Connection, *, link_id: int) -> None:
    conn.execute("DELETE FROM links WHERE id = ?", (link_id,))


# ── Entries (read-only here) ───────────────────────────────────────────


def list_entries_minimal(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Compact list used as Haiku classification context.

    Returns slug, id, English title, start/end year, lane slug, type.
    """
    rows = conn.execute(
        """
        SELECT e.id, e.slug, e.type, e.start_year, e.end_year,
               t.title AS title_en,
               l.slug  AS lane_slug
        FROM entries e
        JOIN entry_translations t
          ON t.entry_id = e.id AND t.lang = 'en'
        JOIN lanes l
          ON l.id = e.lane_id
        ORDER BY e.start_year
        """
    ).fetchall()
    return [dict(r) for r in rows]


def get_entry_id_by_slug(conn: sqlite3.Connection, slug: str) -> int | None:
    row = conn.execute("SELECT id FROM entries WHERE slug = ?", (slug,)).fetchone()
    return int(row["id"]) if row else None


# ── Translations (AI draft) ────────────────────────────────────────────


def upsert_ai_draft_translation(
    conn: sqlite3.Connection,
    *,
    entry_id: int,
    lang: str,
    title: str,
    summary: str,
    wiki_md: str | None,
    source_lang: str,
) -> None:
    """Inserts or overwrites an AI-drafted translation row.

    Existing 'reviewed' or 'published' rows are NOT overwritten — admin
    work is sacred.
    """
    row = conn.execute(
        """
        SELECT translation_status
        FROM entry_translations
        WHERE entry_id = ? AND lang = ?
        """,
        (entry_id, lang),
    ).fetchone()
    if row and row["translation_status"] in ("reviewed", "published"):
        return
    conn.execute(
        """
        INSERT INTO entry_translations
            (entry_id, lang, title, summary, wiki_md,
             translation_status, source_lang, ai_draft_at)
        VALUES (?, ?, ?, ?, ?, 'ai_draft', ?, ?)
        ON CONFLICT(entry_id, lang) DO UPDATE SET
            title = excluded.title,
            summary = excluded.summary,
            wiki_md = excluded.wiki_md,
            translation_status = 'ai_draft',
            source_lang = excluded.source_lang,
            ai_draft_at = excluded.ai_draft_at
        """,
        (entry_id, lang, title, summary, wiki_md, source_lang, _now()),
    )


def list_translations_for_review(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT t.entry_id, t.lang, t.title, t.summary, t.wiki_md,
               t.translation_status, t.source_lang, t.ai_draft_at,
               e.slug
        FROM entry_translations t
        JOIN entries e ON e.id = t.entry_id
        WHERE t.translation_status = 'ai_draft'
        ORDER BY t.ai_draft_at DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def approve_translation(
    conn: sqlite3.Connection,
    *,
    entry_id: int,
    lang: str,
    reviewed_by: str,
    publish: bool = True,
) -> None:
    new_status = "published" if publish else "reviewed"
    conn.execute(
        """
        UPDATE entry_translations
        SET translation_status = ?,
            reviewed_at = ?,
            reviewed_by = ?
        WHERE entry_id = ? AND lang = ?
        """,
        (new_status, _now(), reviewed_by, entry_id, lang),
    )


# ── Failed imports ─────────────────────────────────────────────────────


def record_failed_import(
    conn: sqlite3.Connection,
    *,
    nextcloud_path: str,
    error_message: str,
) -> None:
    """Tracks files that the ingest tick couldn't open at all.

    Distinct from `files.status='failed'`: that's for files we got into
    the table but later failed. This is for files we never got that far on.
    """
    row = conn.execute(
        "SELECT id, retry_count FROM failed_imports WHERE nextcloud_path = ?",
        (nextcloud_path,),
    ).fetchone()
    if row:
        conn.execute(
            """
            UPDATE failed_imports
            SET error_message = ?,
                attempted_at = ?,
                retry_count = retry_count + 1
            WHERE id = ?
            """,
            (error_message, _now(), row["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO failed_imports (nextcloud_path, error_message) VALUES (?, ?)",
            (nextcloud_path, error_message),
        )


# ── Admin review queue ─────────────────────────────────────────────────


def list_links_needing_review(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT l.id, l.confidence, l.reason, l.created_at,
               f.title AS file_title, f.public_url, f.file_type,
               e.slug  AS entry_slug,
               t.title AS entry_title_en
        FROM links l
        JOIN files f   ON f.id = l.file_id
        JOIN entries e ON e.id = l.entry_id
        JOIN entry_translations t
          ON t.entry_id = e.id AND t.lang = 'en'
        WHERE l.needs_review = 1
        ORDER BY l.confidence DESC, l.created_at DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def list_quarantine(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, nextcloud_path, title, file_type, scan_result,
               scan_signatures, moderation_flag, error_message
        FROM files
        WHERE status = 'quarantined' OR moderation_flag = 1
        ORDER BY id DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


# ── Helpers ────────────────────────────────────────────────────────────


def _file_row(row: sqlite3.Row) -> FileRow:
    return FileRow(
        id=int(row["id"]),
        nextcloud_path=row["nextcloud_path"],
        file_type=row["file_type"],
        title=row["title"],
        status=row["status"],
        public_url=row["public_url"],
        size_bytes=row["size_bytes"],
        extracted_text=row["extracted_text"],
        ai_summary_en=row["ai_summary_en"],
        ai_summary_af=row["ai_summary_af"],
        cc_cycle=row["cc_cycle"],
        cc_week=row["cc_week"],
        scan_result=row["scan_result"],
        moderation_flag=int(row["moderation_flag"]),
    )


def loads(value: str | None) -> Any:
    """Safe JSON load — returns None on empty/invalid."""
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None
