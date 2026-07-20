"""Tests for the local-fixture analysis endpoint and the fixtures themselves."""

from __future__ import annotations

import pytest
from app.ingest.fixtures import list_fixtures, load_fixture
from fastapi.testclient import TestClient

ENDPOINT = "/api/analyze/local-fixture"


def test_analyze_valid_fixture_shape(client: TestClient) -> None:
    resp = client.post(ENDPOINT, json={"name": "auth-token-expiry"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "auth-token-expiry"
    assert body["parsed_diff"]["files_changed"] >= 1
    assert 1 <= body["risk"]["score"] <= 5
    assert body["risk"]["band"] in {"low", "medium", "high"}


def test_invalid_fixture_name_returns_400(client: TestClient) -> None:
    resp = client.post(ENDPOINT, json={"name": "../etc/passwd"})
    assert resp.status_code == 400


def test_unknown_fixture_returns_404(client: TestClient) -> None:
    resp = client.post(ENDPOINT, json={"name": "does-not-exist"})
    assert resp.status_code == 404


def test_there_are_at_least_five_fixtures() -> None:
    assert len(list_fixtures()) >= 5


@pytest.mark.parametrize("name", list_fixtures())
def test_fixture_matches_expected(client: TestClient, name: str) -> None:
    """Each fixture's detected categories and band match its expected.json."""
    expected = load_fixture(name).expected

    resp = client.post(ENDPOINT, json={"name": name})
    assert resp.status_code == 200
    body = resp.json()

    detected = {s["category"] for s in body["risk"]["signals"]}
    assert detected == set(expected["expected_categories"]), name
    assert body["risk"]["band"] == expected["risk_band"], name
