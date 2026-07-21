"""Persistence for a single analysis run.

``persist_analysis`` writes one analysis and its children (changed files +
embedding) in a single transaction, creating the parent repository / pull
request rows on first sight. A new run against the same PR head produces a new
``analyses`` row (re-analysis history), never a duplicate PR.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Analysis, ChangedFile, Embedding, PullRequest, Repository
from app.diff.models import ParsedDiff
from app.diff.risk import RiskResult


@dataclass
class PersistResult:
    analysis_id: uuid.UUID
    repository_id: uuid.UUID
    pull_request_id: uuid.UUID
    vector: list[float]


def _split_repo(metadata: dict[str, Any]) -> tuple[str, str]:
    """Split ``metadata['repo']`` ("owner/name") into ``(owner, name)``."""
    repo = str(metadata.get("repo") or "unknown/unknown")
    owner, _, name = repo.partition("/")
    return owner or "unknown", name or "unknown"


def get_or_create_repository(session: Session, owner: str, name: str) -> Repository:
    repo = session.scalar(
        select(Repository).where(Repository.owner == owner, Repository.name == name)
    )
    if repo is None:
        repo = Repository(owner=owner, name=name)
        session.add(repo)
        session.flush()
    return repo


def get_or_create_pull_request(
    session: Session, repository: Repository, metadata: dict[str, Any]
) -> PullRequest:
    number = int(metadata.get("number") or 0)
    head_sha = str(metadata.get("head_sha") or "")
    pr = session.scalar(
        select(PullRequest).where(
            PullRequest.repository_id == repository.id,
            PullRequest.number == number,
            PullRequest.head_sha == head_sha,
        )
    )
    if pr is None:
        pr = PullRequest(
            repository_id=repository.id,
            number=number,
            title=str(metadata.get("title") or ""),
            author=str(metadata.get("author") or ""),
            base_sha=str(metadata.get("base_sha") or ""),
            head_sha=head_sha,
            description=str(metadata.get("description") or ""),
            url=str(metadata.get("url") or ""),
        )
        session.add(pr)
        session.flush()
    return pr


def persist_analysis(
    session: Session,
    *,
    metadata: dict[str, Any],
    parsed: ParsedDiff,
    risk: RiskResult,
    review_outcome: Any,  # app.ai.reviewer.ReviewOutcome (avoids an import cycle)
    vector: list[float],
    embedding_provider_name: str,
    embedding_model: str,
    latency_ms: int | None = None,
) -> PersistResult:
    """Persist an analysis and its children; commit and return identifiers."""
    owner, name = _split_repo(metadata)
    repository = get_or_create_repository(session, owner, name)
    pr = get_or_create_pull_request(session, repository, metadata)

    review = review_outcome.review
    analysis = Analysis(
        pull_request_id=pr.id,
        status=review_outcome.status,
        deterministic_score=risk.score,
        final_score=review.risk_score,
        risk_band=risk.band,
        summary=review.summary,
        risk_json=risk.model_dump(mode="json"),
        review_json=review.model_dump(mode="json"),
        provider=review_outcome.provider,
        model=review_outcome.model,
        prompt_version=review_outcome.prompt_version,
        latency_ms=latency_ms,
    )
    session.add(analysis)
    session.flush()

    for f in parsed.files:
        session.add(
            ChangedFile(
                analysis_id=analysis.id,
                path=f.path,
                status=f.status,
                additions=f.additions,
                deletions=f.deletions,
                hunks_json=[h.model_dump(mode="json") for h in f.hunks],
            )
        )

    session.add(
        Embedding(
            analysis_id=analysis.id,
            kind="summary",
            dim=len(vector),
            provider=embedding_provider_name,
            model=embedding_model,
            vector=vector,
        )
    )

    session.commit()
    return PersistResult(
        analysis_id=analysis.id,
        repository_id=repository.id,
        pull_request_id=pr.id,
        vector=vector,
    )
