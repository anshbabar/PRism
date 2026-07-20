"""The AI review contract.

``AIReview`` is the validated shape every provider must produce (directly or via
the fallback). ``REVIEW_JSON_SCHEMA`` is the JSON Schema handed to the model for
structured outputs.

Structured outputs do not support numeric bounds (``minimum``/``maximum``) or
array-length limits (``maxItems``), so ``risk_score`` range and the "at most 5
concerns" rule are enforced in Pydantic and the reviewer, not in the schema.
"""

from __future__ import annotations

from pydantic import BaseModel

REVIEW_CATEGORIES = [
    "auth",
    "db_schema",
    "api_route",
    "dependency",
    "config_env",
    "missing_tests",
    "large_diff",
    "test_removed",
]


class TopConcern(BaseModel):
    title: str
    detail: str


class SuggestedTest(BaseModel):
    area: str
    reason: str


class AIReview(BaseModel):
    summary: str
    risk_score: int  # 1..5 (clamped by the reviewer)
    risk_categories: list[str]
    top_concerns: list[TopConcern]  # truncated to 5 by the reviewer
    suggested_tests: list[SuggestedTest]
    regression_risks: list[str]
    github_review_markdown: str


# JSON Schema for the model's structured output. Kept in sync with AIReview.
REVIEW_JSON_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "summary",
        "risk_score",
        "risk_categories",
        "top_concerns",
        "suggested_tests",
        "regression_risks",
        "github_review_markdown",
    ],
    "properties": {
        "summary": {"type": "string"},
        "risk_score": {"type": "integer"},
        "risk_categories": {
            "type": "array",
            "items": {"type": "string", "enum": REVIEW_CATEGORIES},
        },
        "top_concerns": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "detail"],
                "properties": {
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                },
            },
        },
        "suggested_tests": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["area", "reason"],
                "properties": {
                    "area": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        },
        "regression_risks": {"type": "array", "items": {"type": "string"}},
        "github_review_markdown": {"type": "string"},
    },
}
