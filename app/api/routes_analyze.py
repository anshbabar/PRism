"""Analysis routes.

Milestone 2 parses a saved fixture's diff and runs deterministic risk heuristics.
Milestone 3 adds a schema-validated AI review (mock provider by default; real
provider via ``LLM_PROVIDER=anthropic``) with a safe heuristic fallback.
Milestone 5 persists each analysis to the database, embeds it, and returns
similar prior PRs. Persistence degrades gracefully: if the database is
unreachable the analysis is still returned (``persisted=false``, ``similar=[]``),
so the offline pipeline keeps working.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.reviewer import ReviewOutcome
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.repository import persist_analysis
from app.db.session import get_session
from app.diff.models import ParsedDiff
from app.diff.risk import RiskResult
from app.ingest.fixtures import (
    FixtureNotFound,
    InvalidFixtureName,
    load_fixture,
)
from app.pipeline import analyze_fixture
from app.retrieval.store import SimilarPR, find_similar

logger = get_logger("app.api.analyze")

router = APIRouter(prefix="/api/analyze", tags=["analyze"])


class LocalFixtureRequest(BaseModel):
    name: str


class LocalFixtureResponse(BaseModel):
    name: str
    metadata: dict[str, Any]
    parsed_diff: ParsedDiff
    risk: RiskResult
    ai: ReviewOutcome
    persisted: bool
    analysis_id: uuid.UUID | None
    similar: list[SimilarPR]


@router.post("/local-fixture", response_model=LocalFixtureResponse)
def analyze_local_fixture(
    req: LocalFixtureRequest,
    session: Annotated[Session, Depends(get_session)],
) -> LocalFixtureResponse:
    """Parse + risk-assess + AI-review a fixture, persist it, and find similar PRs."""
    try:
        fixture = load_fixture(req.name)
    except InvalidFixtureName as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FixtureNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    settings = get_settings()
    artifacts = analyze_fixture(fixture, settings)

    persisted = False
    analysis_id: uuid.UUID | None = None
    similar: list[SimilarPR] = []
    try:
        result = persist_analysis(
            session,
            metadata=fixture.metadata,
            parsed=artifacts.parsed,
            risk=artifacts.risk,
            review_outcome=artifacts.review,
            vector=artifacts.vector,
            embedding_provider_name=artifacts.embedding_provider_name,
            embedding_model=artifacts.embedding_model,
            latency_ms=artifacts.latency_ms,
        )
        analysis_id = result.analysis_id
        similar = find_similar(
            session,
            analysis_id=result.analysis_id,
            repository_id=result.repository_id,
            query_vector=artifacts.vector,
            k=settings.similar_top_k,
        )
        persisted = True
    except SQLAlchemyError as exc:
        session.rollback()
        logger.warning(
            "persistence unavailable; returning unsaved analysis",
            extra={"error": str(exc)},
        )

    return LocalFixtureResponse(
        name=fixture.name,
        metadata=fixture.metadata,
        parsed_diff=artifacts.parsed,
        risk=artifacts.risk,
        ai=artifacts.review,
        persisted=persisted,
        analysis_id=analysis_id,
        similar=similar,
    )
