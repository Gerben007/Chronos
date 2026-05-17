"""Tests for the Cloudflare Access JWT verifier.

We generate an RSA keypair in the test fixture and inject a stub
key-fetcher that returns the public half. The verifier never makes a
network call in these tests.
"""

from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from chronos_ingest.jwt_verify import CfAccessVerifier, JwtVerifyError

TEAM = "stratusfinance"
AUD = "deadbeef-aud-1234"
ISS = f"https://{TEAM}.cloudflareaccess.com"
KID = "test-key-1"


@pytest.fixture(scope="module")
def keypair() -> tuple[bytes, dict]:
    """Generates an RSA keypair and the JWKS representation of the public half."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk["kid"] = KID
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"
    return private_pem, {"keys": [jwk]}


def _make_verifier(jwks: dict, *, aud: str = AUD, clock=None) -> CfAccessVerifier:
    return CfAccessVerifier(
        team=TEAM,
        aud=aud,
        key_fetcher=lambda _team: jwks,
        clock=clock or time.time,
    )


def _make_token(
    private_pem: bytes,
    *,
    aud: str = AUD,
    iss: str = ISS,
    exp_offset: int = 600,
    extra: dict | None = None,
    kid: str = KID,
) -> str:
    now = int(time.time())
    payload = {
        "iss": iss,
        "aud": aud,
        "sub": "user-1",
        "email": "admin@example.com",
        "iat": now,
        "exp": now + exp_offset,
        **(extra or {}),
    }
    return jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": kid})


def test_verifier_rejects_empty_construction() -> None:
    with pytest.raises(ValueError):
        CfAccessVerifier(team="", aud=AUD)
    with pytest.raises(ValueError):
        CfAccessVerifier(team=TEAM, aud="")


def test_valid_token(keypair) -> None:
    priv, jwks = keypair
    verifier = _make_verifier(jwks)
    claims = verifier.verify(_make_token(priv))
    assert claims.email == "admin@example.com"
    assert claims.sub == "user-1"
    assert claims.iss == ISS


def test_expired_token(keypair) -> None:
    priv, jwks = keypair
    verifier = _make_verifier(jwks)
    token = _make_token(priv, exp_offset=-1)
    with pytest.raises(JwtVerifyError, match="expired"):
        verifier.verify(token)


def test_wrong_aud(keypair) -> None:
    priv, jwks = keypair
    verifier = _make_verifier(jwks)
    token = _make_token(priv, aud="not-our-aud")
    with pytest.raises(JwtVerifyError, match="aud"):
        verifier.verify(token)


def test_wrong_iss(keypair) -> None:
    priv, jwks = keypair
    verifier = _make_verifier(jwks)
    token = _make_token(priv, iss="https://evil.cloudflareaccess.com")
    with pytest.raises(JwtVerifyError, match="iss"):
        verifier.verify(token)


def test_unknown_kid(keypair) -> None:
    priv, jwks = keypair
    verifier = _make_verifier(jwks)
    token = _make_token(priv, kid="some-other-kid")
    with pytest.raises(JwtVerifyError, match="no matching key"):
        verifier.verify(token)


def test_malformed_token(keypair) -> None:
    _, jwks = keypair
    verifier = _make_verifier(jwks)
    with pytest.raises(JwtVerifyError):
        verifier.verify("not.a.jwt")


def test_missing_token(keypair) -> None:
    _, jwks = keypair
    verifier = _make_verifier(jwks)
    with pytest.raises(JwtVerifyError, match="token missing"):
        verifier.verify("")


def test_key_cache(keypair) -> None:
    priv, jwks = keypair
    calls = {"n": 0}

    def fetcher(_team: str) -> dict:
        calls["n"] += 1
        return jwks

    verifier = CfAccessVerifier(team=TEAM, aud=AUD, key_fetcher=fetcher, key_ttl_seconds=600)
    verifier.verify(_make_token(priv))
    verifier.verify(_make_token(priv))
    verifier.verify(_make_token(priv))
    assert calls["n"] == 1  # cached after first fetch
