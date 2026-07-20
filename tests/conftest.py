"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.core.config import get_settings
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient bound to a fresh app instance.

    ``get_settings`` is cached; clear it so each test picks up a clean config
    (important once tests start overriding env vars).
    """
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client
