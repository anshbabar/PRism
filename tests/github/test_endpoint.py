"""End-to-end tests for ``POST /api/github/webhook`` via the FastAPI TestClient.

The GitHub client is faked (monkeypatched at the route boundary) and the DB
dependency points at the in-memory SQLite ``db_sessionmaker`` fixture. Starlette
runs background tasks before the TestClient call returns, so we can assert on
persistence immediately after a 202.
"""

from __future__ import annotations

import json

import app.api.routes_webhook as routes_webhook
import pytest
from app.core.config import get_settings
from app.db.models import Analysis
from app.db.session import get_session_factory
from app.github.webhook import sign_body
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from tests.github.support import FakeGitHubClient, make_pr_payload

SECRET = "testsecret"
ENDPOINT = "/api/github/webhook"


@pytest.fixture(autouse=True)
def _isolate_settings() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _make_client(
    db_sessionmaker: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    fake: FakeGitHubClient,
    *,
    post_reviews: bool,
) -> TestClient:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("POST_REVIEWS", "true" if post_reviews else "false")
    get_settings.cache_clear()
    monkeypatch.setattr(
        routes_webhook, "build_installation_client", lambda settings, installation_id: fake
    )
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: db_sessionmaker
    return TestClient(app)


def _post(
    client: TestClient,
    payload: dict,
    *,
    event: str = "pull_request",
    secret: str = SECRET,
    signed: bool = True,
    valid_sig: bool = True,
) -> object:
    body = json.dumps(payload).encode()
    headers = {"X-GitHub-Event": event, "Content-Type": "application/json"}
    if signed:
        headers["X-Hub-Signature-256"] = sign_body(body, secret) if valid_sig else "sha256=bad"
    return client.post(ENDPOINT, content=body, headers=headers)


def test_ping_returns_pong(
    db_sessionmaker: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _make_client(db_sessionmaker, monkeypatch, FakeGitHubClient(), post_reviews=False)
    resp = _post(client, {"zen": "keep it simple"}, event="ping")
    assert resp.status_code == 200
    assert resp.json() == {"msg": "pong"}


def test_missing_signature_is_401(
    db_sessionmaker: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGitHubClient()
    client = _make_client(db_sessionmaker, monkeypatch, fake, post_reviews=False)
    resp = _post(client, make_pr_payload(), signed=False)
    assert resp.status_code == 401
    assert fake.diff_calls == 0


def test_invalid_signature_is_401(
    db_sessionmaker: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGitHubClient()
    client = _make_client(db_sessionmaker, monkeypatch, fake, post_reviews=False)
    resp = _post(client, make_pr_payload(), valid_sig=False)
    assert resp.status_code == 401
    assert fake.diff_calls == 0


def test_non_pull_request_event_is_204(
    db_sessionmaker: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _make_client(db_sessionmaker, monkeypatch, FakeGitHubClient(), post_reviews=False)
    resp = _post(client, {"hello": "world"}, event="issues")
    assert resp.status_code == 204


def test_ignored_action_is_204(
    db_sessionmaker: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGitHubClient()
    client = _make_client(db_sessionmaker, monkeypatch, fake, post_reviews=False)
    resp = _post(client, make_pr_payload(action="closed"))
    assert resp.status_code == 204
    assert fake.diff_calls == 0
    with db_sessionmaker() as s:
        assert s.scalar(select(func.count()).select_from(Analysis)) == 0


def test_opened_pr_returns_202_and_persists_in_dry_run(
    db_sessionmaker: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGitHubClient()
    client = _make_client(db_sessionmaker, monkeypatch, fake, post_reviews=False)
    resp = _post(client, make_pr_payload(action="opened", number=7))

    assert resp.status_code == 202
    assert resp.json()["number"] == 7
    with db_sessionmaker() as s:
        assert s.scalar(select(func.count()).select_from(Analysis)) == 1
    assert fake.diff_calls == 1
    assert fake.created == []  # dry-run posts nothing


def test_enabled_mode_posts_one_comment_review(
    db_sessionmaker: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGitHubClient()
    client = _make_client(db_sessionmaker, monkeypatch, fake, post_reviews=True)
    resp = _post(client, make_pr_payload(action="opened", number=7))

    assert resp.status_code == 202
    assert len(fake.created) == 1
    assert fake.created[0]["event"] == "COMMENT"
