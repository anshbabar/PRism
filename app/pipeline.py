"""The deterministic analysis pipeline, provider-agnostic and DB-free.

``analyze_diff`` runs parse -> risk -> AI review -> embedding for any
``(metadata, diff_text)`` pair and returns the artifacts. ``analyze_fixture`` is
a thin wrapper over it for loaded fixtures. Both are shared by the analyze
endpoint, the GitHub webhook, and the seeder so persistence and the API agree on
exactly how an analysis is produced. Persistence is intentionally *not* done
here — callers persist the artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from app.ai.reviewer import ReviewOutcome, build_review_input, generate_ai_review
from app.core.config import Settings
from app.diff.models import ParsedDiff
from app.diff.parser import parse_diff
from app.diff.risk import RiskResult, assess_risk
from app.ingest.fixtures import Fixture
from app.retrieval.embeddings import get_embedding_provider
from app.retrieval.store import build_embedding_text


@dataclass
class AnalysisArtifacts:
    parsed: ParsedDiff
    risk: RiskResult
    review: ReviewOutcome
    vector: list[float]
    embedding_provider_name: str
    embedding_model: str
    latency_ms: int


def analyze_diff(metadata: dict[str, Any], diff_text: str, settings: Settings) -> AnalysisArtifacts:
    """Run the full analysis pipeline for a raw diff and return its artifacts.

    ``metadata`` is the PR descriptor (``repo``, ``number``, ``title``, ``author``,
    ``head_sha``, ``base_sha``, ``description``, ``url``); ``diff_text`` is the
    unified diff. Source-agnostic: fixtures and live GitHub PRs share this path.
    """
    start = perf_counter()
    parsed = parse_diff(diff_text)
    risk = assess_risk(parsed, raw_text=diff_text)
    review_input = build_review_input(metadata, parsed, risk, diff_text)
    review = generate_ai_review(review_input, settings=settings)
    latency_ms = int((perf_counter() - start) * 1000)

    embedder = get_embedding_provider(settings)
    vector = embedder.embed([build_embedding_text(metadata, review.review)])[0]

    return AnalysisArtifacts(
        parsed=parsed,
        risk=risk,
        review=review,
        vector=vector,
        embedding_provider_name=embedder.name,
        embedding_model=embedder.model,
        latency_ms=latency_ms,
    )


def analyze_fixture(fixture: Fixture, settings: Settings) -> AnalysisArtifacts:
    """Run the full analysis pipeline for a loaded fixture."""
    return analyze_diff(fixture.metadata, fixture.diff_text, settings)
