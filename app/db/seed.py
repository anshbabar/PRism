"""Seed the database by analyzing every local fixture.

Run with ``make seed`` (after ``make db-up`` + ``make migrate``) to populate the
dashboard. Uses the same pipeline as the API, so seeded rows are identical to
what the endpoint would produce. Re-running adds fresh analyses (re-analysis
history); it does not wipe existing data.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.db.repository import persist_analysis
from app.db.session import get_sessionmaker
from app.ingest.fixtures import list_fixtures, load_fixture
from app.pipeline import analyze_fixture


def seed() -> int:
    settings = get_settings()
    factory = get_sessionmaker(settings.database_url)
    names = list_fixtures()

    with factory() as session:
        for name in names:
            fixture = load_fixture(name)
            artifacts = analyze_fixture(fixture, settings)
            persist_analysis(
                session,
                metadata=fixture.metadata,
                parsed=artifacts.parsed,
                risk=artifacts.risk,
                review_outcome=artifacts.review,
                vector=artifacts.vector,
                embedding_provider_name=artifacts.embedding_provider_name,
                embedding_model=artifacts.embedding_model,
                latency_ms=artifacts.latency_ms,
            )
            print(f"  seeded {name} (risk {artifacts.risk.score}/5)")

    print(f"Seeded {len(names)} analyses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(seed())
