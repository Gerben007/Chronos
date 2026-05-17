import sqlite3
from pathlib import Path

import pytest

from chronos_ingest import budget


def _make_db(tmp_path: Path) -> Path:
    db = tmp_path / "chronos.db"
    schema = Path(__file__).parents[3] / "db" / "migrations" / "0001_init.sql"
    with sqlite3.connect(db) as c:
        c.executescript(schema.read_text(encoding="utf-8"))
    return db


def test_today_cost_empty(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    assert budget.today_cost(db) == 0.0


def test_record_then_today_cost(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    budget.record(db, input_tokens=1000, output_tokens=200, cost_usd=0.12)
    budget.record(db, input_tokens=500, output_tokens=100, cost_usd=0.05)
    assert budget.today_cost(db) == pytest.approx(0.17)


def test_may_call_under_ceiling(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    budget.record(db, input_tokens=0, output_tokens=0, cost_usd=0.80)
    assert budget.may_call(db, estimated_cost_usd=0.10, daily_budget_usd=1.00)
    assert not budget.may_call(db, estimated_cost_usd=0.30, daily_budget_usd=1.00)


def test_record_for_specific_day(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    budget.record(db, input_tokens=10, output_tokens=10, cost_usd=0.01, day="2026-01-01")
    budget.record(db, input_tokens=20, output_tokens=20, cost_usd=0.02, day="2026-01-01")
    budget.record(db, input_tokens=5,  output_tokens=5,  cost_usd=0.005, day="2026-01-02")
    assert budget.today_cost(db, day="2026-01-01") == pytest.approx(0.03)
    assert budget.today_cost(db, day="2026-01-02") == pytest.approx(0.005)
