"""Tests for lib/query.py — the public query API."""

import pytest


def test_query_module_imports():
    from lib import query

    assert hasattr(query, "execute_query")
    assert hasattr(query, "execute_metabase_query")
    assert hasattr(query, "execute_matomo_query")
    assert hasattr(query, "CallerType")
    assert hasattr(query, "QueryResult")
    assert hasattr(query, "MatomoAPI")
    assert hasattr(query, "MetabaseAPI")
    assert hasattr(query, "MatomoError")
    assert hasattr(query, "MetabaseError")


def test_caller_type_enum():
    from lib.query import CallerType

    assert CallerType.AGENT.value == "agent"
    assert CallerType.APP.value == "app"


def test_query_result_dataclass():
    from lib.query import QueryResult

    result = QueryResult(success=True, data={"test": 1}, execution_time_ms=100)
    assert result.success is True
    assert result.data == {"test": 1}
    assert result.error is None
    assert result.execution_time_ms == 100


def test_public_api_exports():
    from lib import query

    assert hasattr(query, "execute_query")
    assert hasattr(query, "execute_metabase_query")
    assert hasattr(query, "execute_matomo_query")
    assert hasattr(query, "MatomoAPI")
    assert hasattr(query, "MetabaseAPI")


def metabase_api_mock(mocker):
    from lib.metabase import QueryResult as MetabaseQueryResult

    mock_result = MetabaseQueryResult(
        columns=["id", "name"],
        rows=[[1, "test"]],
        row_count=1,
    )
    mock_api = mocker.MagicMock()
    mock_api.execute_sql.return_value = mock_result
    mock_api.execute_card.return_value = mock_result
    mock_api.caller = "agent"
    return mock_api


def test_execute_metabase_sql(mocker):
    from lib.query import CallerType, execute_metabase_query

    mock_api = metabase_api_mock(mocker)
    mocker.patch("lib.query.get_metabase", return_value=mock_api)

    result = execute_metabase_query(
        instance="stats",
        caller=CallerType.AGENT,
        sql="SELECT 1",
        database_id=2,
    )

    assert result.success is True
    assert result.data["row_count"] == 1
    mock_api.execute_sql.assert_called_once()


def test_execute_metabase_card(mocker):
    from lib.query import CallerType, execute_metabase_query

    mock_api = metabase_api_mock(mocker)
    mocker.patch("lib.query.get_metabase", return_value=mock_api)

    result = execute_metabase_query(
        instance="stats",
        caller=CallerType.AGENT,
        card_id=123,
    )

    assert result.success is True
    mock_api.execute_card.assert_called_once_with(123, timeout=60)


def test_execute_metabase_requires_sql_or_card(mocker):
    from lib.query import CallerType, execute_metabase_query

    mock_api = metabase_api_mock(mocker)
    mocker.patch("lib.query.get_metabase", return_value=mock_api)

    result = execute_metabase_query(
        instance="stats",
        caller=CallerType.AGENT,
    )

    assert result.success is False
    assert "sql+database_id or card_id" in result.error


def test_execute_matomo_query(mocker):
    from lib.query import CallerType, execute_matomo_query

    mock_api = mocker.MagicMock()
    mock_api.request.return_value = {"nb_visits": 100}
    mock_api.caller = "agent"
    mocker.patch("lib.query.get_matomo", return_value=mock_api)

    result = execute_matomo_query(
        instance="inclusion",
        caller=CallerType.AGENT,
        method="VisitsSummary.get",
        params={"idSite": 117, "period": "month", "date": "2025-12-01"},
    )

    assert result.success is True
    assert result.data == {"nb_visits": 100}
    mock_api.request.assert_called_once()


def test_list_metabase_models(mocker):
    from lib.query import CallerType, list_metabase_models

    mock_api = mocker.MagicMock()
    mock_api.list_models.return_value = [{"id": 1, "name": "Model A"}, {"id": 2, "name": "Model B"}]
    mock_api.caller = "agent"
    mocker.patch("lib.query.get_metabase", return_value=mock_api)

    result = list_metabase_models(instance="data_inclusion", caller=CallerType.AGENT)

    assert result.success is True
    assert len(result.data) == 2
    mock_api.list_models.assert_called_once()


def test_list_metabase_models_error(mocker):
    from lib.metabase import MetabaseError
    from lib.query import CallerType, list_metabase_models

    mock_api = mocker.MagicMock()
    mock_api.list_models.side_effect = MetabaseError("HTTP 401: Unauthorized")
    mocker.patch("lib.query.get_metabase", return_value=mock_api)

    result = list_metabase_models(instance="data_inclusion", caller=CallerType.AGENT)

    assert result.success is False
    assert "401" in result.error


@pytest.mark.parametrize(
    "source, kwargs, patched",
    [
        (
            "metabase",
            {"instance": "stats", "sql": "SELECT 1", "database_id": 2},
            "lib.query.execute_metabase_query",
        ),
        (
            "matomo",
            {"instance": "inclusion", "method": "VisitsSummary.get", "params": {"idSite": 117}},
            "lib.query.execute_matomo_query",
        ),
        (
            "data_inclusion",
            {"instance": "datawarehouse", "sql": "SELECT 1"},
            "lib.query.execute_data_inclusion_query",
        ),
        (
            "autometa_tables_db",
            {"instance": "default", "sql": "SELECT 1"},
            "lib.query.execute_autometa_tables_query",
        ),
    ],
)
def test_execute_query_routes_to_source(mocker, source, kwargs, patched):
    from lib.query import CallerType, QueryResult, execute_query

    mock_executor = mocker.patch(patched)
    mock_executor.return_value = QueryResult(success=True, data={})

    execute_query(source=source, caller=CallerType.AGENT, **kwargs)

    mock_executor.assert_called_once()


def test_execute_query_unknown_source():
    from lib.query import CallerType, execute_query

    result = execute_query(
        source="unknown",
        instance="test",
        caller=CallerType.AGENT,
    )

    assert result.success is False
    assert "Unknown source" in result.error


def test_reads_conversation_id_from_env(mocker):
    from lib.metabase import QueryResult as MetabaseQueryResult
    from lib.query import CallerType, execute_metabase_query

    mock_result = MetabaseQueryResult(columns=["x"], rows=[[1]], row_count=1)
    mock_api = mocker.MagicMock()
    mock_api.execute_sql.return_value = mock_result
    mock_api.caller = "agent"
    mocker.patch("lib.query.get_metabase", return_value=mock_api)
    mocker.patch.dict("os.environ", {"MATOMETA_CONVERSATION_ID": "env-conv-123"})

    result = execute_metabase_query(
        instance="stats",
        caller=CallerType.AGENT,
        sql="SELECT 1",
        database_id=2,
    )

    assert result.success is True


@pytest.mark.integration
def test_query_integration_metabase_query_executes():
    from lib.query import CallerType, execute_metabase_query

    result = execute_metabase_query(
        instance="stats",
        caller=CallerType.AGENT,
        sql="SELECT 1 as test",
        database_id=2,
    )

    assert result.success is True
    assert result.data["row_count"] == 1


@pytest.mark.integration
def test_query_integration_matomo_query_executes():
    from lib.query import CallerType, execute_matomo_query

    result = execute_matomo_query(
        instance="inclusion",
        caller=CallerType.AGENT,
        method="SitesManager.getSitesWithAtLeastViewAccess",
        params={},
    )

    assert result.success is True
    assert isinstance(result.data, list)
