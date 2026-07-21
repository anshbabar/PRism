"""Read-side database queries for the dashboard.

Separated from ``repository.py`` (the write side) so reads stay simple and
side-effect-free. Summaries are built in one query; detail returns the ORM row
and the route composes the response (including similar-PR retrieval).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Analysis, ChangedFile, PullRequest, Repository


def list_analysis_summaries(session: Session, *, limit: int = 50) -> list[dict[str, Any]]:
    """Return analysis summaries (newest first) for the dashboard list."""
    files_count = (
        select(ChangedFile.analysis_id, func.count().label("n"))
        .group_by(ChangedFile.analysis_id)
        .subquery()
    )
    rows = session.execute(
        select(Analysis, PullRequest, Repository, func.coalesce(files_count.c.n, 0))
        .join(PullRequest, Analysis.pull_request_id == PullRequest.id)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .outerjoin(files_count, files_count.c.analysis_id == Analysis.id)
        .order_by(Analysis.created_at.desc())
        .limit(limit)
    ).all()

    summaries: list[dict[str, Any]] = []
    for analysis, pr, repo, n_files in rows:
        concerns = (analysis.review_json or {}).get("top_concerns") or []
        top_concern = concerns[0]["title"] if concerns else None
        summaries.append(
            {
                "analysis_id": analysis.id,
                "repository": f"{repo.owner}/{repo.name}",
                "number": pr.number,
                "title": pr.title,
                "author": pr.author,
                "status": analysis.status,
                "deterministic_score": analysis.deterministic_score,
                "final_score": analysis.final_score,
                "risk_band": analysis.risk_band,
                "top_concern": top_concern,
                "files_changed": int(n_files),
                "created_at": analysis.created_at,
            }
        )
    return summaries


def get_analysis(session: Session, analysis_id: uuid.UUID) -> Analysis | None:
    """Return the analysis ORM row (or None). Relationships load lazily."""
    return session.get(Analysis, analysis_id)
