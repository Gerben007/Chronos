"""Env-driven configuration for the Chronos ingest service.

Loaded once at startup; never reaches over the wire to fetch values.
Secrets must come via the environment (`.env` on the homelab,
chmod 600) — never committed.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-derived configuration.

    Every field has either an explicit env name or a sensible default.
    Fields without defaults are required and will fail loudly if absent
    — that's the intent (no silent degradation in production).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Nextcloud ─────────────────────────────────────────────────────
    nextcloud_url: str = Field(default="")
    nextcloud_user: str = Field(default="")
    nextcloud_app_password: str = Field(default="")
    # Single recursive scan root. Files stay in place; status is tracked in
    # the DB. CC cycle/stage/week are inferred from the folder structure.
    nextcloud_root_path: str = "/Chronos"

    # ── Anthropic ─────────────────────────────────────────────────────
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = "claude-haiku-4-5-20251001"
    daily_haiku_budget_usd: float = 1.00

    # ── Storage ───────────────────────────────────────────────────────
    sqlite_path: Path = Path("/data/db/chronos.db")
    astro_dist_path: Path = Path("/data/dist")
    rebuild_webhook_url: str = ""

    # ── Admin / Cloudflare Access ────────────────────────────────────
    admin_api_bind: str = "0.0.0.0:8001"
    cf_access_team: str = Field(default="")
    cf_access_aud: str = Field(default="")

    # ── Webhooks ──────────────────────────────────────────────────────
    webhook_hmac_secret: str = Field(default="")
    webhook_max_age_seconds: int = 300

    # ── File scanning ─────────────────────────────────────────────────
    clamav_socket: Path = Path("/var/run/clamav/clamd.sock")


def get_settings() -> Settings:
    """Returns a fresh Settings instance. Cheap; safe to call per-request."""
    return Settings()
