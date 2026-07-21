"""Integration tests for the evaluation runner over the real fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from app.eval.runner import format_table, run_eval, write_results
from app.ingest.fixtures import list_fixtures

_METRIC_KEYS = {
    "valid_json_rate",
    "risk_score_accuracy_within_1",
    "risk_category_precision",
    "risk_category_recall",
    "suggested_test_overlap",
    "average_latency_ms",
}


def test_run_eval_shape_and_invariants() -> None:
    result = run_eval(provider_name="mock")

    assert result["provider"] == "mock"
    assert result["fixture_count"] == len(list_fixtures())
    assert set(result["metrics"]) == _METRIC_KEYS

    metrics = result["metrics"]
    # The mock provider is deterministic and schema-valid by construction, and
    # the fixtures' expected labels are authored to the deterministic detector.
    assert metrics["valid_json_rate"] == 1.0
    assert metrics["risk_score_accuracy_within_1"] == 1.0
    assert metrics["risk_category_precision"] == 1.0
    assert metrics["risk_category_recall"] == 1.0
    # Overlap is a soft metric against generic mock suggestions: strictly in (0, 1).
    assert 0.0 < metrics["suggested_test_overlap"] < 1.0
    assert metrics["average_latency_ms"] >= 0.0


def test_every_fixture_row_is_complete() -> None:
    result = run_eval(provider_name="mock")
    required = {
        "name",
        "ai_status",
        "valid_json",
        "expected_band",
        "expected_score",
        "deterministic_score",
        "predicted_score",
        "score_within_1",
        "expected_categories",
        "predicted_categories",
        "category_tp",
        "category_fp",
        "category_fn",
        "expected_test_areas",
        "suggested_test_areas",
        "test_overlap",
        "latency_ms",
    }
    assert result["fixtures"], "expected at least one fixture row"
    for row in result["fixtures"]:
        assert required <= set(row), row.get("name")
        assert 1 <= row["predicted_score"] <= 5
        assert row["ai_status"] in {"completed", "fallback"}


def test_write_results_roundtrip(tmp_path: Path) -> None:
    result = run_eval(provider_name="mock")
    out = tmp_path / "nested" / "latest.json"
    written = write_results(result, out)

    assert written == out
    assert out.exists()
    loaded = json.loads(out.read_text())
    assert loaded["metrics"] == result["metrics"]
    assert loaded["fixture_count"] == result["fixture_count"]


def test_format_table_mentions_every_metric() -> None:
    table = format_table(run_eval(provider_name="mock"))
    for key in _METRIC_KEYS:
        assert key in table
    # Header and at least one fixture name are present.
    assert "Per fixture" in table
    assert "bump-dependencies" in table
