"""Les tableaux de bord que personne n'ouvre plus : qui est listé, sur quelles preuves, et ce qu'en dit Slack."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from lib.query import QueryResult
from web import idle_dashboards
from web.db import get_db
from web.models import Dashboard, DashboardPublication

NOW = datetime(2026, 11, 16, tzinfo=timezone.utc)


def make_dashboard(session, slug, days_old, archived=False):
    session.add(
        Dashboard(
            slug=slug,
            title="t",
            description="d",
            website="emplois",
            category="c",
            first_author_email="alice@x",
            is_archived=archived,
            has_api_access=False,
            has_cron=False,
            has_persistence=False,
            created_at=NOW - timedelta(days=days_old),
            updated_at=NOW,
        )
    )
    session.flush()


def make_publication(session, slug, environment, days_old, unpublished=False):
    session.add(
        DashboardPublication(
            dashboard_slug=slug,
            publication_id=uuid.uuid4().hex[:6],
            environment=environment,
            published_by="bob@x",
            published_at=NOW - timedelta(days=days_old),
            unpublished_at=NOW - timedelta(days=1) if unpublished else None,
        )
    )


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_candidates_are_old_dashboards_without_a_recent_live_production_publication():
    run_id = uuid.uuid4().hex[:8]
    with get_db() as session:
        make_dashboard(session, f"old-{run_id}", 60)
        make_dashboard(session, f"recent-{run_id}", 30)
        make_dashboard(session, f"archived-{run_id}", 60, archived=True)
        for name, environment, days_old, unpublished in (
            ("published-long-ago", "production", 50, False),
            ("published-lately", "production", 10, False),
            ("staging-only", "staging", 10, False),
            ("unpublished", "production", 10, True),
        ):
            make_dashboard(session, f"{name}-{run_id}", 60)
            make_publication(session, f"{name}-{run_id}", environment, days_old, unpublished)

    found = {row.slug: row.published_at for row in idle_dashboards.candidates(NOW) if row.slug.endswith(run_id)}

    assert found == {
        f"old-{run_id}": None,
        f"published-long-ago-{run_id}": NOW - timedelta(days=50),
        f"staging-only-{run_id}": None,
        f"unpublished-{run_id}": None,
    }


def matomo(mocker, pages=(), error=None):
    return mocker.patch(
        "web.idle_dashboards.execute_matomo_query",
        return_value=QueryResult(success=error is None, data=list(pages), error=error),
    )


@pytest.mark.parametrize(
    ("label", "visits", "slugs"),
    [
        ("/interactive/tdb/", 3, {"tdb"}),
        ("/interactive/tdb", 3, {"tdb"}),
        ("/interactive/tdb/index.html?q=abc", 3, {"tdb"}),
        ("/interactive/tdb?onglet=carte", 3, {"tdb"}),
        ("/interactive/tdb/", 0, set()),
        ("/conversations", 3, set()),
    ],
)
def test_a_visited_page_under_the_prefix_counts_for_its_dashboard(mocker, label, visits, slugs):
    matomo(mocker, [{"label": label, "nb_visits": visits}])

    assert idle_dashboards.visited("/interactive/", NOW) == slugs


def test_matomo_is_asked_for_45_days_of_the_site_that_follows_the_app_and_its_publications(mocker):
    query = matomo(mocker)

    idle_dashboards.visited("/dashboards/", NOW, "pageUrl=^x")

    params = query.call_args.kwargs["params"]
    assert (params["idSite"], params["period"], params["date"], params["segment"]) == (
        224,
        "range",
        "2026-10-02,2026-11-16",
        "pageUrl=^x",
    )


def test_a_matomo_failure_is_no_answer_rather_than_no_visit(mocker):
    matomo(mocker, error="HTTP 500")

    assert idle_dashboards.visited("/interactive/", NOW) is None


@pytest.mark.parametrize(
    ("result", "seen"),
    [
        (QueryResult(success=True, data={"count": 2, "distinct": None}), True),
        (QueryResult(success=True, data={"count": 0, "distinct": None}), False),
        (QueryResult(success=False, data=None, error="HTTP 429"), None),
    ],
    ids=["opened", "never-opened", "datadog-down"],
)
def test_datadog_tells_whether_the_page_was_opened_in_its_30_days(mocker, result, seen):
    count = mocker.patch("web.idle_dashboards.execute_datadog_count", return_value=result)

    assert idle_dashboards.opened("tdb") is seen
    assert (count.call_args.kwargs["search"], count.call_args.kwargs["days"]) == (
        'service:matometa "/interactive/tdb/"',
        30,
    )
