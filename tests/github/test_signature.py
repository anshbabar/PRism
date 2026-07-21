"""Unit tests for webhook HMAC-SHA256 signature verification."""

from __future__ import annotations

from app.github.webhook import sign_body, verify_signature

SECRET = "s3cr3t"
BODY = b'{"action":"opened"}'


def test_valid_signature_passes() -> None:
    assert verify_signature(BODY, sign_body(BODY, SECRET), SECRET) is True


def test_wrong_secret_fails() -> None:
    assert verify_signature(BODY, sign_body(BODY, "other"), SECRET) is False


def test_tampered_body_fails() -> None:
    sig = sign_body(BODY, SECRET)
    assert verify_signature(BODY + b"tamper", sig, SECRET) is False


def test_missing_header_fails() -> None:
    assert verify_signature(BODY, None, SECRET) is False


def test_unconfigured_secret_fails_closed() -> None:
    assert verify_signature(BODY, sign_body(BODY, SECRET), None) is False


def test_malformed_header_fails() -> None:
    assert verify_signature(BODY, "sha1=deadbeef", SECRET) is False
