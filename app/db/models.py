"""SQLAlchemy 2.0 ORM models.

Portable across Postgres (real) and SQLite (tests): ``Uuid`` maps to native
UUID on Postgres and ``CHAR(32)`` elsewhere; ``JSON`` maps to JSON/JSONB on
Postgres and JSON-encoded TEXT on SQLite. Embedding vectors are stored as JSON
``list[float]`` (see module docstring in ``app/db``).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy import DateTime as SADateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def _created_at() -> Mapped[datetime]:
    return mapped_column(SADateTime(timezone=True), default=_utcnow)


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("owner", "name", name="uq_repositories_owner_name"),)

    id: Mapped[uuid.UUID] = _pk()
    owner: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = _created_at()

    pull_requests: Mapped[list[PullRequest]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint(
            "repository_id", "number", "head_sha", name="uq_pull_requests_repo_number_head"
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    repository_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("repositories.id"))
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(255), default="")
    base_sha: Mapped[str] = mapped_column(String(64), default="")
    head_sha: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(Text, default="")  # untrusted PR text
    url: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = _created_at()

    repository: Mapped[Repository] = relationship(back_populates="pull_requests")
    analyses: Mapped[list[Analysis]] = relationship(
        back_populates="pull_request", cascade="all, delete-orphan"
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = _pk()
    pull_request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pull_requests.id"))
    status: Mapped[str] = mapped_column(String(32))  # completed | fallback
    deterministic_score: Mapped[int] = mapped_column(Integer)
    final_score: Mapped[int] = mapped_column(Integer)
    risk_band: Mapped[str] = mapped_column(String(16))
    summary: Mapped[str] = mapped_column(Text, default="")
    risk_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    review_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    provider: Mapped[str] = mapped_column(String(64), default="")
    model: Mapped[str] = mapped_column(String(128), default="")
    prompt_version: Mapped[str] = mapped_column(String(64), default="")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = _created_at()

    pull_request: Mapped[PullRequest] = relationship(back_populates="analyses")
    changed_files: Mapped[list[ChangedFile]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    embedding: Mapped[Embedding | None] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", uselist=False
    )


class ChangedFile(Base):
    __tablename__ = "changed_files"

    id: Mapped[uuid.UUID] = _pk()
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id"))
    path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16))
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    hunks_json: Mapped[list[Any]] = mapped_column(JSON, default=list)

    analysis: Mapped[Analysis] = relationship(back_populates="changed_files")


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = _pk()
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id"), unique=True)
    kind: Mapped[str] = mapped_column(String(32), default="summary")
    dim: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(64), default="")
    model: Mapped[str] = mapped_column(String(128), default="")
    vector: Mapped[list[float]] = mapped_column(JSON)
    created_at: Mapped[datetime] = _created_at()

    analysis: Mapped[Analysis] = relationship(back_populates="embedding")
