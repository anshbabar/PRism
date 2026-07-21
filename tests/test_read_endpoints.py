"""Tests for the dashboard read endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

ANALYZE = "/api/analyze/local-fixture"


def _seed(client: TestClient, *names: str) -> list[str]:
    ids: list[str] = []
    for name in names:
        body = client.post(ANALYZE, json={"name": name}).json()
        ids.append(body["analysis_id"])
    return ids


def test_list_analyses_returns_summaries_newest_first(client: TestClient) -> None:
    _seed(client, "auth-token-expiry", "add-orders-table")
    rows = client.get("/api/analyses").json()

    assert len(rows) == 2
    row = rows[0]
    for field in (
        "analysis_id",
        "repository",
        "number",
        "title",
        "risk_band",
        "final_score",
        "files_changed",
        "created_at",
    ):
        assert field in row
    # Newest first: add-orders-table was analyzed last.
    assert rows[0]["title"] == "Add orders table and Order model"


def test_analysis_detail_has_full_payload(client: TestClient) -> None:
    (first_id, second_id) = _seed(client, "add-orders-table", "add-orders-api-endpoint")
    detail = client.get(f"/api/analyses/{second_id}").json()

    assert detail["analysis_id"] == second_id
    assert detail["repository"] == "anshbabar/PRism"
    assert detail["review"]["summary"]
    assert detail["risk"]["signals"]
    assert detail["changed_files"]
    assert 1 <= detail["final_score"] <= 5
    # The related orders PR should show up as similar.
    assert any(s["analysis_id"] == first_id for s in detail["similar"])


def test_analysis_detail_404_for_unknown_id(client: TestClient) -> None:
    resp = client.get("/api/analyses/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_analysis_detail_422_for_malformed_id(client: TestClient) -> None:
    resp = client.get("/api/analyses/not-a-uuid")
    assert resp.status_code == 422


def test_eval_latest_returns_metrics(client: TestClient) -> None:
    resp = client.get("/api/eval/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert "metrics" in body
    assert "valid_json_rate" in body["metrics"]
