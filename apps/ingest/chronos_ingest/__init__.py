"""Chronos ingest pipeline.

Modules (per PLAN.md §7) — implementations land in Phase 2:
    config        env-driven settings
    nextcloud     WebDAV + OCS read-only shares
    scan          ClamAV + pikepdf JS strip + Pillow re-encode
    extract       pdfplumber / Pillow / ffprobe
    classify      Haiku classification (prompt-cached, moderation flag)
    translate     en → af for wiki + summaries
    db            SQLite writer (parameterised only)
    rebuild       fast-path JSON / full rebuild
    admin_api     FastAPI, CF Access JWT verification
    webhook       Apps Script HMAC webhook
    budget        daily Haiku spend guard
"""

__version__ = "0.1.0"
