"""Health and root routes."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Liveness probe. Returns 200 with service metadata when the app is up."""
    settings: Settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.version,
        environment=settings.environment,
    )


@router.get("/", tags=["health"])
def root() -> dict[str, str]:
    """Root endpoint — a friendly pointer to the docs and health check."""
    settings = get_settings()
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }
