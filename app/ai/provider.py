"""LLM provider abstraction.

A provider takes a :class:`ReviewInput` (PR metadata + parsed diff + heuristic
risk result + a bounded diff excerpt) and returns a raw review dict, which the
reviewer validates against ``AIReview``. Keeping the return type a plain dict
lets the reviewer own validation and fallback uniformly across providers.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from app.diff.models import ParsedDiff
from app.diff.risk import RiskResult


class ReviewInput(BaseModel):
    metadata: dict[str, Any]
    parsed_diff: ParsedDiff
    risk: RiskResult
    diff_excerpt: str
    diff_truncated: bool = False


@runtime_checkable
class ReviewProvider(Protocol):
    """Structural interface every review provider implements."""

    name: str
    model: str

    def generate_review(self, req: ReviewInput) -> dict[str, Any]:
        """Return a raw review dict (validated by the reviewer)."""
        ...
