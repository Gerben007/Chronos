"""Cloudflare Access JWT verification.

Verifies the `Cf-Access-Jwt-Assertion` header against Cloudflare's
public JWKS for the configured team. We do NOT trust the proxy alone:
even though Cloudflare Access sits in front of /admin/*, an admin
endpoint must independently verify the token on every request.

Public keys are fetched from
    https://<team>.cloudflareaccess.com/cdn-cgi/access/certs
and cached for 10 minutes. The `aud` claim is checked against the
configured AUD tag (the application identifier set in the CF Access
dashboard).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, cast

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jwt.algorithms import RSAAlgorithm

_DEFAULT_KEY_TTL_SECONDS = 600  # 10 min


class JwtVerifyError(Exception):
    """Raised on any verification failure (bad signature, exp, aud, ...)."""


@dataclass
class VerifiedClaims:
    """The subset of claims we care about after verification."""

    email: str
    sub: str
    aud: str
    iss: str
    exp: int
    iat: int
    raw: dict[str, Any]


class KeyFetcher(Protocol):
    """Pluggable so tests can inject a fixed-key fetcher."""

    def __call__(self, team: str) -> dict[str, Any]: ...


def default_key_fetcher(team: str) -> dict[str, Any]:
    """Fetches the live JWKS from Cloudflare. Used in production."""
    url = f"https://{team}.cloudflareaccess.com/cdn-cgi/access/certs"
    resp = httpx.get(url, timeout=5.0)
    resp.raise_for_status()
    return cast(dict[str, Any], resp.json())


class CfAccessVerifier:
    """Stateful verifier with a small in-memory JWKS cache.

    Construct one per process. `verify(token)` is the only public method.
    """

    def __init__(
        self,
        team: str,
        aud: str,
        *,
        key_fetcher: KeyFetcher = default_key_fetcher,
        key_ttl_seconds: int = _DEFAULT_KEY_TTL_SECONDS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not team:
            raise ValueError("team must not be empty")
        if not aud:
            raise ValueError("aud must not be empty")
        self.team = team
        self.aud = aud
        self.issuer = f"https://{team}.cloudflareaccess.com"
        self._fetch = key_fetcher
        self._ttl = key_ttl_seconds
        self._clock = clock
        self._keys_cache: dict[str, Any] | None = None
        self._keys_fetched_at: float = 0.0

    def _jwks(self) -> dict[str, Any]:
        now = self._clock()
        if self._keys_cache and (now - self._keys_fetched_at) < self._ttl:
            return self._keys_cache
        try:
            jwks = self._fetch(self.team)
        except Exception as e:  # noqa: BLE001
            raise JwtVerifyError(f"could not fetch JWKS: {e}") from e
        self._keys_cache = jwks
        self._keys_fetched_at = now
        return jwks

    def verify(self, token: str) -> VerifiedClaims:
        """Returns the verified claims, or raises JwtVerifyError."""
        if not token or not isinstance(token, str):
            raise JwtVerifyError("token missing")
        try:
            unverified_header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as e:
            raise JwtVerifyError(f"malformed token header: {e}") from e

        kid = unverified_header.get("kid")
        if not kid:
            raise JwtVerifyError("token has no kid")

        jwks = self._jwks()
        key_obj = next(
            (k for k in jwks.get("keys", []) if k.get("kid") == kid),
            None,
        )
        if key_obj is None:
            raise JwtVerifyError(f"no matching key for kid={kid!r}")

        try:
            public_key = RSAAlgorithm.from_jwk(key_obj)
        except Exception as e:  # noqa: BLE001
            raise JwtVerifyError(f"could not build public key: {e}") from e
        if not isinstance(public_key, RSAPublicKey):
            raise JwtVerifyError("expected RSA public key from JWK")

        try:
            claims = jwt.decode(
                token,
                key=public_key,
                algorithms=["RS256"],
                audience=self.aud,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "aud", "iss", "sub"]},
            )
        except jwt.ExpiredSignatureError as e:
            raise JwtVerifyError("token expired") from e
        except jwt.InvalidAudienceError as e:
            raise JwtVerifyError("aud mismatch") from e
        except jwt.InvalidIssuerError as e:
            raise JwtVerifyError("iss mismatch") from e
        except jwt.InvalidTokenError as e:
            raise JwtVerifyError(f"invalid token: {e}") from e

        return VerifiedClaims(
            email=str(claims.get("email", "")),
            sub=str(claims["sub"]),
            aud=str(claims["aud"]) if isinstance(claims["aud"], str) else self.aud,
            iss=str(claims["iss"]),
            exp=int(claims["exp"]),
            iat=int(claims["iat"]),
            raw=claims,
        )
