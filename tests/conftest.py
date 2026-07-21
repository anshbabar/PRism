"""Shared pytest fixtures.

Database tests and the API client run against a hermetic in-memory SQLite
database (one shared connection via ``StaticPool``), so no Postgres or other
external service is needed. The API client overrides the ``get_session``
dependency to use this test database.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from app.ai.reviewer import build_review_input, generate_ai_review
from app.core.config import get_settings
from app.db.models import Base
from app.db.repository import PersistResult, persist_analysis
from app.db.session import get_session
from app.diff.parser import parse_diff
from app.diff.risk import assess_risk
from app.ingest.fixtures import load_fixture
from app.main import create_app
from app.retrieval.embeddings import HashingEmbeddingProvider
from app.retrieval.store import build_embedding_text
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def db_sessionmaker() -> Iterator[sessionmaker[Session]]:
    """A sessionmaker bound to a fresh in-memory SQLite database."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture
def db_session(db_sessionmaker: sessionmaker[Session]) -> Iterator[Session]:
    with db_sessionmaker() as session:
        yield session


@pytest.fixture
def client(db_sessionmaker: sessionmaker[Session]) -> Iterator[TestClient]:
    """A TestClient whose DB dependency is backed by the test SQLite database."""
    get_settings.cache_clear()
    app = create_app()

    def _override_get_session() -> Iterator[Session]:
        with db_sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def persist_fixture(
    db_session: Session,
) -> Callable[[str], tuple[PersistResult, list[float]]]:
    """Return a helper that runs the full pipeline on a fixture and persists it.

    All calls share the one ``db_session`` so retrieval tests can persist several
    fixtures and then query across them.
    """
    embedder = HashingEmbeddingProvider(dim=256)

    def _run(name: str) -> tuple[PersistResult, list[float]]:
        fixture = load_fixture(name)
        parsed = parse_diff(fixture.diff_text)
        risk = assess_risk(parsed, raw_text=fixture.diff_text)
        review_input = build_review_input(fixture.metadata, parsed, risk, fixture.diff_text)
        ai = generate_ai_review(review_input)
        vector = embedder.embed([build_embedding_text(fixture.metadata, ai.review)])[0]
        result = persist_analysis(
            db_session,
            metadata=fixture.metadata,
            parsed=parsed,
            risk=risk,
            review_outcome=ai,
            vector=vector,
            embedding_provider_name=embedder.name,
            embedding_model=embedder.model,
        )
        return result, vector

    return _run
