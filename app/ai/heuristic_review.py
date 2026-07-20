"""Build a review purely from heuristic signals.

Shared by the mock provider (offline/test path) and the reviewer's safe
fallback (when a real provider fails or returns invalid output). Deterministic
and always schema-valid.
"""

from __future__ import annotations

from typing import Any

from app.ai.provider import ReviewInput

_TEST_HINTS: dict[str, tuple[str, str]] = {
    "auth": (
        "authentication and authorization flows",
        "Cover token issuance, expiry, and permission checks.",
    ),
    "db_schema": (
        "database migration and data integrity",
        "Test the migration up/down and queries against the new schema.",
    ),
    "api_route": (
        "API endpoint contracts",
        "Add request/response tests for the new or changed endpoints.",
    ),
    "dependency": (
        "post-upgrade smoke tests",
        "Exercise the code paths that use the upgraded dependency.",
    ),
    "config_env": (
        "configuration loading",
        "Verify the app boots and parses the new config/env values.",
    ),
    "missing_tests": (
        "unit tests for the changed modules",
        "Add tests covering the code that changed without tests.",
    ),
    "large_diff": (
        "regression tests across touched modules",
        "Broadly exercise the refactored areas for regressions.",
    ),
    "test_removed": (
        "replacement test coverage",
        "Re-add or replace the coverage lost by the deleted tests.",
    ),
}

_REGRESSION_HINTS: dict[str, str] = {
    "auth": "Authentication/authorization behavior may regress for existing users.",
    "db_schema": "Schema change may break existing queries or migrations.",
    "api_route": "API contract change may break existing clients.",
    "dependency": "Dependency upgrade may introduce behavioral or transitive changes.",
    "config_env": "Config/env change may alter runtime behavior across environments.",
    "missing_tests": "Untested code paths raise the chance of undetected regressions.",
    "large_diff": "Wide change surface increases regression risk across modules.",
    "test_removed": "Reduced coverage lowers the chance of catching future regressions.",
}


def _humanize(category: str) -> str:
    return category.replace("_", " ").title()


def build_review(req: ReviewInput) -> dict[str, Any]:
    """Return a schema-valid review dict derived from the heuristic result."""
    risk = req.risk
    pd = req.parsed_diff
    title = str(req.metadata.get("title") or "Pull request")
    cats = sorted({s.category.value for s in risk.signals})

    concerns = [
        {"title": _humanize(s.category.value), "detail": s.detail} for s in risk.signals[:5]
    ]

    tests: list[dict[str, str]] = []
    seen: set[str] = set()
    for c in cats:
        area, reason = _TEST_HINTS.get(
            c, ("changed code paths", "Verify behavior of the modified code.")
        )
        if area not in seen:
            seen.add(area)
            tests.append({"area": area, "reason": reason})
    if not tests:
        tests = [
            {"area": "changed code paths", "reason": "Add or run tests covering the modified code."}
        ]

    regressions = [_REGRESSION_HINTS[c] for c in cats if c in _REGRESSION_HINTS] or [
        "Low regression risk; the change appears isolated."
    ]

    summary = (
        f"{title}: {pd.files_changed} file(s) changed "
        f"(+{pd.total_additions}/-{pd.total_deletions}). "
        f"Heuristic risk {risk.score}/5 ({risk.band}); "
        f"categories: {', '.join(cats) if cats else 'none'}."
    )

    md_lines = ["### PRism review", f"**Risk:** {risk.score}/5 ({risk.band})", "", summary, ""]
    if concerns:
        md_lines.append("**Top concerns**")
        md_lines += [f"- **{c['title']}** — {c['detail']}" for c in concerns]
        md_lines.append("")
    md_lines.append("**Suggested tests**")
    md_lines += [f"- {t['area']}: {t['reason']}" for t in tests]
    md_lines += ["", "_Advisory review — not a merge blocker._"]

    return {
        "summary": summary,
        "risk_score": risk.score,
        "risk_categories": cats,
        "top_concerns": concerns,
        "suggested_tests": tests,
        "regression_risks": regressions,
        "github_review_markdown": "\n".join(md_lines),
    }
