"""Engine / session factory and the FastAPI DB dependency.

The engine and sessionmaker are cached per database URL so a process reuses one
connection pool. ``get_session`` is the FastAPI dependency the routes use; tests
override it with a SQLite-backed sessionmaker (see ``tests/conftest.py``).
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@cache
def get_engine(url: str) -> Engine:
    """Return a cached engine for ``url``. ``pool_pre_ping`` avoids stale conns."""
    return create_engine(url, pool_pre_ping=True, future=True)


@cache
def get_sessionmaker(url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(url), expire_on_commit=False, future=True)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: yield a session bound to the configured database."""
    factory = get_sessionmaker(get_settings().database_url)
    with factory() as session:
        yield session
