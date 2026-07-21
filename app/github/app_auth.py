"""GitHub App authentication: App JWT -> installation access token.

Flow (see docs/technical-design.md §7):

1. Sign a short-lived RS256 **App JWT** (``iss`` = App ID) with the App's private
   key. GitHub caps its lifetime at 10 minutes; we use 9 and backdate ``iat`` 60s
   to tolerate clock skew.
2. Exchange it at ``POST /app/installations/{id}/access_tokens`` for an
   **installation token** (valid ~1 hour), scoped to that installation.

Installation tokens are cached in-process per installation and reused until ~1
minute before expiry. Secrets (the PEM and tokens) are never logged.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger("app.github.app_auth")

_APP_JWT_TTL = timedelta(minutes=9)
_CLOCK_SKEW = timedelta(seconds=60)
_REFRESH_MARGIN = timedelta(seconds=60)

# installation_id -> (token, expires_at). Process-local; fine for a single worker.
_token_cache: dict[int, tuple[str, datetime]] = {}


def create_app_jwt(app_id: str, private_key_pem: str, *, now: datetime | None = None) -> str:
    """Return a signed RS256 App JWT. Requires ``pyjwt[crypto]`` (lazy import)."""
    import jwt  # lazy: only the real GitHub App path needs it

    now = now or datetime.now(UTC)
    payload = {
        "iat": int((now - _CLOCK_SKEW).timestamp()),
        "exp": int((now + _APP_JWT_TTL).timestamp()),
        "iss": app_id,
    }
    return jwt.encode(payload, private_key_pem, algorithm="RS256")


def _read_private_key(settings: Settings) -> str:
    if not settings.github_app_id:
        raise RuntimeError("GITHUB_APP_ID is not configured")
    if not settings.github_app_private_key_path:
        raise RuntimeError("GITHUB_APP_PRIVATE_KEY_PATH is not configured")
    return Path(settings.github_app_private_key_path).read_text()


def get_installation_token(
    settings: Settings, installation_id: int, *, now: datetime | None = None
) -> str:
    """Return a cached installation token, minting a fresh one when needed."""
    now = now or datetime.now(UTC)
    cached = _token_cache.get(installation_id)
    if cached and cached[1] - _REFRESH_MARGIN > now:
        return cached[0]

    app_jwt = create_app_jwt(settings.github_app_id or "", _read_private_key(settings), now=now)
    with httpx.Client(base_url=settings.github_api_url, timeout=10.0) as client:
        resp = client.post(
            f"/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    token = str(data["token"])
    expires_at = datetime.fromisoformat(str(data["expires_at"]).replace("Z", "+00:00"))
    _token_cache[installation_id] = (token, expires_at)
    logger.info("minted installation token", extra={"installation_id": installation_id})
    return token
