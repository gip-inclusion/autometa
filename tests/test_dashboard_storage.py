import pytest

from lib.dashboard_storage import execute_sql
from lib.pg import QueryResult


def make_sa_mocks(mocker, columns, rows, returns_rows=True, rowcount=-1):
    mock_result = mocker.MagicMock()
    mock_result.keys.return_value = columns
    mock_result.fetchall.return_value = rows
    mock_result.returns_rows = returns_rows
    mock_result.rowcount = rowcount
    mock_conn = mocker.MagicMock()
    mock_conn.__enter__ = mocker.MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = mocker.MagicMock(return_value=False)
    mock_conn.execute.return_value = mock_result
    mock_engine = mocker.MagicMock()
    mock_engine.begin.return_value = mock_conn
    return mock_engine, mock_conn


def test_execute_sql_returns_rows(mocker):
    mock_engine, _ = make_sa_mocks(mocker, ["id"], [(1,)])
    mocker.patch("lib.dashboard_storage.build_engine", return_value=mock_engine)
    mocker.patch("lib.dashboard_storage.emit_api_signal")

    result = execute_sql(database_url="postgresql://u:p@db/app", sql="SELECT id FROM dashboard_storage.t")

    assert result == QueryResult(columns=["id"], rows=[[1]], row_count=1)


def test_execute_sql_uses_begin_for_commit(mocker):
    mock_engine, _ = make_sa_mocks(mocker, [], [])
    mocker.patch("lib.dashboard_storage.build_engine", return_value=mock_engine)
    mocker.patch("lib.dashboard_storage.emit_api_signal")

    execute_sql(database_url="postgresql://u:p@db/app", sql="SELECT 1")

    mock_engine.begin.assert_called_once()


def test_execute_sql_binds_named_params(mocker):
    mock_engine, mock_conn = make_sa_mocks(mocker, ["n"], [(1,)])
    mocker.patch("lib.dashboard_storage.build_engine", return_value=mock_engine)
    mocker.patch("lib.dashboard_storage.emit_api_signal")

    execute_sql(database_url="postgresql://u:p@db/app", sql="SELECT :n", params={"n": 1})

    assert mock_conn.execute.call_args.args[1] == {"n": 1}


@pytest.mark.parametrize(("rowcount", "expected"), [(3, 3), (-1, 0)])
def test_execute_sql_ddl_without_resultset(mocker, rowcount, expected):
    mock_engine, _ = make_sa_mocks(mocker, [], [], returns_rows=False, rowcount=rowcount)
    mocker.patch("lib.dashboard_storage.build_engine", return_value=mock_engine)
    mocker.patch("lib.dashboard_storage.emit_api_signal")

    result = execute_sql(database_url="postgresql://u:p@db/app", sql="UPDATE dashboard_storage.t SET x = 1")

    assert result == QueryResult(columns=[], rows=[], row_count=expected)


def test_execute_sql_emits_signal(mocker):
    mock_engine, _ = make_sa_mocks(mocker, [], [])
    mocker.patch("lib.dashboard_storage.build_engine", return_value=mock_engine)
    emit = mocker.patch("lib.dashboard_storage.emit_api_signal")

    execute_sql(database_url="postgresql://u:p@db/app", sql="SELECT 1")

    assert emit.call_args.kwargs["source"] == "dashboard_storage"
