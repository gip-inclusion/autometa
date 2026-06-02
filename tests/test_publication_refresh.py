from datetime import datetime, timezone

import pytest
from botocore.exceptions import ClientError
from sqlalchemy import select

from web import publications
from web.db import get_db
from web.models import Dashboard, DashboardPublication


def _make_dashboard(slug):
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(
            Dashboard(
                slug=slug,
                title=slug,
                description="d",
                website="emplois",
                category="c",
                first_author_email="alice@x",
                is_archived=False,
                has_api_access=False,
                has_cron=False,
                has_persistence=False,
                created_at=now,
                updated_at=now,
            )
        )


def _make_publication(slug, publication_id, *, environment="staging", unpublished=False, paused=False, status=None):
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(
            DashboardPublication(
                dashboard_slug=slug,
                publication_id=publication_id,
                environment=environment,
                published_by="bob@x",
                published_at=now,
                unpublished_at=now if unpublished else None,
                refresh_paused_at=now if paused else None,
                last_refresh_status=status,
            )
        )


def _client_error():
    return ClientError({"Error": {"Code": "AccessDenied", "Message": "denied"}}, "PutObject")


REFRESH_MATRIX = [
    (None, False, "success", False, True),
    (None, True, "failure", True, False),
    ("success", False, "success", False, True),
    ("success", True, "failure", True, False),
    ("failure", False, "success", True, True),
    ("failure", True, "failure", False, False),
]


@pytest.mark.parametrize("previous,raises,expected,alert,ts_set", REFRESH_MATRIX)
def test_refresh_matrix(client, mocker, previous, raises, expected, alert, ts_set):
    _make_dashboard("refresh-mx")
    _make_publication("refresh-mx", "matrx1", status=previous)
    if raises:
        mocker.patch("web.publications.s3.sync_prefix", side_effect=_client_error())
    else:
        mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    notify = mocker.patch("web.publications.alerts.notify_alert_channel")

    publications.refresh("matrx1")

    with get_db() as session:
        row = session.scalar(select(DashboardPublication).where(DashboardPublication.publication_id == "matrx1"))
        assert row.last_refresh_status == expected
        assert (row.last_successful_refresh_at is not None) is ts_set
        if expected == "success":
            assert row.last_refresh_error is None
    assert notify.called is alert


def test_refresh_truncates_long_error_message(client, mocker):
    _make_dashboard("refresh-trunc")
    _make_publication("refresh-trunc", "trunc1")
    huge = "x" * 5000
    err = ClientError({"Error": {"Code": "AccessDenied", "Message": huge}}, "PutObject")
    mocker.patch("web.publications.s3.sync_prefix", side_effect=err)
    mocker.patch("web.publications.alerts.notify_alert_channel")

    publications.refresh("trunc1")

    with get_db() as session:
        row = session.scalar(select(DashboardPublication).where(DashboardPublication.publication_id == "trunc1"))
        assert row.last_refresh_status == "failure"
        assert row.last_refresh_error is not None
        assert len(row.last_refresh_error) <= 500


@pytest.mark.parametrize("flag", ["unpublished", "paused"])
def test_refresh_is_noop_when_unpublished_or_paused(client, mocker, flag):
    _make_dashboard("refresh-guard")
    _make_publication(
        "refresh-guard",
        "guard1",
        unpublished=(flag == "unpublished"),
        paused=(flag == "paused"),
    )
    sync = mocker.patch("web.publications.s3.sync_prefix")
    notify = mocker.patch("web.publications.alerts.notify_alert_channel")

    publications.refresh("guard1")

    sync.assert_not_called()
    notify.assert_not_called()
    with get_db() as session:
        row = session.scalar(select(DashboardPublication).where(DashboardPublication.publication_id == "guard1"))
        assert row.last_refresh_status is None


def test_refresh_unknown_publication_is_silent_noop(client, mocker):
    sync = mocker.patch("web.publications.s3.sync_prefix")
    publications.refresh("nope12")
    sync.assert_not_called()
