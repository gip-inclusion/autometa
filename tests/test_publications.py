from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from web import publications
from web.db import get_db
from web.models import Dashboard, DashboardPublication
from web.publications import PublicationBlocked


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


def test_publish_staging_creates_row_and_pushes(client, mocker):
    _make_dashboard("pub-stg")
    copy = mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.delete_prefix", return_value=0)
    pub = publications.publish("pub-stg", "staging", "bob@x")
    assert pub["environment"] == "staging"
    assert len(pub["publication_id"]) == 6
    assert pub["url"].startswith("https://staging.statistiques.inclusion.gouv.fr/dashboards/pub-stg-")
    assert copy.call_count == 2
    assert len(publications.list_publications("pub-stg")) == 1


def test_publish_blocked_when_archived(client, mocker):
    _make_dashboard("pub-arch", archived=True)
    mocker.patch("web.publications.s3.copy_prefix")
    with pytest.raises(PublicationBlocked):
        publications.publish("pub-arch", "staging", "bob@x")


def test_publish_blocked_when_uses_query_api(client, mocker):
    _make_dashboard("pub-api", has_api_access=True)
    mocker.patch("web.publications.s3.copy_prefix")
    with pytest.raises(PublicationBlocked):
        publications.publish("pub-api", "staging", "bob@x")


def test_publish_blocked_when_persistence(client, mocker):
    _make_dashboard("pub-persist", has_persistence=True)
    mocker.patch("web.publications.s3.copy_prefix")
    with pytest.raises(PublicationBlocked):
        publications.publish("pub-persist", "staging", "bob@x")


def test_publish_production_supersedes_previous(client, mocker):
    _make_dashboard("pub-prod")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.delete_prefix", return_value=0)
    first = publications.publish("pub-prod", "production", "bob@x")
    second = publications.publish("pub-prod", "production", "bob@x")
    active = publications.list_publications("pub-prod", active_only=True)
    assert len(active) == 1
    assert active[0]["publication_id"] == second["publication_id"]
    assert first["publication_id"] != second["publication_id"]


def test_unpublish_soft_deletes_and_clears_public(client, mocker):
    _make_dashboard("pub-unp")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    delete = mocker.patch("web.publications.s3.delete_prefix", return_value=1)
    pub = publications.publish("pub-unp", "staging", "bob@x")
    assert publications.unpublish(pub["publication_id"]) is True
    assert publications.list_publications("pub-unp", active_only=True) == []
    delete.assert_called_with(publications._public_bucket("staging"), f"dashboards/pub-unp-{pub['publication_id']}/")
