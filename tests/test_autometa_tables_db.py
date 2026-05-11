from lib.autometa_tables_db import execute_sql
from lib.pg import QueryResult


def make_sa_mocks(mocker, columns, rows):
    mock_result = mocker.MagicMock()
    mock_result.keys.return_value = columns
    mock_result.fetchall.return_value = rows
    mock_conn = mocker.MagicMock()
    mock_conn.__enter__ = mocker.MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = mocker.MagicMock(return_value=False)
    mock_conn.execute.return_value = mock_result
    mock_engine = mocker.MagicMock()
    mock_engine.connect.return_value = mock_conn
    return mock_engine, mock_conn


def test_execute_sql_returns_query_result(mocker):
    mock_engine, _ = make_sa_mocks(mocker, ["id", "name"], [(1, "foo")])
    mocker.patch("lib.autometa_tables_db.create_engine", return_value=mock_engine)
    mocker.patch("lib.autometa_tables_db.emit_api_signal")

    result = execute_sql(database_url="postgresql://user:pass@db:5432/tables", sql="SELECT id, name FROM t")

    assert result == QueryResult(columns=["id", "name"], rows=[[1, "foo"]], row_count=1)


def test_execute_sql_uses_nullpool(mocker):
    from sqlalchemy.pool import NullPool

    mock_engine, _ = make_sa_mocks(mocker, [], [])
    mock_create = mocker.patch("lib.autometa_tables_db.create_engine", return_value=mock_engine)
    mocker.patch("lib.autometa_tables_db.emit_api_signal")

    execute_sql(database_url="postgresql://user:pass@db:5432/tables", sql="SELECT 1")

    _, kwargs = mock_create.call_args
    assert kwargs.get("poolclass") is NullPool


def test_execute_sql_applies_statement_timeout(mocker):
    mock_engine, _ = make_sa_mocks(mocker, [], [])
    mock_create = mocker.patch("lib.autometa_tables_db.create_engine", return_value=mock_engine)
    mocker.patch("lib.autometa_tables_db.emit_api_signal")

    execute_sql(database_url="postgresql://user:pass@db:5432/tables", sql="SELECT 1", timeout=30)

    _, kwargs = mock_create.call_args
    assert kwargs.get("connect_args") == {"options": "-c statement_timeout=30000"}


def test_execute_sql_emits_signal(mocker):
    mock_engine, _ = make_sa_mocks(mocker, [], [])
    mocker.patch("lib.autometa_tables_db.create_engine", return_value=mock_engine)
    mock_signal = mocker.patch("lib.autometa_tables_db.emit_api_signal")

    execute_sql(database_url="postgresql://user:pass@db:5432/tables", sql="SELECT 1")

    mock_signal.assert_called_once_with(
        source="autometa_tables_db", instance="default", url="postgresql://user:pass@db:5432/tables", sql="SELECT 1"
    )
