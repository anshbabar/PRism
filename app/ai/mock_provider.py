"""Deterministic, offline review provider.

Used for tests and local demos (``LLM_PROVIDER=mock``). Produces a schema-valid
review grounded in the heuristic result — no network, no API key.
"""

from __future__ import annotations

from typing import Any

from app.ai.heuristic_review import build_review
from app.ai.provider import ReviewInput


class MockProvider:
    name = "mock"
    model = "mock"

    def generate_review(self, req: ReviewInput) -> dict[str, Any]:
        return build_review(req)
