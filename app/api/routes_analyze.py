"""Analysis routes.

Milestone 2: analyze a saved local fixture — parse its diff and run the
deterministic risk heuristics. The LLM review and persistence land in later
milestones.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.diff.models import ParsedDiff
from app.diff.parser import parse_diff
from app.diff.risk import RiskResult, assess_risk
from app.ingest.fixtures import (
    FixtureNotFound,
    InvalidFixtureName,
    load_fixture,
)

router = APIRouter(prefix="/api/analyze", tags=["analyze"])


class LocalFixtureRequest(BaseModel):
    name: str


class LocalFixtureResponse(BaseModel):
    name: str
    metadata: dict[str, Any]
    parsed_diff: ParsedDiff
    risk: RiskResult


@router.post("/local-fixture", response_model=LocalFixtureResponse)
def analyze_local_fixture(req: LocalFixtureRequest) -> LocalFixtureResponse:
    """Parse + risk-assess a local PR fixture by name."""
    try:
        fixture = load_fixture(req.name)
    except InvalidFixtureName as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FixtureNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    parsed = parse_diff(fixture.diff_text)
    risk = assess_risk(parsed, raw_text=fixture.diff_text)

    return LocalFixtureResponse(
        name=fixture.name,
        metadata=fixture.metadata,
        parsed_diff=parsed,
        risk=risk,
    )
