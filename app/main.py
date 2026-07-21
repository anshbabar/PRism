"""FastAPI application entrypoint.

``create_app`` is a factory so tests can build isolated app instances. The
module-level ``app`` is what uvicorn serves (``uvicorn app.main:app``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import routes_analyses, routes_analyze, routes_eval, routes_health
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger("app.main")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Startup: DB pools / provider clients get wired here in later milestones.
        logger.info(
            "starting up",
            extra={"service": settings.app_name, "environment": settings.environment},
        )
        yield
        logger.info("shutting down")

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="AI PR Reviewer + Regression Triage platform.",
        lifespan=lifespan,
    )

    app.include_router(routes_health.router)
    app.include_router(routes_analyze.router)
    app.include_router(routes_analyses.router)
    app.include_router(routes_eval.router)
    return app


app = create_app()
