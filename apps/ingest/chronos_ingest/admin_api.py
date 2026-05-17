"""Minimal FastAPI admin app.

Phase 1 surface is intentionally narrow: health + whoami. The real
review-queue endpoints land in Phase 2 once the file pipeline and the
links/quarantine schemas have data flowing through them.

Auth model: every protected route verifies the Cf-Access-Jwt-Assertion
header via chronos_ingest.jwt_verify — we do not trust the proxy alone.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status

from chronos_ingest.config import Settings, get_settings
from chronos_ingest.jwt_verify import CfAccessVerifier, JwtVerifyError, VerifiedClaims

app = FastAPI(
    title="Chronos admin API",
    version="0.1.0",
    docs_url=None,             # never expose OpenAPI UI in prod
    redoc_url=None,
    openapi_url=None,
)


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


@app.get("/admin/api/health")
def health() -> dict[str, str]:
    """Unauthenticated. Cheap. For container healthchecks only."""
    return {"status": "ok"}


@app.get("/admin/api/whoami")
def whoami(claims: Annotated[VerifiedClaims, Depends(require_admin)]) -> dict[str, str | int]:
    """Returns the email proven by the verified CF Access JWT."""
    return {
        "email": claims.email,
        "sub": claims.sub,
        "exp": claims.exp,
    }
