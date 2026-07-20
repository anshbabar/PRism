"""Application configuration.

All settings are environment-driven (see ``.env.example`` for the full list).
Secrets must come from the environment — never hardcode them here. ``.env`` is
git-ignored; ``.env.example`` documents every key.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app import __version__


class Settings(BaseSettings):
    """Typed application settings loaded from the environment / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Core ---
    app_name: str = "PRism"
    version: str = __version__
    environment: Literal["local", "ci", "production"] = "local"
    log_level: str = "info"

    # --- Database (used from later milestones; declared now so config is stable) ---
    database_url: str = "postgresql+psycopg://prism:prism@localhost:5432/prism"

    # --- LLM ---
    llm_provider: Literal["mock", "anthropic"] = "mock"
    llm_model: str = "claude-opus-4-8"
    llm_max_tokens: int = 4096
    anthropic_api_key: str | None = None

    # --- GitHub App (used from later milestones) ---
    github_app_id: str | None = None
    github_webhook_secret: str | None = None
    post_reviews: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    Cached so the ``.env`` file is parsed once per process. Tests that need a
    fresh instance can call ``get_settings.cache_clear()``.
    """
    return Settings()
