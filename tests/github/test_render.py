"""Unit tests for rendering the GitHub review comment body."""

from __future__ import annotations

from app.ai.schema import AIReview, SuggestedTest, TopConcern
from app.github.render import PRISM_REVIEW_MARKER, render_review_comment


def _review(**overrides: object) -> AIReview:
    base: dict[str, object] = {
        "summary": "Adds refresh-token handling to auth.",
        "risk_score": 4,
        "risk_categories": ["auth"],
        "top_concerns": [TopConcern(title=f"C{i}", detail=f"detail {i}") for i in range(5)],
        "suggested_tests": [SuggestedTest(area="auth flow", reason="cover refresh path")],
        "regression_risks": ["existing sessions"],
        "github_review_markdown": "ignored — we render our own",
    }
    base.update(overrides)
    return AIReview(**base)  # type: ignore[arg-type]


def test_render_starts_with_marker_and_includes_required_sections() -> None:
    body = render_review_comment(_review())
    assert body.startswith(PRISM_REVIEW_MARKER)
    assert "Adds refresh-token handling" in body  # summary
    assert "**Risk score:** 4/5 (high)" in body  # score + band
    assert "**Top concerns**" in body
    assert "**Suggested tests**" in body
    assert "cover refresh path" in body


def test_render_caps_concerns_at_three() -> None:
    body = render_review_comment(_review())
    # Five concerns supplied; only the first three (C0, C1, C2) should render.
    assert "C2" in body
    assert "C3" not in body


def test_render_band_mapping() -> None:
    assert "2/5 (low)" in render_review_comment(_review(risk_score=2))
    assert "3/5 (medium)" in render_review_comment(_review(risk_score=3))
    assert "5/5 (high)" in render_review_comment(_review(risk_score=5))


def test_render_handles_empty_summary() -> None:
    body = render_review_comment(_review(summary=""))
    assert "_No summary available._" in body
