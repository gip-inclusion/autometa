"""Les tableaux de bord que personne n'ouvre plus : qui est listé, sur quelles preuves, et ce qu'en dit Slack."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from lib.query import QueryResult
from web import idle_dashboards
from web.db import get_db
from web.environment import Environment
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


def matomo(mocker, *days, error=None):
    return mocker.patch(
        "web.idle_dashboards.execute_matomo_query",
        return_value=QueryResult(
            success=error is None,
            data={f"2026-11-{i + 1:02d}": list(pages) for i, pages in enumerate(days)},
            error=error,
        ),
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


def test_every_day_of_the_window_counts(mocker):
    matomo(
        mocker,
        [{"label": "/interactive/a/", "nb_visits": 1}],
        [],
        [{"label": "/interactive/b/", "nb_visits": 2}],
    )

    assert idle_dashboards.visited("/interactive/", NOW) == {"a", "b"}


def test_matomo_is_asked_day_by_day_for_45_days_of_the_site_that_follows_the_app_and_its_publications(mocker):
    query = matomo(mocker)

    idle_dashboards.visited("/dashboards/", NOW, "pageUrl=^x")

    params = query.call_args.kwargs["params"]
    assert (params["idSite"], params["period"], params["date"], params["segment"]) == (
        224,
        "day",
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


def dashboard(slug, *, title="Titre", has_cron=False, published=False):
    return SimpleNamespace(
        slug=slug,
        title=title,
        first_author_email="alice@x",
        has_cron=has_cron,
        published_at=NOW - timedelta(days=60) if published else None,
    )


def sweep(
    mocker, monkeypatch, *, dashboards=(), internal=frozenset(), public=frozenset(), hits=None, env=Environment.PROD
):
    monkeypatch.setattr("web.idle_dashboards.config.ENV", env)
    monkeypatch.setattr("web.idle_dashboards.config.BASE_URL", "https://autometa.test")
    candidates = mocker.patch("web.idle_dashboards.candidates", return_value=list(dashboards))
    mocker.patch("web.idle_dashboards.visited", side_effect=[internal, public])
    datadog = mocker.patch("web.idle_dashboards.opened", side_effect=lambda slug: (hits or {}).get(slug, False))
    slack = mocker.patch("web.idle_dashboards.alerts.notify_alert_channel", return_value="1700000000.000100")
    idle_dashboards.run()
    return candidates, datadog, slack


def test_only_dashboards_nobody_opened_anywhere_are_listed(mocker, monkeypatch):
    _, datadog, slack = sweep(
        mocker,
        monkeypatch,
        dashboards=[dashboard(s) for s in ("a", "in-app", "in-public", "in-datadog", "e")],
        internal={"in-app"},
        public={"in-public"},
        hits={"in-datadog": True},
    )

    assert [c.args[0] for c in datadog.call_args_list] == ["a", "in-datadog", "e"]
    assert slack.call_args_list[0].args == (
        ":zzz: 2 tableaux de bord sans visite connue (Matomo sur 45 jours, Datadog sur 30) — à archiver ?",
    )
    assert slack.call_args_list[1].args == (
        "<https://autometa.test/dashboards/a/edit|a> — Titre — alice@x\n"
        "<https://autometa.test/dashboards/e/edit|e> — Titre — alice@x",
    )


def test_a_line_flags_cron_and_publication_and_escapes_the_title(mocker, monkeypatch):
    _, _, slack = sweep(
        mocker, monkeypatch, dashboards=[dashboard("tdb", title="R&D <b>", has_cron=True, published=True)]
    )

    assert slack.call_args_list[1].args == (
        "<https://autometa.test/dashboards/tdb/edit|tdb> — R&amp;D &lt;b&gt; — alice@x — cron — publié, à dépublier aussi",
    )


def test_a_dashboard_datadog_could_not_check_is_left_out_and_counted(mocker, monkeypatch):
    _, _, slack = sweep(mocker, monkeypatch, dashboards=[dashboard("tdb")], hits={"tdb": None})

    assert slack.call_args_list == [
        mocker.call(
            ":zzz: 0 tableau de bord sans visite connue (Matomo sur 45 jours, Datadog sur 30) — à archiver ?"
            " (1 non vérifié : Datadog n'a pas répondu)"
        )
    ]


@pytest.mark.parametrize(("internal", "public"), [(None, set()), (set(), None)], ids=["app", "publications"])
def test_without_matomo_a_warning_replaces_the_list(mocker, monkeypatch, internal, public):
    candidates, datadog, slack = sweep(
        mocker, monkeypatch, dashboards=[dashboard("tdb")], internal=internal, public=public
    )

    candidates.assert_not_called()
    datadog.assert_not_called()
    assert slack.call_args_list == [
        mocker.call(":warning: Tableaux de bord sans visite : Matomo n'a pas répondu, pas de liste cette semaine")
    ]


@pytest.mark.parametrize("env", [Environment.DEV, Environment.REVIEW, Environment.STAGING])
def test_nothing_is_queried_or_posted_outside_production(mocker, monkeypatch, env):
    candidates, datadog, slack = sweep(mocker, monkeypatch, dashboards=[dashboard("tdb")], env=env)

    candidates.assert_not_called()
    datadog.assert_not_called()
    slack.assert_not_called()
