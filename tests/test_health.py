"""Tests for the health and root endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "PRism"
    assert body["version"]
    assert body["environment"]


def test_root_points_to_health_and_docs(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["health"] == "/health"
    assert body["docs"] == "/docs"
