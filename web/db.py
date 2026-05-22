"""Database connection infrastructure (PostgreSQL + SQLAlchemy)."""

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from . import config

logger = logging.getLogger(__name__)

engine = None
SessionLocal = None


def get_engine():
    global engine, SessionLocal
    if engine is None:
        engine = create_engine(
            config.DATABASE_URL,
            pool_size=2,
            max_overflow=3,
            pool_pre_ping=True,
        )
        SessionLocal = sessionmaker(bind=engine)
        logger.info("SQLAlchemy engine created (pool_size=2, max_overflow=3)")
    return engine


def get_session_factory():
    get_engine()
    return SessionLocal


test_session_var: ContextVar[Optional[Session]] = ContextVar("db_test_session", default=None)


@contextmanager
def get_db() -> Session:
    """Context manager yielding a SQLAlchemy Session. Auto-commits on success, rolls back on error."""
    test_session = test_session_var.get()
    if test_session is not None:
        # Why: SAVEPOINT to mirror prod commit/rollback semantics inside the shared test session.
        with test_session.begin_nested():
            yield test_session
        return

    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def test_transaction():
    """Hold one session for a test; rolls back on exit so tests leave no durable DB state."""
    factory = get_session_factory()
    session = factory()
    token = test_session_var.set(session)
    try:
        yield
    finally:
        try:
            session.rollback()
        finally:
            test_session_var.reset(token)
            session.close()


def init_tables():
    """Create all tables from SQLAlchemy models (used in tests and initial setup)."""
    from .models import Base

    get_engine()
    Base.metadata.create_all(engine)
