"""Light tests for scan + extract.

Native deps (clamd, pikepdf, Pillow, ffprobe) aren't all available in the
test container; these tests verify the fail-closed behaviour and basic
dispatch paths instead.
"""

from __future__ import annotations

from pathlib import Path

from chronos_ingest import extract, scan


def test_scan_file_fails_closed_when_no_clamav(tmp_path: Path) -> None:
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF-fake")
    result = scan.scan_file(p, clamav_socket=Path("/nonexistent/clamd.sock"))
    assert result.is_clean is False
    assert result.result in ("suspicious", "infected", "error")


def test_extract_returns_empty_for_unsupported_type(tmp_path: Path) -> None:
    p = tmp_path / "y.zip"
    p.write_bytes(b"PK")
    r = extract.extract(p, file_type="doc")
    assert r.text is None
    assert r.duration_seconds is None
    assert r.width is None
    assert r.height is None


def test_extract_pdf_without_pdfplumber_returns_none(tmp_path: Path) -> None:
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF-not-real")
    # pdfplumber may not be installed; either way an invalid PDF yields None.
    assert extract.extract_pdf_text(p) is None


def test_ffprobe_duration_without_binary(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(extract.shutil, "which", lambda _name: None)
    assert extract.ffprobe_duration(tmp_path / "v.mp4") is None
