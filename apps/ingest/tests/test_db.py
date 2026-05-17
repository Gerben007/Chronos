import sqlite3
from pathlib import Path

import pytest

from chronos_ingest import db


def _make_db(tmp_path: Path) -> Path:
    """Builds a fresh DB with the production schema and one seed lane + entry."""
    p = tmp_path / "chronos.db"
    schema = Path(__file__).parents[3] / "db" / "migrations" / "0001_init.sql"
    with sqlite3.connect(p) as c:
        c.executescript(schema.read_text(encoding="utf-8"))
        c.execute(
            """
            INSERT INTO lanes (id, slug, label_en, colour, colour_soft, group_label, sort_order)
            VALUES (1, 'bible', 'Bible', '#1F2A44', '#DAD4BE', 'biblical', 0)
            """
        )
        c.execute(
            """
            INSERT INTO entries (id, slug, type, lane_id, start_year, display_dates_en)
            VALUES (1, 'abraham', 'person', 1, -2000, '2000 BC')
            """
        )
        c.execute(
            """
            INSERT INTO entry_translations (entry_id, lang, title, summary, translation_status)
            VALUES (1, 'en', 'Abraham', 'Father of nations', 'published')
            """
        )
        c.commit()
    return p


def test_upsert_file_idempotent(tmp_path: Path) -> None:
    p = _make_db(tmp_path)
    with db.connect(p) as c, db.transaction(c):
        id1 = db.upsert_file_pending(
            c, nextcloud_path="/inbox/a.pdf", file_type="pdf", title="A"
        )
        id2 = db.upsert_file_pending(
            c, nextcloud_path="/inbox/a.pdf", file_type="pdf", title="A again"
        )
        assert id1 == id2


def test_pipeline_progression(tmp_path: Path) -> None:
    p = _make_db(tmp_path)
    with db.connect(p) as c:
        with db.transaction(c):
            fid = db.upsert_file_pending(
                c, nextcloud_path="/inbox/b.pdf", file_type="pdf", title="B"
            )
            db.update_scan(c, file_id=fid, scan_result="clean", scan_signatures=None)
            db.update_extract(c, file_id=fid, extracted_text="hello", duration_seconds=None)
            db.update_classification(
                c,
                file_id=fid,
                ai_summary_en="A summary",
                cc_cycle=1,
                cc_week=2,
                age_min=6,
                age_max=10,
                moderation_flag=0,
                public_url="https://nc/share/x",
            )
            db.mark_processed(c, file_id=fid, needs_review=False)
        row = db.get_file_by_path(c, "/inbox/b.pdf")
    assert row is not None
    assert row.status == "processed"
    assert row.scan_result == "clean"
    assert row.ai_summary_en == "A summary"
    assert row.cc_cycle == 1
    assert row.public_url == "https://nc/share/x"


def test_quarantine_and_list(tmp_path: Path) -> None:
    p = _make_db(tmp_path)
    with db.connect(p) as c:
        with db.transaction(c):
            fid = db.upsert_file_pending(
                c, nextcloud_path="/inbox/bad.pdf", file_type="pdf", title="Bad"
            )
            db.update_scan(c, file_id=fid, scan_result="infected", scan_signatures="Eicar")
            db.quarantine_file(c, file_id=fid, error_message="virus found")
        q = db.list_quarantine(c)
    assert len(q) == 1
    assert q[0]["scan_result"] == "infected"


def test_upsert_link_idempotent_and_review(tmp_path: Path) -> None:
    p = _make_db(tmp_path)
    with db.connect(p) as c:
        with db.transaction(c):
            fid = db.upsert_file_pending(
                c, nextcloud_path="/inbox/c.pdf", file_type="pdf", title="C"
            )
            l1 = db.upsert_link(
                c,
                entry_id=1,
                file_id=fid,
                confidence=0.6,
                source="auto",
                reason="initial",
                needs_review=True,
            )
            l2 = db.upsert_link(
                c,
                entry_id=1,
                file_id=fid,
                confidence=0.9,
                source="auto",
                reason="updated",
                needs_review=False,
            )
            assert l1 == l2
        review = db.list_links_needing_review(c)
    assert review == []


def test_ai_draft_does_not_overwrite_published(tmp_path: Path) -> None:
    p = _make_db(tmp_path)
    with db.connect(p) as c, db.transaction(c):
        # Seed a published AF translation.
        c.execute(
            """
            INSERT INTO entry_translations
                (entry_id, lang, title, summary, translation_status)
            VALUES (1, 'af', 'Abram', 'Vader van nasies', 'published')
            """
        )
        db.upsert_ai_draft_translation(
            c,
            entry_id=1,
            lang="af",
            title="AI title",
            summary="AI summary",
            wiki_md=None,
            source_lang="en",
        )
        row = c.execute(
            "SELECT title, translation_status FROM entry_translations WHERE entry_id=1 AND lang='af'"
        ).fetchone()
    assert row["title"] == "Abram"
    assert row["translation_status"] == "published"


def test_failed_imports_increments(tmp_path: Path) -> None:
    p = _make_db(tmp_path)
    with db.connect(p) as c, db.transaction(c):
        db.record_failed_import(c, nextcloud_path="/inbox/x.pdf", error_message="boom")
        db.record_failed_import(c, nextcloud_path="/inbox/x.pdf", error_message="boom again")
        row = c.execute(
            "SELECT retry_count FROM failed_imports WHERE nextcloud_path = ?",
            ("/inbox/x.pdf",),
        ).fetchone()
    assert row["retry_count"] == 1


def test_list_entries_minimal(tmp_path: Path) -> None:
    p = _make_db(tmp_path)
    with db.connect(p) as c:
        entries = db.list_entries_minimal(c)
    assert entries == [
        {
            "id": 1,
            "slug": "abraham",
            "type": "person",
            "start_year": -2000,
            "end_year": None,
            "title_en": "Abraham",
            "lane_slug": "bible",
        }
    ]
