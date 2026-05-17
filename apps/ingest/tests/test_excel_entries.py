from __future__ import annotations

import json
from pathlib import Path

import pytest

from chronos_ingest import excel_entries


VALID_LANES = {"bible", "egypt", "rome", "church-history", "science", "arts", "reformation"}


def _template_with_rows(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "in.xlsx"
    excel_entries.export_xlsx(rows, p)
    return p


def _entry(**overrides) -> dict:
    base = {
        "slug": "test",
        "type": "person",
        "lane_slug": "bible",
        "start_year": -1000,
        "end_year": -900,
        "importance": 3,
        "translations": {
            "en": {"title": "T", "display_dates": "1000 BC", "summary": "S"},
            "af": {"title": "Tt", "display_dates": "1000 v.C.", "summary": "Ss"},
        },
        "scripture_refs": ["Gen 1"],
    }
    base.update(overrides)
    return base


def test_roundtrip_minimal(tmp_path: Path) -> None:
    src = [_entry()]
    p = _template_with_rows(tmp_path, src)
    result = excel_entries.parse_xlsx(p, valid_lanes=VALID_LANES)
    assert result.errors == []
    assert len(result.entries) == 1
    e = result.entries[0]
    assert e["slug"] == "test"
    assert e["start_year"] == -1000
    assert e["end_year"] == -900
    assert e["translations"]["en"]["title"] == "T"
    assert e["translations"]["af"]["title"] == "Tt"
    assert e["scripture_refs"] == ["Gen 1"]


def test_blank_af_falls_back_to_en(tmp_path: Path) -> None:
    src = [_entry(translations={
        "en": {"title": "Only EN", "display_dates": "10 BC", "summary": "Sum"},
    })]
    p = _template_with_rows(tmp_path, src)
    result = excel_entries.parse_xlsx(p, valid_lanes=VALID_LANES)
    assert not result.errors
    e = result.entries[0]
    assert e["translations"]["af"]["title"] == "Only EN"
    assert e["translations"]["af"]["summary"] == "Sum"


def test_invalid_lane_collected_as_error(tmp_path: Path) -> None:
    src = [_entry(lane_slug="atlantis")]
    p = _template_with_rows(tmp_path, src)
    result = excel_entries.parse_xlsx(p, valid_lanes=VALID_LANES)
    assert result.entries == []
    assert any("atlantis" in e for e in result.errors)


def test_duplicate_slug_collected_as_error(tmp_path: Path) -> None:
    p = _template_with_rows(tmp_path, [_entry(slug="same"), _entry(slug="same")])
    result = excel_entries.parse_xlsx(p, valid_lanes=VALID_LANES)
    assert len(result.entries) == 1
    assert any("duplicate" in e for e in result.errors)


def test_sort_order_is_chronological(tmp_path: Path) -> None:
    p = _template_with_rows(tmp_path, [
        _entry(slug="b", start_year=-500),
        _entry(slug="a", start_year=-2000),
        _entry(slug="c", start_year=100),
    ])
    result = excel_entries.parse_xlsx(p, valid_lanes=VALID_LANES)
    assert [e["slug"] for e in result.entries] == ["a", "b", "c"]


def test_roundtrip_seed_entries(tmp_path: Path) -> None:
    """The shipped seed entries.json must roundtrip cleanly."""
    seed = Path(__file__).parents[3] / "db" / "seed" / "entries.json"
    entries = json.loads(seed.read_text(encoding="utf-8"))
    p = tmp_path / "seed.xlsx"
    excel_entries.export_xlsx(entries, p)
    result = excel_entries.parse_xlsx(p, valid_lanes=VALID_LANES)
    assert result.errors == [], f"seed roundtrip errors: {result.errors}"
    assert len(result.entries) == len(entries)
