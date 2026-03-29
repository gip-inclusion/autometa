"""Pytest configuration — uses a separate _test database to never touch dev/prod data."""

import importlib
import os
from urllib.parse import urlparse, urlunparse

# Force a dedicated test database BEFORE any app code loads config.
# If DATABASE_URL already ends with _test (CI), keep it. Otherwise append _test.
_original_url = os.environ.get("DATABASE_URL", "")
if _original_url and not urlparse(_original_url).path.endswith("_test"):
    parsed = urlparse(_original_url)
    os.environ["DATABASE_URL"] = urlunparse(parsed._replace(path=parsed.path + "_test"))

os.environ.setdefault("AUTOMETA_SSE_MESSAGE_WAIT_TIMEOUT", "0.05")

import pytest

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


# Create the test database if it doesn't exist (uses the original URL to connect)
def _ensure_test_db():
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    test_url = os.environ["DATABASE_URL"]
    db_name = urlparse(test_url).path.lstrip("/")

    conn = psycopg2.connect(_original_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE "{db_name}"')
    conn.close()


_ensure_test_db()

MATOMO_TEST_SITE_ID = int(os.environ.get("MATOMO_TEST_SITE_ID", "117"))
MATOMO_TEST_PERIOD = os.environ.get("MATOMO_TEST_PERIOD", "month")
MATOMO_TEST_DATE = os.environ.get("MATOMO_TEST_DATE", "2025-12-01")
MATOMO_TEST_DIMENSION_ID = int(os.environ.get("MATOMO_TEST_DIMENSION_ID", "1"))
MATOMO_TEST_SEGMENT = os.environ.get("MATOMO_TEST_SEGMENT", "pageUrl=@/gps/")


def truncate_all_tables():
    from sqlalchemy import text

    from web.db import get_db

    with get_db() as session:
        session.execute(
            text("""
            TRUNCATE TABLE messages, conversation_tags, report_tags,
                uploaded_files, cron_runs, pinned_items, pm_commands,
                pm_heartbeat, reports, conversations, tags, schema_version,
                wishlist, matomo_baselines, matomo_dimensions, matomo_segments,
                matomo_events, metabase_cards, metabase_dashboards
                CASCADE;
        """)
        )


@pytest.fixture
def app():
    from web import database

    importlib.reload(database)

    from web.app import app as fastapi_app

    yield fastapi_app

    truncate_all_tables()


@pytest.fixture
def client(app):
    from starlette.testclient import TestClient

    return TestClient(app)
