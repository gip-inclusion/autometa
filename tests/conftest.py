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
os.environ.setdefault("S3_BUCKET", "test-bucket")
os.environ.setdefault("PUBLIC_DASHBOARDS_BUCKET_STAGING", "test-staging-bucket")
os.environ.setdefault("PUBLIC_DASHBOARDS_BUCKET_PROD", "test-prod-bucket")

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


@pytest.fixture(scope="session", autouse=True)
def init_schema():
    from web.schema import init_db

    init_db()


@pytest.fixture(autouse=True)
def _s3_default_404(mocker):
    """Default S3 head_object/get_object to NoSuchKey for CI (no real S3 endpoint); tests override as needed."""
    from botocore.exceptions import ClientError

    from web import s3

    nf = ClientError({"Error": {"Code": "NoSuchKey", "Message": "x"}}, "Op")
    mocker.patch.object(s3._client, "head_object", side_effect=nf)
    mocker.patch.object(s3._client, "get_object", side_effect=nf)


@pytest.fixture(autouse=True)
def _reset_otel_provider():
    # Why: trace.set_tracer_provider() is a Once-guarded global; once any test installs a
    # provider, subsequent set_tracer_provider() calls silently no-op. Reset the guard before
    # each test so per-test InMemorySpanExporter setups actually take effect.
    from opentelemetry import trace
    from opentelemetry.util._once import Once

    trace._TRACER_PROVIDER = None
    trace._TRACER_PROVIDER_SET_ONCE = Once()
    yield


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
            TRUNCATE TABLE conversation_message_embeddings, messages, conversation_tags, report_tags,
                uploaded_files, cron_runs, dashboards, dashboard_tags, dashboard_publications, pinned_items,
                reports, conversations, tags,
                matomo_baselines, matomo_dimensions, matomo_segments,
                matomo_events, metabase_cards, metabase_dashboards
                CASCADE;
        """)
        )


@pytest.fixture
def app():
    import web.redis_conn
    from web import database

    web.redis_conn._pool = None

    importlib.reload(database)

    from web.app import app as fastapi_app

    yield fastapi_app

    truncate_all_tables()
    web.redis_conn._pool = None


@pytest.fixture
def client(app):
    from starlette.testclient import TestClient

    return TestClient(app)
