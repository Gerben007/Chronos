"""End-to-end ingest tick test with fake Nextcloud + Anthropic.

Verifies the happy path: download → scan-noop → classify → link → move
→ mark processed. Also covers the moderation-quarantine branch.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from chronos_ingest import db, main, scan
from chronos_ingest.config import Settings
from chronos_ingest.nextcloud import RemoteFile


# ── Fakes ──────────────────────────────────────────────────────────────


@dataclass
class _FakeUsage:
    input_tokens: int = 200
    output_tokens: int = 80


@dataclass
class _FakeBlock:
    text: str


@dataclass
class _FakeResponse:
    content: list[_FakeBlock]
    usage: _FakeUsage


class _FakeAnthropic:
    def __init__(self, reply: str) -> None:
        self.reply = reply

        class _Messages:
            def create(inner, **_kwargs: Any) -> _FakeResponse:
                return _FakeResponse(content=[_FakeBlock(text=self.reply)], usage=_FakeUsage())

        self.messages = _Messages()


class _FakeNextcloud:
    """In-memory stand-in for NextcloudClient."""

    def __init__(self, *, inbox: list[RemoteFile], file_bytes: bytes = b"%PDF-fake") -> None:
        self.inbox = inbox
        self.file_bytes = file_bytes
        self.moves: list[tuple[str, str]] = []
        self.shares: list[str] = []

    def __enter__(self) -> _FakeNextcloud:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def list_dir(self, _path: str) -> list[RemoteFile]:
        return list(self.inbox)

    def list_tree(self, _path: str) -> list[RemoteFile]:
        return list(self.inbox)

    def download_to_path(self, _remote: str, local: Path) -> int:
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(self.file_bytes)
        return len(self.file_bytes)

    def move(self, src: str, dest: str, *, overwrite: bool = False) -> None:  # noqa: ARG002
        self.moves.append((src, dest))

    def create_public_share(self, remote_path: str, *, password: str | None = None, hide_download: bool = False) -> str:  # noqa: ARG002
        url = f"https://nc.example.com/s/{Path(remote_path).name}"
        self.shares.append(url)
        return url


# ── Test fixtures ──────────────────────────────────────────────────────


def _make_db(tmp_path: Path) -> Path:
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
            "INSERT INTO entries (id, slug, type, lane_id, start_year, display_dates_en) "
            "VALUES (1, 'abraham', 'person', 1, -2000, '2000 BC')"
        )
        c.execute(
            "INSERT INTO entry_translations (entry_id, lang, title, summary, translation_status) "
            "VALUES (1, 'en', 'Abraham', 'Father of nations', 'published')"
        )
        c.commit()
    return p


def _settings(db_path: Path) -> Settings:
    return Settings(
        nextcloud_url="https://nc.example.com",
        nextcloud_user="gerben",
        nextcloud_app_password="x",
        anthropic_api_key="sk-test",
        sqlite_path=db_path,
        clamav_socket=Path("/nonexistent.sock"),
    )


# ── Tests ──────────────────────────────────────────────────────────────


_REMOTE = "/Chronos/Cycle 1/1. Foundations (Grammar Stage)/Week 5/abraham.pdf"


def test_process_one_file_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        scan, "scan_file",
        lambda _p, *, clamav_socket: scan.ScanResult(result="clean", signatures=[], notes=""),
    )

    db_path = _make_db(tmp_path)
    settings = _settings(db_path)
    nc = _FakeNextcloud(
        inbox=[RemoteFile(
            path=_REMOTE, name="abraham.pdf", size=1234,
            content_type="application/pdf", etag="x", is_dir=False,
        )]
    )
    # Haiku might return a different cycle/week — path-derived (1, 5) must win.
    fake_anthropic = _FakeAnthropic(
        '{"links": [{"entry_slug": "abraham", "confidence": 0.9, "reason": "match"}], '
        '"summary_en": "Notes on Abraham", "cc_cycle": 2, "cc_week": 22, '
        '"age_min": 6, "age_max": 10, "moderation_flag": false}'
    )

    monkeypatch.setattr(main, "NextcloudClient", lambda **_: nc)
    result = main.run_tick(settings, anthropic_client=fake_anthropic)

    assert result["processed"] == 1
    assert nc.shares == [f"https://nc.example.com/s/abraham.pdf"]
    assert nc.moves == []                    # no moves — files stay in place

    with db.connect(db_path) as c:
        row = db.get_file_by_path(c, _REMOTE)
        assert row is not None
        assert row.status == "processed"
        assert row.ai_summary_en == "Notes on Abraham"
        assert row.cc_cycle == 1             # path won over Haiku's 2
        assert row.cc_week == 5              # path won over Haiku's 22
        assert row.public_url == "https://nc.example.com/s/abraham.pdf"


def test_idempotent_skip_already_processed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A second tick over the same file is a no-op."""
    monkeypatch.setattr(
        scan, "scan_file",
        lambda _p, *, clamav_socket: scan.ScanResult(result="clean", signatures=[], notes=""),
    )
    db_path = _make_db(tmp_path)
    settings = _settings(db_path)
    nc = _FakeNextcloud(
        inbox=[RemoteFile(
            path=_REMOTE, name="abraham.pdf", size=1234,
            content_type="application/pdf", etag="x", is_dir=False,
        )]
    )
    fake_anthropic = _FakeAnthropic(
        '{"links": [{"entry_slug": "abraham", "confidence": 0.9, "reason": "r"}], '
        '"summary_en": "x", "cc_cycle": 1, "cc_week": 5, '
        '"age_min": 6, "age_max": 10, "moderation_flag": false}'
    )
    monkeypatch.setattr(main, "NextcloudClient", lambda **_: nc)

    first = main.run_tick(settings, anthropic_client=fake_anthropic)
    assert first["processed"] == 1
    nc.shares.clear()
    second = main.run_tick(settings, anthropic_client=fake_anthropic)
    assert second["skipped"] == 1
    assert nc.shares == []                   # no new share on retry


