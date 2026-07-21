"""Webhook signature verification and payload parsing (pure, no I/O).

Signature verification is HMAC-SHA256 over the *raw* request body, compared in
constant time. Parsing helpers pull the fields we need out of a ``pull_request``
event and map them to the pipeline's metadata shape. Everything here is
untrusted input — nothing is executed, and PR text flows through only as data.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any

# PR actions we analyze. Everything else (closed, edited, labeled, ...) is ignored.
HANDLED_ACTIONS = frozenset({"opened", "synchronize", "reopened"})

_SIG_PREFIX = "sha256="


def verify_signature(body: bytes, signature_header: str | None, secret: str | None) -> bool:
    """Return True iff ``signature_header`` is a valid HMAC-SHA256 of ``body``.

    Fails closed: a missing secret (misconfiguration), a missing or malformed
    header, or any mismatch returns False. The comparison is constant-time.
    """
    if not secret or not signature_header:
        return False
    if not signature_header.startswith(_SIG_PREFIX):
        return False
    expected = _SIG_PREFIX + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def sign_body(body: bytes, secret: str) -> str:
    """Compute the ``sha256=...`` signature header for ``body`` (mirrors GitHub).

    Used by tests to sign fixtures; kept next to ``verify_signature`` so the two
    stay in lockstep.
    """
    return _SIG_PREFIX + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class PullRequestRef:
    owner: str
    repo: str
    number: int
    installation_id: int | None

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"


def pr_ref_from_payload(payload: dict[str, Any]) -> PullRequestRef:
    """Extract owner / repo / number / installation id from a PR event payload."""
    repo = payload.get("repository") or {}
    full_name = str(repo.get("full_name") or "unknown/unknown")
    owner, _, name = full_name.partition("/")
    pr = payload.get("pull_request") or {}
    installation = payload.get("installation") or {}
    inst_id = installation.get("id")
    return PullRequestRef(
        owner=owner or "unknown",
        repo=name or "unknown",
        number=int(pr.get("number") or 0),
        installation_id=int(inst_id) if inst_id is not None else None,
    )


def pr_metadata_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Map a ``pull_request`` event payload to the pipeline's metadata dict.

    The webhook payload embeds the full PR object (identical to the REST PR
    representation), so we build metadata from it and fetch only the diff over
    the API — no redundant metadata round-trip. All values are untrusted PR text.
    """
    pr = payload.get("pull_request") or {}
    repo = payload.get("repository") or {}
    head = pr.get("head") or {}
    base = pr.get("base") or {}
    user = pr.get("user") or {}
    return {
        "repo": str(repo.get("full_name") or "unknown/unknown"),
        "number": int(pr.get("number") or 0),
        "title": str(pr.get("title") or ""),
        "author": str(user.get("login") or ""),
        "head_sha": str(head.get("sha") or ""),
        "base_sha": str(base.get("sha") or ""),
        "description": str(pr.get("body") or ""),  # untrusted
        "url": str(pr.get("html_url") or ""),
    }
