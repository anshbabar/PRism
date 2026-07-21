"""Database layer: SQLAlchemy models, session factory, and persistence.

Relational persistence for PR analyses. Models are dialect-portable so the real
app runs on Postgres (docker-compose) while tests run on hermetic in-memory
SQLite. Embeddings are stored as JSON vectors; similarity is computed in the
retrieval layer (see ``app/retrieval``).
"""
