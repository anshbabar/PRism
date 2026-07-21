"""Tests for similarity search over persisted analyses."""

from __future__ import annotations

from collections.abc import Callable

from app.db.repository import PersistResult
from app.retrieval.store import find_similar
from sqlalchemy.orm import Session

Persist = Callable[[str], tuple[PersistResult, list[float]]]


def test_related_pr_ranks_above_unrelated(db_session: Session, persist_fixture: Persist) -> None:
    # Two "orders" PRs plus an unrelated dependency bump, all in the same repo.
    persist_fixture("add-orders-table")
    persist_fixture("add-orders-api-endpoint")
    persist_fixture("bump-dependencies")

    # Re-run one PR head to get a fresh analysis + its query vector.
    result, vector = persist_fixture("add-orders-table")

    similar = find_similar(
        db_session,
        analysis_id=result.analysis_id,
        repository_id=result.repository_id,
        query_vector=vector,
        k=5,
    )

    assert similar, "expected at least one similar prior analysis"
    titles = [s.title for s in similar]
    # The orders API PR should be ranked above the dependency bump.
    orders_idx = next(i for i, t in enumerate(titles) if "orders API" in t or "orders" in t.lower())
    bump_idx = next(i for i, t in enumerate(titles) if "Bump" in t or "uvicorn" in t.lower())
    assert orders_idx < bump_idx
    # Similarities are sorted descending.
    sims = [s.similarity for s in similar]
    assert sims == sorted(sims, reverse=True)


def test_find_similar_excludes_self_and_scopes_to_repo(
    db_session: Session, persist_fixture: Persist
) -> None:
    result, vector = persist_fixture("update-env-config")
    # Only one analysis exists in the repo besides… none. Its own row is excluded.
    similar = find_similar(
        db_session,
        analysis_id=result.analysis_id,
        repository_id=result.repository_id,
        query_vector=vector,
        k=5,
    )
    assert all(s.analysis_id != result.analysis_id for s in similar)


def test_top_k_limits_results(db_session: Session, persist_fixture: Persist) -> None:
    for name in ("add-orders-table", "add-orders-api-endpoint", "auth-token-expiry"):
        persist_fixture(name)
    result, vector = persist_fixture("large-refactor-logging")

    similar = find_similar(
        db_session,
        analysis_id=result.analysis_id,
        repository_id=result.repository_id,
        query_vector=vector,
        k=2,
    )
    assert len(similar) <= 2
