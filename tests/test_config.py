"""Tests for the configuration system."""

from __future__ import annotations

import pytest
from app.core.config import Settings, get_settings


def test_defaults_are_sane() -> None:
    settings = Settings()
    assert settings.app_name == "PRism"
    assert settings.environment in {"local", "ci", "production"}
    assert settings.llm_provider == "stub"  # offline by default
    assert settings.post_reviews is False  # never post to GitHub by default


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "ci")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    settings = Settings()
    assert settings.environment == "ci"
    assert settings.log_level == "debug"


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()
