#!/usr/bin/env python3
"""PRism evaluation harness CLI.

Runs the analysis pipeline over every benchmark fixture, writes the metrics to
``eval/results/latest.json``, and prints a summary table.

Usage::

    python eval/run_eval.py                 # use the configured provider (mock default)
    python eval/run_eval.py --provider mock # force the offline mock provider
    python eval/run_eval.py --check         # also enforce smoke-test invariants (CI)

The reusable logic lives in ``app/eval`` (``metrics.py`` + ``runner.py``); this
file is a thin CLI wrapper so ``import app`` resolves via the installed package.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.eval.runner import DEFAULT_RESULTS_PATH, format_table, run_eval, write_results


def _check_invariants(result: dict) -> list[str]:
    """Return a list of invariant violations (empty == healthy).

    These are the smoke-test guarantees: the mock provider is deterministic and
    schema-valid by construction, so any fallback is a real regression.
    """
    problems: list[str] = []
    metrics = result["metrics"]

    if result["fixture_count"] < 5:
        problems.append(f"expected >= 5 fixtures, ran {result['fixture_count']}")

    if result["provider"] == "mock" and metrics["valid_json_rate"] < 1.0:
        problems.append(
            f"valid_json_rate={metrics['valid_json_rate']} < 1.0 with the mock provider "
            "(a fallback fired — the mock must always be schema-valid)"
        )

    for key, value in metrics.items():
        if value is None:
            problems.append(f"metric {key} is null")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the PRism evaluation harness.")
    parser.add_argument(
        "--provider",
        choices=["mock", "anthropic"],
        default=None,
        help="Force a provider (default: the configured LLM_PROVIDER, mock offline).",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_RESULTS_PATH),
        help="Where to write the results JSON (default: eval/results/latest.json).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Enforce smoke-test invariants and exit non-zero on violation.",
    )
    args = parser.parse_args(argv)

    result = run_eval(provider_name=args.provider)
    out_path = write_results(result, Path(args.out))

    print(format_table(result))
    print(f"\nWrote {out_path}")

    if args.check:
        problems = _check_invariants(result)
        if problems:
            print("\nEval check FAILED:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 1
        print("\nEval check passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
