"""Evaluation harness runner.

Runs the full analysis pipeline (parse -> risk -> AI review) over every
benchmark fixture, aggregates the metrics defined in ``metrics.py``, and returns
a JSON-serializable result dict. Also renders a terminal summary table.

The default provider is the configured one (mock offline by default). Pass
``provider_name`` to force a specific provider — the eval smoke test uses
``"mock"`` so it stays network-free and deterministic.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from app.ai.anthropic_provider import AnthropicProvider
from app.ai.mock_provider import MockProvider
from app.ai.prompts import PROMPT_VERSION
from app.ai.provider import ReviewProvider
from app.ai.reviewer import build_review_input, generate_ai_review, get_provider
from app.core.config import Settings, get_settings
from app.diff.parser import parse_diff
from app.diff.risk import assess_risk
from app.eval import metrics as m
from app.ingest.fixtures import list_fixtures, load_fixture

# app/eval/runner.py -> parents[2] == repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_PATH = REPO_ROOT / "eval" / "results" / "latest.json"

_METRIC_KEYS = (
    "valid_json_rate",
    "risk_score_accuracy_within_1",
    "risk_category_precision",
    "risk_category_recall",
    "suggested_test_overlap",
    "average_latency_ms",
)


def _resolve_provider(provider_name: str | None, settings: Settings) -> ReviewProvider:
    if provider_name == "mock":
        return MockProvider()
    if provider_name == "anthropic":
        return AnthropicProvider(settings)
    return get_provider(settings)


def _evaluate_fixture(name: str, settings: Settings, provider: ReviewProvider) -> dict[str, Any]:
    """Run the pipeline on one fixture and return its per-fixture eval row."""
    fixture = load_fixture(name)
    expected = fixture.expected
    expected_categories = list(expected.get("expected_categories", []))
    expected_band = str(expected.get("risk_band", "low"))
    expected_test_areas = list(expected.get("expected_test_areas", []))

    start = perf_counter()
    parsed = parse_diff(fixture.diff_text)
    risk = assess_risk(parsed, raw_text=fixture.diff_text)
    review_input = build_review_input(fixture.metadata, parsed, risk, fixture.diff_text)
    outcome = generate_ai_review(review_input, settings=settings, provider=provider)
    latency_ms = (perf_counter() - start) * 1000.0

    review = outcome.review
    predicted_categories = list(review.risk_categories)
    suggested_areas = [t.area for t in review.suggested_tests]

    tp, fp, fn = m.category_counts(predicted_categories, expected_categories)
    overlap = m.area_overlap(expected_test_areas, suggested_areas)

    return {
        "name": name,
        "ai_status": outcome.status,
        "valid_json": outcome.status == "completed",
        "expected_band": expected_band,
        "expected_score": m.BAND_TO_SCORE[expected_band],
        "deterministic_score": risk.score,
        "predicted_score": review.risk_score,
        "score_within_1": m.score_within_1(review.risk_score, expected_band),
        "expected_categories": sorted(expected_categories),
        "predicted_categories": sorted(predicted_categories),
        "category_tp": tp,
        "category_fp": fp,
        "category_fn": fn,
        "expected_test_areas": expected_test_areas,
        "suggested_test_areas": suggested_areas,
        "test_overlap": None if overlap is None else round(overlap, 4),
        "latency_ms": round(latency_ms, 3),
    }


def run_eval(
    *,
    provider_name: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Evaluate all fixtures and return a JSON-serializable result dict."""
    settings = settings or get_settings()
    provider = _resolve_provider(provider_name, settings)

    rows = [_evaluate_fixture(name, settings, provider) for name in list_fixtures()]

    tp = sum(r["category_tp"] for r in rows)
    fp = sum(r["category_fp"] for r in rows)
    fn = sum(r["category_fn"] for r in rows)
    precision, recall = m.precision_recall(tp, fp, fn)
    overlaps = [r["test_overlap"] for r in rows if r["test_overlap"] is not None]

    metrics = {
        "valid_json_rate": round(m.mean(1.0 if r["valid_json"] else 0.0 for r in rows), 4),
        "risk_score_accuracy_within_1": round(
            m.mean(1.0 if r["score_within_1"] else 0.0 for r in rows), 4
        ),
        "risk_category_precision": round(precision, 4),
        "risk_category_recall": round(recall, 4),
        "suggested_test_overlap": round(m.mean(overlaps), 4),
        "average_latency_ms": round(m.mean(r["latency_ms"] for r in rows), 3),
    }

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "provider": provider.name,
        "model": provider.model,
        "prompt_version": PROMPT_VERSION,
        "fixture_count": len(rows),
        "metrics": metrics,
        "fixtures": rows,
    }


def write_results(result: dict[str, Any], path: Path = DEFAULT_RESULTS_PATH) -> Path:
    """Write the result dict to ``path`` (creating parent dirs) and return it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    return path


def format_table(result: dict[str, Any]) -> str:
    """Render a clean terminal summary: metrics block + per-fixture table."""
    metrics = result["metrics"]
    lines: list[str] = []
    lines.append(
        f"PRism eval — provider={result['provider']} model={result['model']} "
        f"prompt={result['prompt_version']} fixtures={result['fixture_count']}"
    )
    lines.append("")
    lines.append("Metrics")
    lines.append("-" * 44)
    for key in _METRIC_KEYS:
        value = metrics[key]
        rendered = f"{value:.2f} ms" if key == "average_latency_ms" else f"{value:.3f}"
        lines.append(f"  {key:<32} {rendered:>10}")
    lines.append("")

    # Per-fixture table.
    header = f"{'fixture':<26}{'score':>7}{'exp':>5}{'±1':>5}{'cat P/R':>10}{'overlap':>9}{'ms':>8}"
    lines.append("Per fixture")
    lines.append("-" * len(header))
    lines.append(header)
    lines.append("-" * len(header))
    for r in result["fixtures"]:
        tp, fp, fn = r["category_tp"], r["category_fp"], r["category_fn"]
        prec = tp / (tp + fp) if (tp + fp) else 1.0
        rec = tp / (tp + fn) if (tp + fn) else 1.0
        pr = f"{prec:.2f}/{rec:.2f}"
        overlap = "—" if r["test_overlap"] is None else f"{r['test_overlap']:.2f}"
        within = "✓" if r["score_within_1"] else "✗"
        lines.append(
            f"{r['name']:<26}"
            f"{r['predicted_score']:>7}"
            f"{r['expected_score']:>5}"
            f"{within:>5}"
            f"{pr:>10}"
            f"{overlap:>9}"
            f"{r['latency_ms']:>8.2f}"
        )
    return "\n".join(lines)
