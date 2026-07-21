"""Tests for the background worker: analyze -> persist -> (optionally) post.

The GitHub client is faked (no network), and persistence goes to the in-memory
SQLite ``db_sessionmaker`` fixture from ``tests/conftest.py``.
"""

from __future__ import annotations

from app.api.routes_webhook import handle_pull_request_event
from app.core.config import Settings
from app.db.models import Analysis, PullRequest, Repository
from app.github.render import PRISM_REVIEW_MARKER
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tests.github.support import FakeGitHubClient, make_pr_payload


def _settings(*, post_reviews: bool) -> Settings:
    return Settings(github_webhook_secret="s", post_reviews=post_reviews)


def test_dry_run_persists_but_does_not_post(db_sessionmaker: sessionmaker[Session]) -> None:
    fake = FakeGitHubClient()
    handle_pull_request_event(
        make_pr_payload(action="opened", repo="octo/hello", number=7),
        settings=_settings(post_reviews=False),
        session_factory=db_sessionmaker,
        client=fake,
    )

    with db_sessionmaker() as s:
        assert s.scalar(select(func.count()).select_from(Analysis)) == 1
        repo = s.scalar(select(Repository))
        assert repo is not None and repo.owner == "octo" and repo.name == "hello"
        pr = s.scalar(select(PullRequest))
        assert pr is not None and pr.number == 7 and pr.head_sha == "deadbeef"

    assert fake.diff_calls == 1
    assert fake.created == []  # dry-run: nothing posted


def test_enabled_mode_posts_one_comment_review(db_sessionmaker: sessionmaker[Session]) -> None:
    fake = FakeGitHubClient()
    handle_pull_request_event(
        make_pr_payload(number=7),
        settings=_settings(post_reviews=True),
        session_factory=db_sessionmaker,
        client=fake,
    )

    assert len(fake.created) == 1
    posted = fake.created[0]
    assert posted["event"] == "COMMENT"  # never REQUEST_CHANGES
    assert PRISM_REVIEW_MARKER in posted["body"]
    assert "**Risk score:**" in posted["body"]


def test_only_one_review_per_pr_across_deliveries(
    db_sessionmaker: sessionmaker[Session],
) -> None:
    fake = FakeGitHubClient()
    settings = _settings(post_reviews=True)

    # opened -> posts; a later synchronize -> must not post again.
    handle_pull_request_event(
        make_pr_payload(action="opened", number=7),
        settings=settings,
        session_factory=db_sessionmaker,
        client=fake,
    )
    handle_pull_request_event(
        make_pr_payload(action="synchronize", number=7),
        settings=settings,
        session_factory=db_sessionmaker,
        client=fake,
    )

    assert len(fake.created) == 1  # idempotent posting
    with db_sessionmaker() as s:
        assert s.scalar(select(func.count()).select_from(Analysis)) == 2  # both analyzed


def test_posts_even_when_persistence_unavailable() -> None:
    # A sessionmaker over a schemaless DB: every query raises SQLAlchemyError.
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    broken_factory = sessionmaker(bind=engine, future=True)
    fake = FakeGitHubClient()

    handle_pull_request_event(
        make_pr_payload(number=7),
        settings=_settings(post_reviews=True),
        session_factory=broken_factory,
        client=fake,
    )

    # Persistence failed gracefully; the review is still posted.
    assert len(fake.created) == 1
    engine.dispose()


def test_skips_when_no_installation_id_and_no_client() -> None:
    payload = make_pr_payload(installation_id=None)
    # No client injected and no installation id -> cannot authenticate; no crash.
    handle_pull_request_event(payload, settings=_settings(post_reviews=True))
