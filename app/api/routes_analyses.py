"""Read endpoints that power the dashboard.

``GET /api/analyses`` lists stored analyses (newest first) and
``GET /api/analyses/{id}`` returns the full detail plus similar prior PRs. These
are read-only; analyses are created by the analyze endpoint (see
``routes_analyze.py``).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.schema import AIReview
from app.core.config import get_settings
from app.db.queries import get_analysis, list_analysis_summaries
from app.db.session import get_session
from app.diff.risk import RiskResult
from app.retrieval.store import SimilarPR, find_similar

router = APIRouter(prefix="/api", tags=["analyses"])


class AnalysisSummary(BaseModel):
    analysis_id: uuid.UUID
    repository: str
    number: int
    title: str
    author: str
    status: str
    deterministic_score: int
    final_score: int
    risk_band: str
    top_concern: str | None
    files_changed: int
    created_at: datetime


class ChangedFileOut(BaseModel):
    path: str
    status: str
    additions: int
    deletions: int


class AnalysisDetail(BaseModel):
    analysis_id: uuid.UUID
    repository: str
    number: int
    title: str
    author: str
    url: str
    description: str
    status: str
    provider: str
    model: str
    prompt_version: str
    deterministic_score: int
    final_score: int
    risk_band: str
    created_at: datetime
    risk: RiskResult
    review: AIReview
    changed_files: list[ChangedFileOut]
    similar: list[SimilarPR]


@router.get("/analyses", response_model=list[AnalysisSummary])
def list_analyses(session: Annotated[Session, Depends(get_session)]) -> list[AnalysisSummary]:
    return [AnalysisSummary(**row) for row in list_analysis_summaries(session, limit=100)]


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
def get_analysis_detail(
    analysis_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
) -> AnalysisDetail:
    analysis = get_analysis(session, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail=f"No analysis {analysis_id}")

    pr = analysis.pull_request
    repo = pr.repository
    vector = analysis.embedding.vector if analysis.embedding else []
    similar = (
        find_similar(
            session,
            analysis_id=analysis.id,
            repository_id=pr.repository_id,
            query_vector=vector,
            k=get_settings().similar_top_k,
        )
        if vector
        else []
    )

    return AnalysisDetail(
        analysis_id=analysis.id,
        repository=f"{repo.owner}/{repo.name}",
        number=pr.number,
        title=pr.title,
        author=pr.author,
        url=pr.url,
        description=pr.description,
        status=analysis.status,
        provider=analysis.provider,
        model=analysis.model,
        prompt_version=analysis.prompt_version,
        deterministic_score=analysis.deterministic_score,
        final_score=analysis.final_score,
        risk_band=analysis.risk_band,
        created_at=analysis.created_at,
        risk=RiskResult.model_validate(analysis.risk_json),
        review=AIReview.model_validate(analysis.review_json),
        changed_files=[
            ChangedFileOut(
                path=f.path, status=f.status, additions=f.additions, deletions=f.deletions
            )
            for f in analysis.changed_files
        ],
        similar=similar,
    )
