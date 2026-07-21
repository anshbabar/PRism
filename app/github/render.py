"""Render a concise, deterministic GitHub review body from a validated review.

We render the *structured* ``AIReview`` fields ourselves rather than posting the
model's free-form ``github_review_markdown`` verbatim. That keeps the comment
format under our control (summary, risk score, at most three concerns, suggested
tests) and means we post model text as inert markdown only — never as anything
that could steer the app. Every body carries a hidden marker so we can tell our
own reviews apart from humans' and post at most one per PR.
"""

from __future__ import annotations

from app.ai.schema import AIReview

# Hidden HTML comment embedded in every PRism review. GitHub renders it invisibly;
# we scan existing reviews for it to enforce "one review per PR" without needing to
# know our own bot login.
PRISM_REVIEW_MARKER = "<!-- prism:review -->"

MAX_CONCERNS = 3  # GitHub review rule: top 3 concerns maximum
MAX_TESTS = 5

_BANDS = {1: "low", 2: "low", 3: "medium", 4: "high", 5: "high"}


def _band(score: int) -> str:
    return _BANDS.get(score, "medium")


def render_review_comment(review: AIReview) -> str:
    """Build the markdown body for a PRism PR review.

    Includes: summary, risk score (with band), the top 3 concerns, and suggested
    tests. Intentionally omits line-level comments — reliable line mapping is out
    of scope for the MVP (see CLAUDE.md GitHub review rules).
    """
    score = review.risk_score
    lines: list[str] = [
        PRISM_REVIEW_MARKER,
        "## 🔍 PRism review",
        "",
        review.summary.strip() or "_No summary available._",
        "",
        f"**Risk score:** {score}/5 ({_band(score)})",
    ]

    concerns = review.top_concerns[:MAX_CONCERNS]
    if concerns:
        lines += ["", "**Top concerns**"]
        for i, c in enumerate(concerns, start=1):
            detail = f" — {c.detail.strip()}" if c.detail.strip() else ""
            lines.append(f"{i}. **{c.title.strip()}**{detail}")

    tests = review.suggested_tests[:MAX_TESTS]
    if tests:
        lines += ["", "**Suggested tests**"]
        for t in tests:
            reason = f" — {t.reason.strip()}" if t.reason.strip() else ""
            lines.append(f"- **{t.area.strip()}**{reason}")

    lines += [
        "",
        "---",
        "<sub>🤖 Automated review by PRism. AI-generated from the diff; advisory only.</sub>",
    ]
    return "\n".join(lines)
