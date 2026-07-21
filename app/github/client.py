"""Minimal GitHub REST client for the PR review flow.

Only what the webhook needs: fetch a PR's unified diff, list existing reviews,
and post one review. Each call uses a short-lived ``httpx.Client`` (a webhook
handles just a few calls), so there's no connection lifecycle to manage. The
installation token is passed in — this class never touches App credentials.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings
from app.github.app_auth import get_installation_token
from app.github.render import PRISM_REVIEW_MARKER

_API_VERSION = "2022-11-28"


class GitHubClient:
    def __init__(
        self, token: str, *, api_url: str = "https://api.github.com", timeout: float = 10.0
    ) -> None:
        self._token = token
        self._api_url = api_url
        self._timeout = timeout

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": accept,
            "X-GitHub-Api-Version": _API_VERSION,
        }

    def get_pull_request_diff(self, owner: str, repo: str, number: int) -> str:
        """Return the PR's unified diff (via the ``.diff`` media type)."""
        with httpx.Client(base_url=self._api_url, timeout=self._timeout) as client:
            resp = client.get(
                f"/repos/{owner}/{repo}/pulls/{number}",
                headers=self._headers("application/vnd.github.v3.diff"),
            )
            resp.raise_for_status()
            return resp.text

    def list_reviews(self, owner: str, repo: str, number: int) -> list[dict[str, Any]]:
        """Return existing reviews on the PR (first page, up to 100)."""
        with httpx.Client(base_url=self._api_url, timeout=self._timeout) as client:
            resp = client.get(
                f"/repos/{owner}/{repo}/pulls/{number}/reviews",
                headers=self._headers(),
                params={"per_page": 100},
            )
            resp.raise_for_status()
            data = resp.json()
            return list(data) if isinstance(data, list) else []

    def has_prism_review(self, owner: str, repo: str, number: int) -> bool:
        """True if a prior PRism review (identified by its marker) already exists."""
        return any(
            PRISM_REVIEW_MARKER in str(r.get("body") or "")
            for r in self.list_reviews(owner, repo, number)
        )

    def create_review(
        self, owner: str, repo: str, number: int, *, body: str, event: str = "COMMENT"
    ) -> dict[str, Any]:
        """Post a single PR-level review. Defaults to a non-blocking COMMENT."""
        with httpx.Client(base_url=self._api_url, timeout=self._timeout) as client:
            resp = client.post(
                f"/repos/{owner}/{repo}/pulls/{number}/reviews",
                headers=self._headers(),
                json={"body": body, "event": event},
            )
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
            return result


def build_installation_client(settings: Settings, installation_id: int) -> GitHubClient:
    """Construct a client authenticated as the given App installation."""
    token = get_installation_token(settings, installation_id)
    return GitHubClient(token, api_url=settings.github_api_url)
