"""Evaluation harness for PRism.

Runs the analysis pipeline over the benchmark fixtures and computes quality
metrics (see ``metrics.py`` for the exact formulas). ``runner.py`` orchestrates
a run and produces a JSON-serializable result; the ``eval/run_eval.py`` CLI is a
thin wrapper around it.
"""
