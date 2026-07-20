"""Rule-based (deterministic) risk heuristics.

These run with no LLM. Each detector inspects the parsed diff and emits zero or
more :class:`RiskSignal`s; signals are combined into a 1-5 score with an
explainable rationale. The LLM stage (a later milestone) refines this within a
clamp — it never replaces it.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

from app.diff.models import DiffFile, ParsedDiff


class RiskCategory(StrEnum):
    AUTH = "auth"
    DB_SCHEMA = "db_schema"
    API_ROUTE = "api_route"
    DEPENDENCY = "dependency"
    CONFIG_ENV = "config_env"
    MISSING_TESTS = "missing_tests"
    LARGE_DIFF = "large_diff"
    TEST_REMOVED = "test_removed"


# Severity weight per category (1 = low, 3 = high).
_SEVERITY: dict[RiskCategory, int] = {
    RiskCategory.AUTH: 3,
    RiskCategory.DB_SCHEMA: 3,
    RiskCategory.TEST_REMOVED: 3,
    RiskCategory.API_ROUTE: 2,
    RiskCategory.DEPENDENCY: 2,
    RiskCategory.CONFIG_ENV: 2,
    RiskCategory.MISSING_TESTS: 2,
    RiskCategory.LARGE_DIFF: 1,
}

Band = Literal["low", "medium", "high"]


class RiskSignal(BaseModel):
    category: RiskCategory
    severity: int
    file_path: str | None
    detail: str


class RiskResult(BaseModel):
    score: int  # 1..5
    band: Band
    signals: list[RiskSignal]
    rationale: str


# --- matchers -------------------------------------------------------------

_AUTH_TOKENS = (
    "auth",
    "login",
    "logout",
    "session",
    "password",
    "jwt",
    "oauth",
    "token",
    "credential",
    "permission",
    "security",
)

_DEP_FILES = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "poetry.lock",
    "pipfile",
    "pipfile.lock",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "go.mod",
    "go.sum",
    "gemfile",
    "gemfile.lock",
    "cargo.toml",
    "cargo.lock",
}

_CONFIG_EXTS = {"yaml", "yml", "ini", "cfg", "conf", "toml"}
_CONFIG_FILES = {"docker-compose.yml", "docker-compose.yaml", "dockerfile"}

_CODE_EXTS = {"py", "ts", "tsx", "js", "jsx", "go", "java", "rb", "rs", "kt", "cs", "php"}

# Thresholds for "large diff".
_LARGE_FILES = 8
_LARGE_LINES = 200

_SQL_DDL_RE = re.compile(r"\b(create|alter|drop)\s+table\b", re.IGNORECASE)
_API_DECORATOR_RE = re.compile(r"@(app|router)\.(get|post|put|patch|delete)\b|APIRouter\(")


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1].lower()


def _is_dependency_file(path: str) -> bool:
    return _basename(path) in _DEP_FILES


def _is_config_file(f: DiffFile) -> bool:
    base = _basename(f.path)
    if _is_dependency_file(f.path):
        return False  # dependency files are their own category
    if base.startswith(".env"):
        return True
    if base in _CONFIG_FILES:
        return True
    return f.extension in _CONFIG_EXTS


def _is_code_file(f: DiffFile) -> bool:
    return f.extension in _CODE_EXTS and not f.is_test


# --- detectors ------------------------------------------------------------


def detect_signals(diff: ParsedDiff, *, raw_text: str = "") -> list[RiskSignal]:
    """Run all heuristics and return the raised signals.

    ``raw_text`` (the original diff text) is scanned for content-based rules
    (SQL DDL, route decorators); path-based rules use the parsed model.
    """
    signals: list[RiskSignal] = []

    changed_test_files = [f for f in diff.files if f.is_test]
    changed_code_files = [f for f in diff.files if _is_code_file(f)]

    # auth (path-based)
    for f in diff.files:
        if any(tok in f.path.lower() for tok in _AUTH_TOKENS):
            signals.append(
                RiskSignal(
                    category=RiskCategory.AUTH,
                    severity=_SEVERITY[RiskCategory.AUTH],
                    file_path=f.path,
                    detail=f"Touches an auth/security-related path: {f.path}",
                )
            )
            break

    # db_schema (path + content)
    db_file = None
    for f in diff.files:
        base = _basename(f.path)
        if (
            f.extension == "sql"
            or "migration" in f.path.lower()
            or "alembic" in f.path.lower()
            or base in {"models.py", "model.py", "schema.py", "schema.sql"}
        ):
            db_file = f
            break
    if db_file is None and _SQL_DDL_RE.search(raw_text):
        db_file = next((f for f in diff.files), None)
    if db_file is not None or _SQL_DDL_RE.search(raw_text):
        signals.append(
            RiskSignal(
                category=RiskCategory.DB_SCHEMA,
                severity=_SEVERITY[RiskCategory.DB_SCHEMA],
                file_path=db_file.path if db_file else None,
                detail="Database/schema change (migration, model, or SQL DDL).",
            )
        )

    # api_route (path + content)
    api_file = next(
        (
            f
            for f in diff.files
            if any(seg in f.path.lower() for seg in ("routes", "router", "/api/", "endpoints"))
        ),
        None,
    )
    if api_file is not None or _API_DECORATOR_RE.search(raw_text):
        signals.append(
            RiskSignal(
                category=RiskCategory.API_ROUTE,
                severity=_SEVERITY[RiskCategory.API_ROUTE],
                file_path=api_file.path if api_file else None,
                detail="API route/endpoint change.",
            )
        )

    # dependency
    dep_file = next((f for f in diff.files if _is_dependency_file(f.path)), None)
    if dep_file is not None:
        signals.append(
            RiskSignal(
                category=RiskCategory.DEPENDENCY,
                severity=_SEVERITY[RiskCategory.DEPENDENCY],
                file_path=dep_file.path,
                detail=f"Dependency manifest changed: {dep_file.path}",
            )
        )

    # config_env
    cfg_file = next((f for f in diff.files if _is_config_file(f)), None)
    if cfg_file is not None:
        signals.append(
            RiskSignal(
                category=RiskCategory.CONFIG_ENV,
                severity=_SEVERITY[RiskCategory.CONFIG_ENV],
                file_path=cfg_file.path,
                detail=f"Config/env file changed: {cfg_file.path}",
            )
        )

    # test_removed
    for f in diff.files:
        if f.is_test and f.status == "deleted":
            signals.append(
                RiskSignal(
                    category=RiskCategory.TEST_REMOVED,
                    severity=_SEVERITY[RiskCategory.TEST_REMOVED],
                    file_path=f.path,
                    detail=f"Test file deleted: {f.path}",
                )
            )
            break

    # missing_tests: code changed but no test touched
    if changed_code_files and not changed_test_files:
        signals.append(
            RiskSignal(
                category=RiskCategory.MISSING_TESTS,
                severity=_SEVERITY[RiskCategory.MISSING_TESTS],
                file_path=None,
                detail="Code changed but no test files were added or modified.",
            )
        )

    # large_diff
    total_changed = diff.total_additions + diff.total_deletions
    if diff.files_changed >= _LARGE_FILES or total_changed >= _LARGE_LINES:
        signals.append(
            RiskSignal(
                category=RiskCategory.LARGE_DIFF,
                severity=_SEVERITY[RiskCategory.LARGE_DIFF],
                file_path=None,
                detail=(
                    f"Large change: {diff.files_changed} files, {total_changed} lines changed."
                ),
            )
        )

    return signals


def _bucket(total: int) -> int:
    if total <= 0:
        return 1
    if total <= 2:
        return 2
    if total <= 4:
        return 3
    if total <= 6:
        return 4
    return 5


def _band(score: int) -> Band:
    if score <= 2:
        return "low"
    if score == 3:
        return "medium"
    return "high"


def score_signals(signals: list[RiskSignal]) -> RiskResult:
    """Combine signals into a 1-5 score with an explainable rationale."""
    total = sum(s.severity for s in signals)
    score = _bucket(total)
    band = _band(score)

    if signals:
        cats = ", ".join(sorted({s.category.value for s in signals}))
        rationale = f"Risk {score}/5 ({band}). Signals: {cats}."
    else:
        rationale = f"Risk {score}/5 ({band}). No risk signals detected."

    return RiskResult(score=score, band=band, signals=signals, rationale=rationale)


def assess_risk(diff: ParsedDiff, *, raw_text: str = "") -> RiskResult:
    """Full deterministic assessment: detect signals, then score them."""
    return score_signals(detect_signals(diff, raw_text=raw_text))
