"""Unit tests for the evaluation metric formulas."""

from __future__ import annotations

import pytest
from app.eval import metrics as m


def test_tokenize_lowercases_and_drops_stopwords_and_short_tokens() -> None:
    assert m.tokenize("Authentication and Token Expiry") == {
        "authentication",
        "token",
        "expiry",
    }
    # Punctuation is a separator; 1-char tokens and stopwords are dropped.
    assert m.tokenize("issued-at claim, a X") == {"issued", "at", "claim"}


def test_jaccard_basic_and_empty() -> None:
    assert m.jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert m.jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)
    assert m.jaccard(set(), set()) == 0.0
    assert m.jaccard({"a"}, set()) == 0.0


# Canonical scores: low=2, medium=3, high=4. "within 1" == |predicted - canonical| <= 1.
@pytest.mark.parametrize(
    ("score", "band", "expected"),
    [
        (1, "low", True),
        (2, "low", True),
        (4, "low", False),
        (2, "medium", True),
        (3, "medium", True),
        (5, "medium", False),
        (3, "high", True),
        (5, "high", True),
        (2, "high", False),
    ],
)
def test_score_within_1(score: int, band: str, expected: bool) -> None:
    assert m.score_within_1(score, band) is expected


def test_category_counts_and_precision_recall() -> None:
    # predicted {a,b,c}, expected {b,c,d}: tp=2 (b,c), fp=1 (a), fn=1 (d)
    tp, fp, fn = m.category_counts(["a", "b", "c"], ["b", "c", "d"])
    assert (tp, fp, fn) == (2, 1, 1)
    precision, recall = m.precision_recall(tp, fp, fn)
    assert precision == pytest.approx(2 / 3)
    assert recall == pytest.approx(2 / 3)


def test_precision_recall_empty_denominator_is_one() -> None:
    assert m.precision_recall(0, 0, 0) == (1.0, 1.0)


def test_area_overlap_none_when_no_expected() -> None:
    assert m.area_overlap([], ["anything"]) is None


def test_area_overlap_best_match_average() -> None:
    expected = ["database migration integrity", "logging output format"]
    suggested = ["database migration and data integrity"]
    # area 1: jaccard({database,migration,integrity},{database,migration,data,integrity}) = 3/4
    # area 2: no token overlap -> 0.0
    result = m.area_overlap(expected, suggested)
    assert result == pytest.approx((0.75 + 0.0) / 2)


def test_mean_empty_is_zero() -> None:
    assert m.mean([]) == 0.0
    assert m.mean([1.0, 2.0, 3.0]) == pytest.approx(2.0)
