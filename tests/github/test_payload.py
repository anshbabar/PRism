"""Unit tests for parsing GitHub ``pull_request`` event payloads."""

from __future__ import annotations

from app.github.webhook import (
    HANDLED_ACTIONS,
    pr_metadata_from_payload,
    pr_ref_from_payload,
)

from tests.github.support import make_pr_payload


def test_handled_actions_are_exactly_the_three() -> None:
    assert HANDLED_ACTIONS == frozenset({"opened", "synchronize", "reopened"})


def test_pr_ref_extracts_owner_repo_number_installation() -> None:
    ref = pr_ref_from_payload(make_pr_payload(repo="octo/hello", number=7, installation_id=42))
    assert (ref.owner, ref.repo, ref.number, ref.installation_id) == ("octo", "hello", 7, 42)
    assert ref.full_name == "octo/hello"


def test_pr_ref_handles_missing_installation() -> None:
    payload = make_pr_payload(installation_id=None)
    assert pr_ref_from_payload(payload).installation_id is None


def test_pr_metadata_maps_pipeline_fields() -> None:
    md = pr_metadata_from_payload(
        make_pr_payload(
            repo="octo/hello",
            number=7,
            title="Add refresh tokens",
            author="octocat",
            head_sha="dead",
            base_sha="cafe",
        )
    )
    assert md["repo"] == "octo/hello"
    assert md["number"] == 7
    assert md["title"] == "Add refresh tokens"
    assert md["author"] == "octocat"
    assert md["head_sha"] == "dead"
    assert md["base_sha"] == "cafe"
    assert md["url"].endswith("/pull/7")


def test_pr_metadata_tolerates_missing_fields() -> None:
    md = pr_metadata_from_payload({"action": "opened"})
    assert md["repo"] == "unknown/unknown"
    assert md["number"] == 0
    assert md["title"] == "" and md["author"] == ""
