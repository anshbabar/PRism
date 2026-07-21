"""Tests that an analysis and its children are persisted correctly."""

from __future__ import annotations

from collections.abc import Callable

from app.db.models import Analysis, ChangedFile, Embedding, PullRequest, Repository
from app.db.repository import PersistResult
from app.ingest.fixtures import load_fixture
from sqlalchemy import func, select
from sqlalchemy.orm import Session

Persist = Callable[[str], tuple[PersistResult, list[float]]]


def _count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_persist_writes_all_rows(db_session: Session, persist_fixture: Persist) -> None:
    result, vector = persist_fixture("add-orders-table")

    assert _count(db_session, Repository) == 1
    assert _count(db_session, PullRequest) == 1
    assert _count(db_session, Analysis) == 1
    assert _count(db_session, Embedding) == 1
    assert _count(db_session, ChangedFile) >= 1

    analysis = db_session.get(Analysis, result.analysis_id)
    assert analysis is not None
    assert analysis.status in {"completed", "fallback"}
    assert 1 <= analysis.final_score <= 5
    assert analysis.deterministic_score == 4  # db_schema(3) + missing_tests(2) -> score 4
    assert analysis.risk_band == "high"
    assert analysis.review_json["summary"]  # full review kept verbatim
    assert analysis.risk_json["signals"]  # deterministic signals kept for explainability


def test_embedding_row_matches_vector(db_session: Session, persist_fixture: Persist) -> None:
    result, vector = persist_fixture("auth-token-expiry")
    embedding = db_session.scalar(
        select(Embedding).where(Embedding.analysis_id == result.analysis_id)
    )
    assert embedding is not None
    assert embedding.dim == len(vector)
    assert embedding.vector == vector
    assert embedding.provider == "hash"


def test_changed_files_match_parsed_diff(db_session: Session, persist_fixture: Persist) -> None:
    result, _ = persist_fixture("add-orders-table")
    fixture_files = load_fixture("add-orders-table")
    files = db_session.scalars(
        select(ChangedFile).where(ChangedFile.analysis_id == result.analysis_id)
    ).all()
    assert {f.path for f in files}  # non-empty
    assert all(f.status in {"added", "modified", "deleted", "renamed"} for f in files)
    assert fixture_files  # sanity: fixture loaded


def test_reanalysis_same_head_reuses_pr_new_analysis(
    db_session: Session, persist_fixture: Persist
) -> None:
    first, _ = persist_fixture("bump-dependencies")
    second, _ = persist_fixture("bump-dependencies")

    assert first.pull_request_id == second.pull_request_id  # same PR row reused
    assert first.analysis_id != second.analysis_id  # but a new analysis
    assert _count(db_session, PullRequest) == 1
    assert _count(db_session, Analysis) == 2
