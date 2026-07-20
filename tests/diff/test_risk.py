"""Tests for the rule-based risk heuristics."""

from __future__ import annotations

from app.diff.models import DiffFile, ParsedDiff
from app.diff.parser import is_test_path
from app.diff.risk import RiskCategory, assess_risk, detect_signals


def mkfile(path: str, status: str = "modified", additions: int = 1, deletions: int = 0) -> DiffFile:
    base = path.rsplit("/", 1)[-1]
    ext = base.rsplit(".", 1)[-1].lower() if "." in base else ""
    return DiffFile(
        path=path,
        status=status,  # type: ignore[arg-type]
        additions=additions,
        deletions=deletions,
        extension=ext,
        is_test=is_test_path(path),
    )


def mkdiff(files: list[DiffFile]) -> ParsedDiff:
    return ParsedDiff(
        files=files,
        files_changed=len(files),
        total_additions=sum(f.additions for f in files),
        total_deletions=sum(f.deletions for f in files),
    )


def cats(diff: ParsedDiff, raw_text: str = "") -> set[RiskCategory]:
    return {s.category for s in detect_signals(diff, raw_text=raw_text)}


# --- individual detectors -------------------------------------------------


def test_auth_detected_by_path() -> None:
    diff = mkdiff([mkfile("app/auth/session.py"), mkfile("tests/test_session.py", "added")])
    assert cats(diff) == {RiskCategory.AUTH}


def test_no_auth_on_ordinary_path() -> None:
    diff = mkdiff([mkfile("app/services/orders.py"), mkfile("tests/test_orders.py", "added")])
    assert RiskCategory.AUTH not in cats(diff)


def test_db_schema_by_path_and_content() -> None:
    assert RiskCategory.DB_SCHEMA in cats(mkdiff([mkfile("migrations/001_init.sql", "added")]))
    assert RiskCategory.DB_SCHEMA in cats(
        mkdiff([mkfile("app/store.py")]), raw_text="+CREATE TABLE foo (id int);"
    )


def test_api_route_by_path_and_content() -> None:
    assert RiskCategory.API_ROUTE in cats(mkdiff([mkfile("app/api/routes_x.py", "added")]))
    assert RiskCategory.API_ROUTE in cats(
        mkdiff([mkfile("app/handlers.py")]), raw_text="+@router.get('/')"
    )


def test_dependency_not_also_config() -> None:
    # pyproject.toml is a dependency file, not a generic config file.
    assert cats(mkdiff([mkfile("pyproject.toml")])) == {RiskCategory.DEPENDENCY}


def test_config_env() -> None:
    assert RiskCategory.CONFIG_ENV in cats(mkdiff([mkfile(".env")]))
    assert RiskCategory.CONFIG_ENV in cats(mkdiff([mkfile("config/app.yaml", "added")]))


def test_missing_tests_when_code_without_tests() -> None:
    assert RiskCategory.MISSING_TESTS in cats(mkdiff([mkfile("app/x.py")]))


def test_no_missing_tests_when_test_present() -> None:
    diff = mkdiff([mkfile("app/x.py"), mkfile("tests/test_x.py", "added")])
    assert RiskCategory.MISSING_TESTS not in cats(diff)


def test_deleting_a_test_is_test_removed_not_missing_tests() -> None:
    diff = mkdiff([mkfile("tests/test_x.py", "deleted", additions=0, deletions=5)])
    result = cats(diff)
    assert RiskCategory.TEST_REMOVED in result
    assert RiskCategory.MISSING_TESTS not in result


def test_large_diff_by_file_count_and_by_lines() -> None:
    many = mkdiff([mkfile(f"app/services/mod{i}.py") for i in range(8)])
    assert RiskCategory.LARGE_DIFF in cats(many)

    big = mkdiff([mkfile("app/big.py", additions=200)])
    assert RiskCategory.LARGE_DIFF in cats(big)


def test_small_change_is_not_large() -> None:
    diff = mkdiff([mkfile("app/small.py"), mkfile("tests/test_small.py", "added")])
    assert RiskCategory.LARGE_DIFF not in cats(diff)


# --- scoring --------------------------------------------------------------


def test_safe_change_scores_low() -> None:
    result = assess_risk(mkdiff([mkfile("README.md")]))
    assert result.score == 1
    assert result.band == "low"
    assert result.signals == []


def test_auth_alone_is_medium() -> None:
    diff = mkdiff([mkfile("app/auth/x.py"), mkfile("tests/test_x.py", "added")])
    result = assess_risk(diff)
    assert result.score == 3
    assert result.band == "medium"


def test_auth_plus_schema_is_high() -> None:
    diff = mkdiff(
        [
            mkfile("app/auth/x.py"),
            mkfile("migrations/001.sql", "added"),
            mkfile("tests/test_x.py", "added"),
        ]
    )
    result = assess_risk(diff)
    assert cats(diff) == {RiskCategory.AUTH, RiskCategory.DB_SCHEMA}
    assert result.score == 4
    assert result.band == "high"
