"""Serve the latest evaluation results to the dashboard.

Reads the committed ``eval/results/latest.json`` produced by ``make eval``. The
dashboard's eval page renders this verbatim.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from app.eval.runner import DEFAULT_RESULTS_PATH

router = APIRouter(prefix="/api/eval", tags=["eval"])


@router.get("/latest")
def get_latest_eval() -> dict[str, Any]:
    """Return the latest eval results, or 404 if the harness hasn't been run."""
    if not DEFAULT_RESULTS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="No eval results found. Run `make eval` to generate them.",
        )
    return json.loads(DEFAULT_RESULTS_PATH.read_text())
