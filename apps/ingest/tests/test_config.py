from pathlib import Path

import pytest

from chronos_ingest.config import Settings


def test_defaults_when_env_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)  # avoid picking up a real .env
    # Wipe inherited env that might leak in from CI / dev shells.
    for k in (
        "NEXTCLOUD_URL",
        "ANTHROPIC_API_KEY",
        "CF_ACCESS_TEAM",
        "CF_ACCESS_AUD",
        "WEBHOOK_HMAC_SECRET",
    ):
        monkeypatch.delenv(k, raising=False)
    s = Settings()
    assert s.anthropic_model.startswith("claude-haiku-")
    assert s.daily_haiku_budget_usd == 1.0
    assert s.webhook_max_age_seconds == 300
    assert s.nextcloud_inbox_path == "/CC-Library/_inbox"


def test_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-xyz")
    monkeypatch.setenv("DAILY_HAIKU_BUDGET_USD", "0.25")
    monkeypatch.setenv("CF_ACCESS_TEAM", "stratusfinance")
    monkeypatch.setenv("CF_ACCESS_AUD", "deadbeef")
    s = Settings()
    assert s.anthropic_api_key == "sk-xyz"
    assert s.daily_haiku_budget_usd == 0.25
    assert s.cf_access_team == "stratusfinance"
    assert s.cf_access_aud == "deadbeef"
