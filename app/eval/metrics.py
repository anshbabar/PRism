"""Evaluation metric formulas.

Pure, deterministic functions with no I/O so they can be unit-tested in
isolation. ``runner.py`` calls these to aggregate per-fixture results into the
reported metrics.

Definitions
-----------
- **valid_json_rate**: fraction of fixtures whose *primary* provider path
  produced schema-valid output (``ai.status == "completed"``); heuristic
  fallbacks are excluded.
- **risk_score_accuracy_within_1**: the expected band maps to a canonical score
  (``low=2, medium=3, high=4``); a fixture passes if the final (clamped)
  ``risk_score`` is within 1 of that canonical score.
- **risk_category_precision / recall**: micro-averaged over the fixture set,
  comparing the review's ``risk_categories`` (predicted) to
  ``expected_categories`` (ground truth).
- **suggested_test_overlap**: token-set Jaccard between suggested and expected
  test areas — for each expected area we take the best-matching suggestion, then
  average.
- **average_latency_ms**: mean per-fixture pipeline wall-time in milliseconds.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# Expected risk band -> canonical numeric score, matching diff/risk.py banding
# (low = scores 1-2, medium = 3, high = 4-5).
BAND_TO_SCORE: dict[str, int] = {"low": 2, "medium": 3, "high": 4}

# Small stopword set for test-area token overlap. Kept minimal on purpose:
# topical words like "test"/"migration"/"auth" must survive.
_STOPWORDS = frozenset(
    {"the", "a", "an", "and", "or", "for", "of", "to", "with", "in", "on", "from", "is", "are"}
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> set[str]:
    """Lowercase, split to ``[a-z0-9]+`` tokens, drop stopwords and 1-char tokens."""
    return {
        tok for tok in _TOKEN_RE.findall(text.lower()) if len(tok) >= 2 and tok not in _STOPWORDS
    }


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity of two token sets; 0.0 when both are empty."""
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def score_within_1(predicted_score: int, expected_band: str) -> bool:
    """True if ``predicted_score`` is within 1 of the band's canonical score."""
    expected = BAND_TO_SCORE[expected_band]
    return abs(predicted_score - expected) <= 1


def category_counts(predicted: Iterable[str], expected: Iterable[str]) -> tuple[int, int, int]:
    """Return ``(tp, fp, fn)`` for one fixture's category sets."""
    p, e = set(predicted), set(expected)
    tp = len(p & e)
    fp = len(p - e)
    fn = len(e - p)
    return tp, fp, fn


def precision_recall(tp: int, fp: int, fn: int) -> tuple[float, float]:
    """Micro precision/recall from aggregate counts.

    An empty denominator means "nothing to get wrong" and scores 1.0 (e.g. no
    predictions and no expectations).
    """
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    return precision, recall


def area_overlap(expected_areas: list[str], suggested_areas: list[str]) -> float | None:
    """Mean best-match Jaccard of expected test areas against suggestions.

    For each expected area, take its best token-Jaccard against any suggested
    area, then average across expected areas. Returns ``None`` when there are no
    expected areas (the fixture is then excluded from the aggregate mean).
    """
    if not expected_areas:
        return None
    suggested_tokens = [tokenize(s) for s in suggested_areas]
    per_area: list[float] = []
    for area in expected_areas:
        e_tokens = tokenize(area)
        best = max((jaccard(e_tokens, s) for s in suggested_tokens), default=0.0)
        per_area.append(best)
    return sum(per_area) / len(per_area)


def mean(values: Iterable[float]) -> float:
    """Arithmetic mean; 0.0 for an empty sequence."""
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0