def test_moderation_quarantine_no_move(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        scan, "scan_file",
        lambda _p, *, clamav_socket: scan.ScanResult(result="clean", signatures=[], notes=""),
    )
    db_path = _make_db(tmp_path)
    settings = _settings(db_path)
    nc = _FakeNextcloud(
        inbox=[RemoteFile(
            path="/Chronos/Cycle 1/Week 1/iffy.pdf",
            name="iffy.pdf", size=999, content_type="application/pdf", etag="y", is_dir=False,
        )]
    )
    fake_anthropic = _FakeAnthropic(
        '{"links": [], "summary_en": "bad", "cc_cycle": null, "cc_week": null, '
        '"age_min": null, "age_max": null, "moderation_flag": true}'
    )
    monkeypatch.setattr(main, "NextcloudClient", lambda **_: nc)
    result = main.run_tick(settings, anthropic_client=fake_anthropic)
    assert result["quarantined"] == 1
    assert nc.shares == []
    assert nc.moves == []                    # file stays in place
    with db.connect(db_path) as c:
        row = db.get_file_by_path(c, "/Chronos/Cycle 1/Week 1/iffy.pdf")
        assert row is not None
        assert row.status == "quarantined"
        assert row.moderation_flag == 1


def test_scan_infected_quarantines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        scan, "scan_file",
        lambda _p, *, clamav_socket: scan.ScanResult(
            result="infected", signatures=["Eicar-Test-Signature"], notes="virus"
        ),
    )
    db_path = _make_db(tmp_path)
    settings = _settings(db_path)
    nc = _FakeNextcloud(
        inbox=[RemoteFile(
            path="/Chronos/Cycle 1/eicar.pdf",
            name="eicar.pdf", size=1, content_type="application/pdf", etag="z", is_dir=False,
        )]
    )
    monkeypatch.setattr(main, "NextcloudClient", lambda **_: nc)
    result = main.run_tick(settings, anthropic_client=_FakeAnthropic("{}"))
    assert result["quarantined"] == 1
    assert nc.moves == []
    with db.connect(db_path) as c:
        row = db.get_file_by_path(c, "/Chronos/Cycle 1/eicar.pdf")
        assert row is not None
        assert row.status == "quarantined"
        assert row.scan_result == "infected"
