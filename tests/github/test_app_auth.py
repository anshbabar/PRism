"""Unit test for App JWT creation (RS256).

Skipped if ``pyjwt[crypto]`` isn't installed, so the core suite stays runnable
without the crypto extra. Never hits the network — it only signs and verifies.
"""

from __future__ import annotations

import pytest
from app.github.app_auth import create_app_jwt


def test_create_app_jwt_is_signed_and_verifiable() -> None:
    jwt = pytest.importorskip("jwt")
    pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    token = create_app_jwt("123456", private_pem)
    decoded = jwt.decode(token, public_pem, algorithms=["RS256"])

    assert decoded["iss"] == "123456"
    assert decoded["exp"] > decoded["iat"]  # non-empty, forward-dated lifetime
