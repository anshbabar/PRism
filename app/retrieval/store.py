"""Similarity search over prior PR analyses.

Vectors are stored as JSON (see ``app/db``), so similarity is computed in Python
with cosine distance and a linear scan scoped to the same repository. This is
correct and simple at MVP scale; the production upgrade path is a native
``pgvector`` column + ANN index (design doc §6.2).
"""

from __future__ import annotations

import math
import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.schema import AIReview
from app.db.models import Analysis, Embedding, PullRequest, Repository


class SimilarPR(BaseModel):
    analysis_id: uuid.UUID
    repository: str
    number: int
    title: str
    risk_score: int
    risk_band: str
    similarity: float
    summary: str


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors; 0.0 if either is zero."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def build_embedding_text(metadata: dict[str, Any], review: AIReview) -> str:
    """The document embedded for retrieval: title + summary + risk categories."""
    title = str(metadata.get("title") or "")
    categories = " ".join(review.risk_categories)
    return f"{title}\n{review.summary}\ncategories: {categories}".strip()


def find_similar(
    session: Session,
    *,
    analysis_id: uuid.UUID,
    repository_id: uuid.UUID,
    query_vector: list[float],
    k: int = 5,
) -> list[SimilarPR]:
    """Return the top-``k`` most similar prior analyses in the same repository."""
    rows = session.execute(
        select(Embedding, Analysis, PullRequest, Repository)
        .join(Analysis, Embedding.analysis_id == Analysis.id)
        .join(PullRequest, Analysis.pull_request_id == PullRequest.id)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .where(
            PullRequest.repository_id == repository_id,
            Analysis.id != analysis_id,
        )
    ).all()

    scored: list[tuple[float, Analysis, PullRequest, Repository]] = [
        (cosine_similarity(query_vector, emb.vector), analysis, pr, repo)
        for emb, analysis, pr, repo in rows
    ]
    scored.sort(key=lambda t: t[0], reverse=True)

    return [
        SimilarPR(
            analysis_id=analysis.id,
            repository=f"{repo.owner}/{repo.name}",
            number=pr.number,
            title=pr.title,
            risk_score=analysis.final_score,
            risk_band=analysis.risk_band,
            similarity=round(score, 4),
            summary=analysis.summary,
        )
        for score, analysis, pr, repo in scored[:k]
    ]
