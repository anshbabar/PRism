"""AI review orchestration.

Selects a provider, validates its output against ``AIReview``, applies
defense-in-depth (clamp ``risk_score`` to the heuristic score +/- 1, truncate
concerns to 5), and falls back to a heuristic-built review on any failure.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.ai.anthropic_provider import AnthropicProvider
from app.ai.heuristic_review import build_review
from app.ai.mock_provider import MockProvider
from app.ai.prompts import PROMPT_VERSION
from app.ai.provider import ReviewInput, ReviewProvider
from app.ai.schema import AIReview
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.diff.models import ParsedDiff
from app.diff.risk import RiskResult

logger = get_logger("app.ai.reviewer")

MAX_DIFF_CHARS = 8000
MAX_CONCERNS = 5


class ReviewOutcome(BaseModel):
    review: AIReview
    status: Literal["completed", "fallback"]
    provider: str
    model: str
    prompt_version: str = PROMPT_VERSION


def build_review_input(
    metadata: dict,
    parsed: ParsedDiff,
    risk: RiskResult,
    raw_text: str,
) -> ReviewInput:
    """Bound the raw diff and package the inputs for a provider."""
    truncated = len(raw_text) > MAX_DIFF_CHARS
    excerpt = raw_text[:MAX_DIFF_CHARS] + ("\n... [diff truncated]" if truncated else "")
    return ReviewInput(
        metadata=metadata,
        parsed_diff=parsed,
        risk=risk,
        diff_excerpt=excerpt,
        diff_truncated=truncated,
    )


def get_provider(settings: Settings) -> ReviewProvider:
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(settings)
    return MockProvider()


def _clamp(score: int, heuristic_score: int) -> int:
    """Clamp the model score to the heuristic score +/- 1, within [1, 5].

    An injected instruction cannot pull the score far from the deterministic
    floor — the heuristics are the safety net the model can't argue past.
    """
    lo = max(1, heuristic_score - 1)
    hi = min(5, heuristic_score + 1)
    return max(lo, min(hi, score))


def generate_ai_review(
    req: ReviewInput,
    *,
    settings: Settings | None = None,
    provider: ReviewProvider | None = None,
) -> ReviewOutcome:
    """Produce a validated, safety-clamped AI review, or a safe fallback."""
    settings = settings or get_settings()
    provider = provider or get_provider(settings)
    heuristic_score = req.risk.score

    try:
        raw = provider.generate_review(req)
        review = AIReview.model_validate(raw)
        review.risk_score = _clamp(review.risk_score, heuristic_score)
        review.top_concerns = review.top_concerns[:MAX_CONCERNS]
        return ReviewOutcome(
            review=review,
            status="completed",
            provider=provider.name,
            model=provider.model,
        )
    except Exception as exc:  # invalid output, provider error, missing package, etc.
        logger.warning(
            "AI review failed; using heuristic fallback",
            extra={"provider": provider.name, "error": str(exc)},
        )
        review = AIReview.model_validate(build_review(req))
        review.risk_score = _clamp(review.risk_score, heuristic_score)
        review.top_concerns = review.top_concerns[:MAX_CONCERNS]
        return ReviewOutcome(
            review=review,
            status="fallback",
            provider=provider.name,
            model=provider.model,
        )
