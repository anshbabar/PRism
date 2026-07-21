"""Endpoint tests for Milestone 5: persistence + similar-PR retrieval."""

from __future__ import annotations

from fastapi.testclient import TestClient

ENDPOINT = "/api/analyze/local-fixture"


def test_first_analysis_persists_with_no_similar(client: TestClient) -> None:
    body = client.post(ENDPOINT, json={"name": "add-orders-table"}).json()
    assert body["persisted"] is True
    assert body["analysis_id"]
    assert body["similar"] == []  # nothing prior in a fresh database


def test_related_pr_shows_up_as_similar(client: TestClient) -> None:
    # Seed one orders PR, then analyze a related orders PR in the same repo.
    client.post(ENDPOINT, json={"name": "add-orders-table"})
    body = client.post(ENDPOINT, json={"name": "add-orders-api-endpoint"}).json()

    assert body["persisted"] is True
    assert body["similar"], "expected a similar prior PR"
    top = body["similar"][0]
    for field in ("analysis_id", "repository", "number", "title", "risk_score", "similarity"):
        assert field in top
    assert 0.0 <= top["similarity"] <= 1.0
    assert top["repository"] == "anshbabar/PRism"


def test_similar_excludes_current_analysis(client: TestClient) -> None:
    first = client.post(ENDPOINT, json={"name": "auth-token-expiry"}).json()
    second = client.post(ENDPOINT, json={"name": "add-orders-table"}).json()
    similar_ids = {s["analysis_id"] for s in second["similar"]}
    assert second["analysis_id"] not in similar_ids
    assert first["analysis_id"] in similar_ids  # the prior analysis is retrievable
