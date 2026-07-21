"""Shared helpers for the GitHub webhook tests.

A fake GitHub client (records posted reviews, never touches the network) and a
builder for realistic ``pull_request`` event payloads.
"""

from __future__ import annotations

from typing import Any

from app.github.render import PRISM_REVIEW_MARKER

# A small, valid unified diff (an auth change) the fake client hands back.
DIFF_TEXT = """diff --git a/app/auth.py b/app/auth.py
index 1111111..2222222 100644
--- a/app/auth.py
+++ b/app/auth.py
@@ -1,3 +1,5 @@
 def login(user):
-    return token(user)
+    # refresh token handling
+    return token(user, refresh=True)
"""


def make_pr_payload(
    *,
    action: str = "opened",
    number: int = 7,
    repo: str = "octo/hello",
    installation_id: int | None = 42,
    title: str = "Add refresh tokens",
    body: str = "PR description",
    author: str = "octocat",
    head_sha: str = "deadbeef",
    base_sha: str = "cafebabe",
) -> dict[str, Any]:
    """Build a GitHub ``pull_request`` webhook payload."""
    payload: dict[str, Any] = {
        "action": action,
        "repository": {"full_name": repo},
        "pull_request": {
            "number": number,
            "title": title,
            "body": body,
            "user": {"login": author},
            "head": {"sha": head_sha},
            "base": {"sha": base_sha},
            "html_url": f"https://github.com/{repo}/pull/{number}",
        },
    }
    if installation_id is not None:
        payload["installation"] = {"id": installation_id}
    return payload


class FakeGitHubClient:
    """In-memory stand-in for ``GitHubClient`` that records posted reviews."""

    def __init__(
        self, *, diff: str = DIFF_TEXT, existing_reviews: list[dict[str, Any]] | None = None
    ):
        self._diff = diff
        self.reviews: list[dict[str, Any]] = list(existing_reviews or [])
        self.diff_calls = 0
        self.created: list[dict[str, Any]] = []

    def get_pull_request_diff(self, owner: str, repo: str, number: int) -> str:
        self.diff_calls += 1
        return self._diff

    def list_reviews(self, owner: str, repo: str, number: int) -> list[dict[str, Any]]:
        return list(self.reviews)

    def has_prism_review(self, owner: str, repo: str, number: int) -> bool:
        return any(PRISM_REVIEW_MARKER in str(r.get("body") or "") for r in self.reviews)

    def create_review(
        self, owner: str, repo: str, number: int, *, body: str, event: str = "COMMENT"
    ) -> dict[str, Any]:
        review = {"id": len(self.reviews) + 1, "body": body, "event": event}
        self.reviews.append(review)
        self.created.append(
            {"owner": owner, "repo": repo, "number": number, "body": body, "event": event}
        )
        return review
