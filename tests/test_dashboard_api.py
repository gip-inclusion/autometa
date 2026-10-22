"""Tests de la façade des tableaux de bord et de son vérificateur d'imports."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import OperationalError

from lib import dashboard_api, facade_imports
from lib.airtable import AirtableError
from lib.datadog import by_count
from lib.query import CallerType, QueryResult
from web.db import get_db
from web.models import Dashboard, DashboardPublication

FACADE_IMPORT = "from lib.dashboard_api import query_matomo\n"
FACADE_MODULE_IMPORT = "import lib.dashboard_api\n"
FACADE_FROM_PACKAGE = "from lib import dashboard_api\n"
STDLIB = "import json\nfrom datetime import date\n"
THIRD_PARTY = "import httpx\nfrom sqlalchemy import text\n"
RELATIVE = "from . import helpers\n"
INTERNAL_QUERY = "from lib.query import execute_matomo_query\n"
INTERNAL_DB = "from web.db import get_db\n"
INTERNAL_CONFIG = "import web.config\n"
INTERNAL_FROM_PACKAGE = "from lib import query\n"
INTERNAL_ALIASED = "import lib.query as q\n"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (FACADE_IMPORT, []),
        (FACADE_MODULE_IMPORT, []),
        (FACADE_FROM_PACKAGE, []),
        (STDLIB, []),
        (THIRD_PARTY, []),
        (RELATIVE, []),
        (INTERNAL_QUERY, ["lib.query"]),
        (INTERNAL_DB, ["web.db"]),
        (INTERNAL_CONFIG, ["web.config"]),
        (INTERNAL_FROM_PACKAGE, ["lib.query"]),
        (INTERNAL_ALIASED, ["lib.query"]),
        (INTERNAL_QUERY + INTERNAL_DB, ["lib.query", "web.db"]),
        (FACADE_IMPORT + INTERNAL_DB, ["web.db"]),
    ],
)
def test_facade_violations(source, expected):
    assert dashboard_api.facade_violations(source) == expected


def test_facade_violations_sees_an_import_nested_in_a_function():
    source = "def main():\n    from web.config import BASE_DIR\n    return BASE_DIR\n"
    assert dashboard_api.facade_violations(source) == ["web.config"]


def test_facade_violations_reports_each_module_once():
    source = INTERNAL_QUERY + "import lib.query\n"
    assert dashboard_api.facade_violations(source) == ["lib.query"]


def test_facade_violations_rejects_unparsable_source():
    with pytest.raises(SyntaxError):
        dashboard_api.facade_violations("def main(\n")


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (FACADE_IMPORT, ["lib.dashboard_api.query_matomo"]),
        (
            FACADE_FROM_PACKAGE + "dashboard_api.query_storage('x')\n",
            ["lib.dashboard_api", "lib.dashboard_api.query_storage"],
        ),
        (STDLIB + THIRD_PARTY + RELATIVE, []),
        (INTERNAL_QUERY, ["lib.query.execute_matomo_query"]),
        (INTERNAL_ALIASED + "q.CallerType.APP\n", ["lib.query", "lib.query.CallerType", "lib.query.CallerType.APP"]),
        (INTERNAL_CONFIG + "web.config.GITHUB_TOKEN\n", ["web.config", "web.config.GITHUB_TOKEN"]),
        (
            "from web import s3\ns3.interactive.download('x')\n",
            ["web.s3", "web.s3.interactive", "web.s3.interactive.download"],
        ),
        ("from lib.query import get_metabase as gm\ngm().execute_sql('x')\n", ["lib.query.get_metabase"]),
    ],
)
def test_imported_symbols_names_what_a_dashboard_uses_down_to_the_attribute(source, expected):
    assert facade_imports.imported_symbols(source) == expected


RESULT = QueryResult(success=True, data=[])


@pytest.mark.parametrize(
    ("call", "delegate", "expected"),
    [
        (
            lambda: dashboard_api.query_matomo("inclusion", "VisitsSummary.get", {"idSite": 117}),
            "execute_matomo_query",
            {"instance": "inclusion", "method": "VisitsSummary.get", "params": {"idSite": 117}, "timeout": 180},
        ),
        (
            lambda: dashboard_api.query_metabase("les_emplois", sql="SELECT 1"),
            "execute_metabase_query",
            {"instance": "les_emplois", "sql": "SELECT 1", "card_id": None, "timeout": 60},
        ),
        (
            lambda: dashboard_api.query_metabase("les_emplois", card_id=42, timeout=90),
            "execute_metabase_query",
            {"instance": "les_emplois", "sql": None, "card_id": 42, "timeout": 90},
        ),
        (
            lambda: dashboard_api.query_data_inclusion("SELECT 1"),
            "execute_data_inclusion_query",
            {"sql": "SELECT 1", "timeout": 60},
        ),
        (
            lambda: dashboard_api.query_datadog("service:dora status:error", 7, group_by=["@http.status_code"]),
            "execute_datadog_query",
            {
                "search": "service:dora status:error",
                "days": 7,
                "group_by": ["@http.status_code"],
                "compute": None,
                "window": None,
                "timeout": 60,
            },
        ),
        (
            lambda: dashboard_api.count_datadog(
                "service:dora", distinct="@usr.id", window=("2026-08-01", "2026-09-01")
            ),
            "execute_datadog_count",
            {
                "search": "service:dora",
                "days": 7,
                "distinct": "@usr.id",
                "window": ("2026-08-01", "2026-09-01"),
                "timeout": 60,
            },
        ),
        (
            lambda: dashboard_api.sample_datadog("dora", "status:error", 3, limit=20),
            "execute_datadog_events",
            {"service": "dora", "search": "status:error", "days": 3, "limit": 20, "window": None, "timeout": 60},
        ),
        (
            lambda: dashboard_api.query_autometa_tables("SELECT 1"),
            "execute_autometa_tables_query",
            {"sql": "SELECT 1", "timeout": 60},
        ),
        (
            lambda: dashboard_api.query_airtable("app1", "tbl1", view="viw1", fields=["Nom"]),
            "execute_airtable_query",
            {"base_id": "app1", "table": "tbl1", "view": "viw1", "fields": ["Nom"], "formula": None, "timeout": 60},
        ),
        (
            lambda: dashboard_api.query_storage("SELECT 1 WHERE x = :x", {"x": 2}),
            "execute_dashboard_storage_query",
            {"sql": "SELECT 1 WHERE x = :x", "params": {"x": 2}, "timeout": 60},
        ),
        (
            lambda: dashboard_api.query_appli_monrecap("UPDATE t SET a = :a", {"a": 1}, timeout=30),
            "execute_appli_monrecap_query",
            {"sql": "UPDATE t SET a = :a", "params": {"a": 1}, "timeout": 30},
        ),
        (
            lambda: dashboard_api.query_github("repos/o/r/pulls", {"state": "closed"}),
            "execute_github_query",
            {"path": "repos/o/r/pulls", "params": {"state": "closed"}, "timeout": 30},
        ),
        (
            lambda: dashboard_api.query_notion("db1", filter={"property": "Statut"}, sorts=[{"property": "Date"}]),
            "execute_notion_query",
            {"database_id": "db1", "filter": {"property": "Statut"}, "sorts": [{"property": "Date"}]},
        ),
        (
            lambda: dashboard_api.query_tally("form1", filter="completed"),
            "execute_tally_query",
            {"form_id": "form1", "filter": "completed", "timeout": 30},
        ),
        (
            lambda: dashboard_api.query_zendesk("views/count_many", {"ids": "1,2"}),
            "execute_zendesk_query",
            {"path": "views/count_many", "params": {"ids": "1,2"}},
        ),
        (
            lambda: dashboard_api.search_zendesk_tickets("group:emplois", sort_by="created_at", max_results=1000),
            "execute_zendesk_search",
            {"query": "group:emplois", "sort_by": "created_at", "sort_order": None, "max_results": 1000},
        ),
    ],
)
def test_query_delegates_as_an_app_caller(mocker, call, delegate, expected):
    # Why: autospec fait porter la signature réelle de lib.query au mock — un paramètre renommé
    # en amont fait échouer ce test au lieu de casser silencieusement les TDB de production.
    spy = mocker.patch(f"lib.query.{delegate}", autospec=True, return_value=RESULT)
    assert call() is RESULT
    assert spy.call_args.kwargs == {**expected, "caller": CallerType.APP}


def test_query_appli_monrecap_is_exported():
    assert "query_appli_monrecap" in dashboard_api.__all__


def test_by_count_is_re_exported_unchanged():
    assert dashboard_api.by_count is by_count


@pytest.mark.parametrize(
    "call",
    [
        lambda: dashboard_api.query_datadog(None),
        lambda: dashboard_api.query_datadog("service:x", group_by=5),
        lambda: dashboard_api.count_datadog("service:x", window="hier"),
        lambda: dashboard_api.sample_datadog("x", window=("2026-09-01",)),
        lambda: dashboard_api.sample_datadog("x", limit=None),
        lambda: dashboard_api.sample_datadog("service:*"),
    ],
)
def test_datadog_functions_turn_a_bad_argument_into_a_failed_result(mocker, call):
    mocker.patch("lib.query.DatadogClient", autospec=True)

    result = call()

    assert result.success is False
    assert result.error


def test_dod_6_list_variants_targets_the_running_dashboard(mocker):
    mocker.patch("web.config.dashboard_slug", return_value="multi")
    declared = [
        {"key": "67", "label": "Bas-Rhin", "token": "t", "path": "data/t.json", "url": "/interactive/multi/?q=t"}
    ]
    spy = mocker.patch("lib.variants.list_variants", autospec=True, return_value=declared)

    assert dashboard_api.list_variants() == declared
    assert spy.call_args.args == ("multi",)


def test_dod_6_list_variants_accepts_an_explicit_slug_for_local_runs(mocker):
    mocker.patch("web.config.dashboard_slug", return_value=None)
    spy = mocker.patch("lib.variants.list_variants", autospec=True, return_value=[])

    assert dashboard_api.list_variants("multi") == []
    assert spy.call_args.args == ("multi",)


def test_dod_6_list_variants_without_a_dashboard_is_refused(mocker):
    mocker.patch("web.config.dashboard_slug", return_value=None)
    with pytest.raises(RuntimeError, match="AUTOMETA_DASHBOARD_SLUG"):
        dashboard_api.list_variants()


def test_query_airtable_is_exported():
    assert "query_airtable" in dashboard_api.__all__


@pytest.mark.parametrize(
    ("client", "error"),
    [
        ({"side_effect": AirtableError("AIRTABLE_TOKEN not set")}, "AIRTABLE_TOKEN not set"),
        ({"return_value.__enter__.return_value.list_records.side_effect": AirtableError("HTTP 403")}, "HTTP 403"),
    ],
    ids=["missing-token", "http-error"],
)
def test_query_airtable_turns_a_client_failure_into_a_failed_result(mocker, client, error):
    mocker.patch("lib.query.AirtableClient", **client)

    result = dashboard_api.query_airtable("app1", "tbl1")

    assert result.success is False
    assert result.error == error


def make_dashboard(slug, archived=False):
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    return Dashboard(
        slug=slug,
        title=slug.upper(),
        description="d",
        website="emplois",
        category="c",
        first_author_email="alice@example.org",
        is_archived=archived,
        has_cron=True,
        created_at=now,
        updated_at=now,
    )


def make_publication(slug, publication_id, environment, unpublished=False):
    published_at = datetime(2026, 10, 2, tzinfo=timezone.utc)
    return DashboardPublication(
        dashboard_slug=slug,
        publication_id=publication_id,
        environment=environment,
        published_by="bob@example.org",
        published_at=published_at,
        unpublished_at=published_at if unpublished else None,
    )


@pytest.mark.integration
@pytest.mark.usefixtures("app")
def test_list_dashboards_lists_active_dashboards_and_their_online_publications_without_authors():
    with get_db() as session:
        session.add_all([make_dashboard("b-actif"), make_dashboard("a-archive", archived=True)])
        session.flush()
        session.add_all([
            make_publication("b-actif", "p1", "production"),
            make_publication("b-actif", "p2", "staging", unpublished=True),
            make_publication("a-archive", "p3", "production"),
        ])

    result = dashboard_api.list_dashboards()

    assert result.data == [
        {
            "slug": "b-actif",
            "title": "B-ACTIF",
            "description": "d",
            "website": "emplois",
            "category": "c",
            "has_cron": True,
            "has_api_access": False,
            "created_at": "2026-10-01T00:00:00+00:00",
            "updated_at": "2026-10-01T00:00:00+00:00",
            "publications": [{"environment": "production", "published_at": "2026-10-02T00:00:00+00:00"}],
        }
    ]
    assert "example.org" not in str(result.data)


def test_list_dashboards_turns_a_database_failure_into_a_failed_result(mocker):
    mocker.patch("lib.dashboard_api.get_db", side_effect=OperationalError("SELECT", {}, Exception("down")))

    result = dashboard_api.list_dashboards()

    assert result.success is False
    assert "down" in result.error
