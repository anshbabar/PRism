"""Tests for AI review generation: mock provider, fallback, and clamping."""

from __future__ import annotations

from typing import Any

from app.ai.mock_provider import MockProvider
from app.ai.provider import ReviewInput
from app.ai.reviewer import build_review_input, generate_ai_review
from app.ai.schema import AIReview
from app.diff.parser import parse_diff
from app.diff.risk import assess_risk

DIFF = """\
diff --git a/app/auth/tokens.py b/app/auth/tokens.py
index 1111111..2222222 100644
--- a/app/auth/tokens.py
+++ b/app/auth/tokens.py
@@ -8,7 +8,8 @@ def issue_token(user_id: str) -> str:
     payload = {"sub": user_id}
-    payload["exp"] = _now() + 3600
+    payload["exp"] = _now() + ACCESS_TTL_SECONDS
     return _encode(payload)
"""

METADATA = {"title": "Configurable token expiry", "author": "dev", "description": "x"}


def _input() -> ReviewInput:
    parsed = parse_diff(DIFF)
    risk = assess_risk(parsed, raw_text=DIFF)
    return build_review_input(METADATA, parsed, risk, DIFF)


class BadProvider:
    """Returns invalid output to exercise the fallback path."""

    name = "bad"
    model = "bad"

    def generate_review(self, req: ReviewInput) -> dict[str, Any]:
        return {"not": "a valid review"}


class ExtremeScoreProvider:
    """Valid shape but an out-of-range/injected score, to test clamping."""

    name = "extreme"
    model = "extreme"

    def __init__(self, score: int) -> None:
        self._score = score

    def generate_review(self, req: ReviewInput) -> dict[str, Any]:
        return {
            "summary": "s",
            "risk_score": self._score,
            "risk_categories": ["auth"],
            "top_concerns": [{"title": "t", "detail": "d"}],
            "suggested_tests": [{"area": "a", "reason": "r"}],
            "regression_risks": ["r"],
            "github_review_markdown": "# review",
        }


class TooManyConcernsProvider:
    name = "many"
    model = "many"

    def generate_review(self, req: ReviewInput) -> dict[str, Any]:
        base = MockProvider().generate_review(req)
        base["top_concerns"] = [{"title": f"c{i}", "detail": "d"} for i in range(9)]
        return base


def test_mock_provider_produces_valid_completed_review() -> None:
    req = _input()
    outcome = generate_ai_review(req, provider=MockProvider())
    assert outcome.status == "completed"
    assert outcome.provider == "mock"
    assert isinstance(outcome.review, AIReview)
    assert 1 <= outcome.review.risk_score <= 5
    # grounded in heuristics: auth was detected
    assert "auth" in outcome.review.risk_categories


def test_invalid_model_output_falls_back() -> None:
    req = _input()
    outcome = generate_ai_review(req, provider=BadProvider())
    assert outcome.status == "fallback"
    # fallback is still a fully valid review
    assert isinstance(outcome.review, AIReview)
    assert outcome.review.summary
    assert 1 <= outcome.review.risk_score <= 5
    assert outcome.review.risk_score == req.risk.score


def test_score_is_clamped_to_heuristic_plus_minus_one() -> None:
    req = _input()
    heuristic = req.risk.score

    low = generate_ai_review(req, provider=ExtremeScoreProvider(1))
    assert low.review.risk_score >= max(1, heuristic - 1)

    high = generate_ai_review(req, provider=ExtremeScoreProvider(5))
    assert high.review.risk_score <= min(5, heuristic + 1)


def test_top_concerns_truncated_to_five() -> None:
    outcome = generate_ai_review(_input(), provider=TooManyConcernsProvider())
    assert len(outcome.review.top_concerns) <= 5
