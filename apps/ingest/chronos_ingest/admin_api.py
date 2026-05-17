"""FastAPI admin API for review queues.

Auth: every protected route depends on `require_admin`, which verifies
the Cf-Access-Jwt-Assertion header against Cloudflare's public keys.
We do not trust the proxy alone — the JWT is checked on every request.

Queues exposed:
  - Files (low-confidence links awaiting confirmation)
  - Quarantine (ClamAV/sanitiser failures + moderation flags)
  - Translations (AI-drafted Afrikaans content)
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict

from chronos_ingest import db, rebuild
from chronos_ingest.config import Settings, get_settings
from chronos_ingest.jwt_verify import CfAccessVerifier, JwtVerifyError, VerifiedClaims


app = FastAPI(
    title="Chronos admin API",
    version="0.2.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


# ── Dependencies ──────────────────────────────────────────────────────


def _verifier(settings: Annotated[Settings, Depends(get_settings)]) -> CfAccessVerifier:
    if not settings.cf_access_team or not settings.cf_access_aud:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CF Access not configured",
        )
    return CfAccessVerifier(team=settings.cf_access_team, aud=settings.cf_access_aud)


def require_admin(
    cf_access_jwt_assertion: Annotated[
        str | None, Header(alias="Cf-Access-Jwt-Assertion")
    ] = None,
    verifier: Annotated[CfAccessVerifier, Depends(_verifier)] = ...,  # type: ignore[assignment]
) -> VerifiedClaims:
    if not cf_access_jwt_assertion:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing CF Access JWT",
        )
    try:
        return verifier.verify(cf_access_jwt_assertion)
    except JwtVerifyError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid token: {e}",
        ) from e


def _trigger_rebuild(settings: Settings) -> None:
    """Rewrites resources.json — called after any DB mutation that affects it."""
    try:
        data = rebuild.export_resources(settings.sqlite_path)
        out = settings.resources_output_path
        out.parent.mkdir(parents=True, exist_ok=True)
        import json
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:  # noqa: BLE001
        # Don't fail the admin action because the rebuild step blew up;
        # next ingest tick will refresh anyway.
        pass


# ── Public health ─────────────────────────────────────────────────────


@app.get("/admin/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ── Whoami ────────────────────────────────────────────────────────────


@app.get("/admin/api/whoami")
def whoami(claims: Annotated[VerifiedClaims, Depends(require_admin)]) -> dict[str, str | int]:
    return {"email": claims.email, "sub": claims.sub, "exp": claims.exp}


# ── File-link review queue ────────────────────────────────────────────


class ConfirmBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


@app.get("/admin/api/review/files")
def list_files_review(
    claims: Annotated[VerifiedClaims, Depends(require_admin)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, Any]]:
    """Links flagged needs_review=1 (Haiku confidence 0.5-0.7)."""
    _ = claims
    with db.connect(settings.sqlite_path) as c:
        return db.list_links_needing_review(c)


@app.post("/admin/api/review/files/{link_id}/confirm")
def confirm_link(
    link_id: int,
    claims: Annotated[VerifiedClaims, Depends(require_admin)],
    settings: Annotated[Settings, Depends(get_settings)],
    _body: ConfirmBody | None = None,
) -> dict[str, str]:
    with db.connect(settings.sqlite_path) as c, db.transaction(c):
        db.confirm_link(c, link_id=link_id, confirmed_by=claims.email)
    _trigger_rebuild(settings)
    return {"status": "confirmed"}


@app.post("/admin/api/review/files/{link_id}/reject")
def reject_link(
    link_id: int,
    claims: Annotated[VerifiedClaims, Depends(require_admin)],
    settings: Annotated[Settings, Depends(get_settings)],
    _body: ConfirmBody | None = None,
) -> dict[str, str]:
    _ = claims
    with db.connect(settings.sqlite_path) as c, db.transaction(c):
        db.reject_link(c, link_id=link_id)
    _trigger_rebuild(settings)
    return {"status": "rejected"}


# ── Quarantine queue ──────────────────────────────────────────────────


@app.get("/admin/api/review/quarantine")
def list_quarantine(
    claims: Annotated[VerifiedClaims, Depends(require_admin)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, Any]]:
    _ = claims
    with db.connect(settings.sqlite_path) as c:
        return db.list_quarantine(c)


@app.post("/admin/api/review/quarantine/{file_id}/release")
def release_quarantine(
    file_id: int,
    claims: Annotated[VerifiedClaims, Depends(require_admin)],
    settings: Annotated[Settings, Depends(get_settings)],
    _body: ConfirmBody | None = None,
) -> dict[str, str]:
    """Promotes a quarantined file back to needs_review so it appears in the
    files queue. The file row is otherwise unchanged.
    """
    _ = claims
    with db.connect(settings.sqlite_path) as c, db.transaction(c):
        c.execute(
            "UPDATE files SET status = 'needs_review', error_message = NULL WHERE id = ?",
            (file_id,),
        )
    return {"status": "released"}


@app.post("/admin/api/review/quarantine/{file_id}/delete")
def delete_quarantine(
    file_id: int,
    claims: Annotated[VerifiedClaims, Depends(require_admin)],
    settings: Annotated[Settings, Depends(get_settings)],
    _body: ConfirmBody | None = None,
) -> dict[str, str]:
    """Permanently deletes a quarantined file row (and cascading links)."""
    _ = claims
    with db.connect(settings.sqlite_path) as c, db.transaction(c):
        c.execute("DELETE FROM files WHERE id = ?", (file_id,))
    _trigger_rebuild(settings)
    return {"status": "deleted"}


# ── Translation review queue ──────────────────────────────────────────


@app.get("/admin/api/review/translations")
def list_translations(
    claims: Annotated[VerifiedClaims, Depends(require_admin)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, Any]]:
    _ = claims
    with db.connect(settings.sqlite_path) as c:
        return db.list_translations_for_review(c)


class TranslationApproveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    publish: bool = True


@app.post("/admin/api/review/translations/{entry_id}/{lang}/approve")
def approve_translation(
    entry_id: int,
    lang: str,
    body: TranslationApproveBody,
    claims: Annotated[VerifiedClaims, Depends(require_admin)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    if lang not in ("en", "af"):
        raise HTTPException(status_code=400, detail="lang must be en or af")
    with db.connect(settings.sqlite_path) as c, db.transaction(c):
        db.approve_translation(
            c,
            entry_id=entry_id,
            lang=lang,
            reviewed_by=claims.email,
            publish=body.publish,
        )
    return {"status": "approved"}
