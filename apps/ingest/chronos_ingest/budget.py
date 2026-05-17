"""Daily Anthropic spend guard.

Reads / writes the `usage` table from db/migrations/0001_init.sql.
Single source of truth for "did we hit the ceiling today?".
Caller pattern:

    if not budget.may_call(estimated_cost_usd):
        raise BudgetExceeded
    # ... make the Haiku call ...
    budget.record(input_tokens, output_tokens, actual_cost_usd)
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


class BudgetExceededError(Exception):
    """Raised by callers that opt for exception-style budget checks."""


@contextmanager
def _conn(db_path: Path) -> Iterator[sqlite3.Connection]:
    c = sqlite3.connect(db_path)
    try:
        c.execute("PRAGMA foreign_keys = ON;")
        yield c
        c.commit()
    finally:
        c.close()


def _today_utc() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%d")


def today_cost(db_path: Path, *, day: str | None = None) -> float:
    """Returns today's cumulative haiku_cost_usd (0.0 if no rows)."""
    day = day or _today_utc()
    with _conn(db_path) as c:
        row = c.execute(
            "SELECT haiku_cost_usd FROM usage WHERE day = ?",
            (day,),
        ).fetchone()
    return float(row[0]) if row else 0.0


def may_call(
    db_path: Path,
    estimated_cost_usd: float,
    daily_budget_usd: float,
    *,
    day: str | None = None,
) -> bool:
    """Pure check — does NOT record anything. Use record() after a call."""
    return today_cost(db_path, day=day) + estimated_cost_usd <= daily_budget_usd


def record(
    db_path: Path,
    *,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    day: str | None = None,
) -> None:
    """Atomically increments today's row, creating it if absent."""
    day = day or _today_utc()
    with _conn(db_path) as c:
        c.execute(
            """
            INSERT INTO usage (day, haiku_calls, haiku_input_tokens,
                               haiku_output_tokens, haiku_cost_usd)
            VALUES (?, 1, ?, ?, ?)
            ON CONFLICT(day) DO UPDATE SET
                haiku_calls         = haiku_calls         + 1,
                haiku_input_tokens  = haiku_input_tokens  + excluded.haiku_input_tokens,
                haiku_output_tokens = haiku_output_tokens + excluded.haiku_output_tokens,
                haiku_cost_usd      = haiku_cost_usd      + excluded.haiku_cost_usd
            """,
            (day, input_tokens, output_tokens, cost_usd),
        )
