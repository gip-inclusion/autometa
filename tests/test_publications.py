from datetime import datetime, timezone

from sqlalchemy import select

from web.db import get_db
from web.models import Dashboard, DashboardPublication


def _make_dashboard(slug, *, archived=False, has_api_access=False, has_persistence=False):
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(Dashboard(
            slug=slug, title=slug, description="d", website="emplois", category="c",
            first_author_email="alice@x", is_archived=archived,
            has_api_access=has_api_access, has_cron=False, has_persistence=has_persistence,
            created_at=now, updated_at=now,
        ))


def test_dashboard_publication_row_roundtrip(client):
    _make_dashboard("pub-model")
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(DashboardPublication(
            dashboard_slug="pub-model", publication_id="abc123",
            environment="staging", published_by="bob@x", published_at=now,
        ))
    with get_db() as session:
        row = session.scalar(select(DashboardPublication).where(DashboardPublication.publication_id == "abc123"))
        assert row.dashboard_slug == "pub-model"
        assert row.environment == "staging"
        assert row.unpublished_at is None
