"""Alerte quotidienne des tableaux de bord sans visite Matomo depuis 60 jours."""

from datetime import date, datetime, timedelta, timezone

import pytest

from lib.query import QueryResult
from web import unused_dashboards
from web.unused_dashboards import owner_name, report_unused_dashboards, unused_dashboards_from, visited_slugs

NOW = datetime(2026, 11, 25, 6, 0, tzinfo=timezone.utc)


def dashboard(slug, days_old=90, email="prenom.nom@inclusion.gouv.fr", title=None):
    return {
        "slug": slug,
        "title": title or slug,
        "first_author_email": email,
        "created_at": NOW - timedelta(days=days_old),
    }


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        (["/interactive/x/"], {"x"}),
        (["/interactive/x"], {"x"}),
        (["/interactive/x/index.html?onglet=carte"], {"x"}),
        (["/dashboards/y/"], {"y"}),
        (["/dashboards/y/ - Others"], {"y"}),
        (["/interactive/x?onglet=carte", "/dashboards/y#graphe"], {"x", "y"}),
        (["/dashboards/fiche/edit"], set()),
        (["/explorations/abc", "/", "Page URL not defined"], set()),
    ],
)
def test_visited_slugs(labels, expected):
    assert visited_slugs([{"label": label} for label in labels]) == expected


@pytest.mark.parametrize("label", ["/interactive/ - Others", "/dashboards/ - Others"])
def test_visited_slugs_refuses_truncated_day(label):
    with pytest.raises(RuntimeError, match="Others"):
        visited_slugs([{"label": label}])


@pytest.mark.parametrize(
    ("email", "expected"),
    [
        ("prenom.nom@inclusion.gouv.fr", "Prenom Nom"),
        ("jean-marc.dupont@x.fr", "Jean-Marc Dupont"),
        ("anonyme@x.fr", "anonyme@x.fr"),
    ],
)
def test_owner_name(email, expected):
    assert owner_name(email) == expected


def test_unused_dashboards_keeps_old_unvisited_sorted_by_title():
    dashboards = [
        dashboard("b", title="Zeta"),
        dashboard("a", title="Alpha"),
        dashboard("vu"),
        dashboard("jeune", days_old=59),
        dashboard("rdvi-13", title="Rdvi"),
    ]

    unused = unused_dashboards_from(dashboards, visited={"rdvi-13-2", "vu"}, now=NOW)

    assert [d["slug"] for d in unused] == ["a", "rdvi-13", "b"]


def run_report(mocker, result, dashboards):
    query = mocker.patch.object(unused_dashboards, "execute_matomo_query", return_value=result)
    mocker.patch.object(unused_dashboards.store, "list_dashboards", return_value=dashboards)
    mocker.patch.object(unused_dashboards, "utcnow", return_value=NOW)
    mocker.patch.object(unused_dashboards.config, "BASE_URL", "https://autometa.test")
    notify = mocker.patch.object(unused_dashboards, "notify_alert_channel")
    report_unused_dashboards()
    return query, notify


def test_report_posts_one_message(mocker):
    result = QueryResult(success=True, data=[[{"label": "/interactive/vu/"}]] * 60)

    query, notify = run_report(mocker, result, [dashboard("vu"), dashboard("mort", title="Suivi OKR")])

    query.assert_called_once()
    assert query.call_args.args[2] == "API.getBulkRequest"
    urls = query.call_args.args[3]
    assert len(urls) == 60
    assert all("method=Actions.getPageUrls&idSite=224&period=day" in url for url in urls.values())
    assert f"date={date(2026, 11, 24)}" in urls["urls[0]"]
    assert f"date={date(2026, 9, 26)}" in urls["urls[59]"]
    message = notify.call_args.args[0]
    assert "Suivi OKR — Prenom Nom — https://autometa.test/dashboards/mort" in message
    assert "/dashboards/vu" not in message


def test_report_silent_when_all_visited(mocker):
    result = QueryResult(success=True, data=[[{"label": "/interactive/vu/"}]] * 60)

    _, notify = run_report(mocker, result, [dashboard("vu")])

    notify.assert_not_called()


@pytest.mark.parametrize(
    "result",
    [
        QueryResult(success=False, data=None, error="timeout"),
        QueryResult(success=True, data=[[]] * 59 + [{"result": "error", "message": "archive"}]),
    ],
)
def test_report_raises_and_stays_silent_on_matomo_failure(mocker, result):
    with pytest.raises(RuntimeError):
        run_report(mocker, result, [dashboard("mort")])
    unused_dashboards.notify_alert_channel.assert_not_called()
