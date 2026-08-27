"""Test-only schema bootstrap. Production schema is managed by Alembic; le vocabulaire vient de Notion."""

from sqlalchemy import text

from .db import get_engine, init_tables


def init_db():
    """Initialize database schema via SQLAlchemy models."""
    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    init_tables()
