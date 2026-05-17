"""Export resources from SQLite → static JSON for the Astro build.

The site needs no DB access at build time; it reads
`db/seed/resources.json` (a single file keyed by entry slug). The
ingest container writes it after each successful tick:

    python -m chronos_ingest.rebuild --out /repo/db/seed/resources.json

Shape:
{
  "adam": [
    {
      "file_id": 1,
      "title": "Adam and Eve - Wikipedia",
      "file_type": "pdf",
      "public_url": "https://...",
      "summary_en": "...",
      "summary_af": null,
      "cc_cycle": 2,
      "cc_week": 1,
      "age_min": 8,
      "age_max": 14,
      "confidence": 0.95,
      "needs_review": false
    },
    ...
  ]
}

Only confirmed-or-auto links (needs_review=0) are exported. Review-queue
entries stay invisible to the public site until an admin approves.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def export_resources(db_path: Path) -> dict[str, list[dict]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT e.slug      AS entry_slug,
                   f.id        AS file_id,
                   f.title,
                   f.file_type,
                   f.public_url,
                   f.ai_summary_en,
                   f.ai_summary_af,
                   f.cc_cycle,
                   f.cc_week,
                   f.age_min,
                   f.age_max,
                   l.confidence,
                   l.needs_review
            FROM links l
            JOIN entries e ON e.id = l.entry_id
            JOIN files   f ON f.id = l.file_id
            WHERE f.status = 'processed'
              AND f.public_url IS NOT NULL
              AND l.needs_review = 0
            ORDER BY e.slug, l.confidence DESC
            """
        ).fetchall()
    finally:
        conn.close()

    out: dict[str, list[dict]] = {}
    for r in rows:
        slug = r["entry_slug"]
        out.setdefault(slug, []).append(
            {
                "file_id":       int(r["file_id"]),
                "title":         r["title"],
                "file_type":     r["file_type"],
                "public_url":    r["public_url"],
                "summary_en":    r["ai_summary_en"],
                "summary_af":    r["ai_summary_af"],
                "cc_cycle":      r["cc_cycle"],
                "cc_week":       r["cc_week"],
                "age_min":       r["age_min"],
                "age_max":       r["age_max"],
                "confidence":    round(float(r["confidence"]), 3),
                "needs_review":  bool(r["needs_review"]),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chronos-rebuild")
    parser.add_argument(
        "--db", type=Path, default=Path("/data/db/chronos.db"),
        help="SQLite DB path",
    )
    parser.add_argument(
        "--out", type=Path, default=Path("/app/db/seed/resources.json"),
        help="Output JSON path",
    )
    args = parser.parse_args(argv)

    if not args.db.exists():
        print(f"DB not found at {args.db}", file=sys.stderr)
        return 1

    data = export_resources(args.db)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum(len(v) for v in data.values())
    print(f"wrote {total} resources across {len(data)} entries to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
