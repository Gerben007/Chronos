"""One-shot DB seeder.

Reads db/seed/lanes.json and db/seed/entries.json, applies the migration
schema if needed, and upserts lanes / entries / entry_translations rows
so the ingest classifier has something to link against.

Run with: python -m chronos_ingest.seed [--db /path/to/chronos.db]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    """Walks up from `start` until it finds the `db/` directory."""
    here = (start or Path(__file__)).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "db" / "migrations").is_dir():
            return parent
    raise FileNotFoundError("could not locate repo root with db/migrations/")


def apply_migrations(conn: sqlite3.Connection, repo_root: Path) -> None:
    """Idempotent — runs each .sql in db/migrations/ once.

    SQLite remembers which migrations ran via a tiny `_migrations` table
    so re-runs are safe.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _migrations ("
        "name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    applied = {row[0] for row in conn.execute("SELECT name FROM _migrations")}
    migrations_dir = repo_root / "db" / "migrations"
    for sql in sorted(migrations_dir.glob("*.sql")):
        if sql.name in applied:
            continue
        conn.executescript(sql.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO _migrations (name) VALUES (?)", (sql.name,))
        conn.commit()
        print(f"applied migration: {sql.name}")


def seed_lanes(conn: sqlite3.Connection, repo_root: Path) -> int:
    path = repo_root / "db" / "seed" / "lanes.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    n = 0
    for lane in data:
        conn.execute(
            """
            INSERT INTO lanes
                (slug, label_en, label_af, colour, colour_soft,
                 group_label, default_visible, base_layer, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                label_en = excluded.label_en,
                label_af = excluded.label_af,
                colour = excluded.colour,
                colour_soft = excluded.colour_soft,
                group_label = excluded.group_label,
                default_visible = excluded.default_visible,
                base_layer = excluded.base_layer,
                sort_order = excluded.sort_order
            """,
            (
                lane["slug"],
                lane["label_en"],
                lane.get("label_af"),
                lane["colour"],
                lane["colour_soft"],
                lane["group_label"],
                int(bool(lane.get("default_visible", True))),
                int(bool(lane.get("base_layer", False))),
                int(lane.get("sort_order", 0)),
            ),
        )
        n += 1
    return n


def seed_entries(conn: sqlite3.Connection, repo_root: Path) -> int:
    path = repo_root / "db" / "seed" / "entries.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    n = 0
    for e in data:
        # Resolve lane_id from lane_slug.
        lane = conn.execute(
            "SELECT id FROM lanes WHERE slug = ?",
            (e["lane_slug"],),
        ).fetchone()
        if lane is None:
            print(f"  skip {e['slug']}: unknown lane {e['lane_slug']}", file=sys.stderr)
            continue

        scripture_refs = e.get("scripture_refs")
        scripture_refs_json = json.dumps(scripture_refs) if scripture_refs else None

        translations = e.get("translations", {})
        en = translations.get("en", {})
        # `entries` table requires display_dates_en — fallback to slug if absent.
        display_dates_en = en.get("display_dates") or e["slug"]

        conn.execute(
            """
            INSERT INTO entries
                (slug, type, lane_id, start_year, end_year,
                 display_dates_en, display_dates_af, importance,
                 scripture_refs_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                type = excluded.type,
                lane_id = excluded.lane_id,
                start_year = excluded.start_year,
                end_year = excluded.end_year,
                display_dates_en = excluded.display_dates_en,
                display_dates_af = excluded.display_dates_af,
                importance = excluded.importance,
                scripture_refs_json = excluded.scripture_refs_json,
                updated_at = datetime('now')
            """,
            (
                e["slug"],
                e["type"],
                lane["id"],
                e["start_year"],
                e.get("end_year"),
                display_dates_en,
                translations.get("af", {}).get("display_dates"),
                int(e.get("importance", 3)),
                scripture_refs_json,
            ),
        )

        entry_id_row = conn.execute(
            "SELECT id FROM entries WHERE slug = ?", (e["slug"],)
        ).fetchone()
        entry_id = entry_id_row["id"] if isinstance(entry_id_row, sqlite3.Row) else entry_id_row[0]

        for lang in ("en", "af"):
            t = translations.get(lang)
            if not t:
                continue
            conn.execute(
                """
                INSERT INTO entry_translations
                    (entry_id, lang, title, summary, translation_status)
                VALUES (?, ?, ?, ?, 'published')
                ON CONFLICT(entry_id, lang) DO UPDATE SET
                    title = CASE
                        WHEN entry_translations.translation_status IN ('reviewed','published')
                          THEN entry_translations.title
                        ELSE excluded.title
                    END,
                    summary = CASE
                        WHEN entry_translations.translation_status IN ('reviewed','published')
                          THEN entry_translations.summary
                        ELSE excluded.summary
                    END
                """,
                (entry_id, lang, t.get("title", ""), t.get("summary", "")),
            )
        n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chronos-seed")
    parser.add_argument(
        "--db", type=Path, default=Path("/data/db/chronos.db"),
        help="SQLite DB path (will be created if absent)",
    )
    args = parser.parse_args(argv)

    repo_root = find_repo_root()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    print(f"seeding {args.db} from {repo_root}/db/")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        apply_migrations(conn, repo_root)
        n_lanes = seed_lanes(conn, repo_root)
        n_entries = seed_entries(conn, repo_root)
        conn.commit()
        print(f"seeded {n_lanes} lanes, {n_entries} entries")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
