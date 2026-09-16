"""Tests de la façade des tableaux de bord et de son vérificateur d'imports."""

import pytest

from lib import dashboard_api
from lib.query import CallerType, QueryResult

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
            lambda: dashboard_api.sample_datadog("service:dora status:error", 3, limit=20),
            "execute_datadog_events",
            {"search": "service:dora status:error", "days": 3, "limit": 20, "window": None, "timeout": 60},
        ),
        (
            lambda: dashboard_api.query_autometa_tables("SELECT 1"),
            "execute_autometa_tables_query",
            {"sql": "SELECT 1", "timeout": 60},
        ),
        (
            lambda: dashboard_api.query_storage("SELECT 1 WHERE x = :x", {"x": 2}),
            "execute_dashboard_storage_query",
            {"sql": "SELECT 1 WHERE x = :x", "params": {"x": 2}, "timeout": 60},
        ),
    ],
)
def test_query_delegates_as_an_app_caller(mocker, call, delegate, expected):
    # Why: autospec fait porter la signature réelle de lib.query au mock — un paramètre renommé
    # en amont fait échouer ce test au lieu de casser silencieusement les TDB de production.
    spy = mocker.patch(f"lib.query.{delegate}", autospec=True, return_value=RESULT)
    assert call() is RESULT
    assert spy.call_args.kwargs == {**expected, "caller": CallerType.APP}


def test_by_count_is_re_exported_unchanged():
    from lib.datadog import by_count

    assert dashboard_api.by_count is by_count


@pytest.mark.parametrize(
    "call",
    [
        lambda: dashboard_api.query_datadog(None),
        lambda: dashboard_api.query_datadog("service:x", group_by=5),
        lambda: dashboard_api.count_datadog("service:x", window="hier"),
        lambda: dashboard_api.sample_datadog("service:x", window=("2026-09-01",)),
    ],
)
def test_datadog_functions_turn_a_bad_argument_into_a_failed_result(mocker, call):
    mocker.patch("lib.query.DatadogClient", autospec=True)

    result = call()

    assert result.success is False
    assert result.error
