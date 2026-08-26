import pytest
from sqlalchemy.pool import NullPool

import lib.pg as pg
from lib.pg import QueryResult, execute_sql

DB_URL = "postgresql://u:p@db/x"


def make_engine(mocker, columns=(), rows=(), returns_rows=True, rowcount=-1):
    result = mocker.MagicMock()
    result.keys.return_value = list(columns)
    result.fetchall.return_value = list(rows)
    result.returns_rows = returns_rows
    result.rowcount = rowcount
    conn = mocker.MagicMock()
    conn.__enter__ = mocker.MagicMock(return_value=conn)
    conn.__exit__ = mocker.MagicMock(return_value=False)
    conn.execute.return_value = result
    engine = mocker.MagicMock()
    engine.connect.return_value = conn
    engine.begin.return_value = conn
    return engine, conn


@pytest.fixture
def build_engine(mocker):
    mocker.patch("lib.pg.emit_api_signal")
    return mocker.patch("lib.pg.build_engine")


@pytest.mark.parametrize(
    ("read_only", "expected_options"),
    [
        (False, "-c statement_timeout=60000"),
        (True, "-c statement_timeout=60000 -c default_transaction_read_only=on"),
    ],
)
def test_build_engine_nullpool_and_options(mocker, read_only, expected_options):
    mock_create = mocker.patch("lib.pg.create_engine")

    pg.build_engine(DB_URL, 60, read_only=read_only)

    mock_create.assert_called_once_with(DB_URL, poolclass=NullPool, connect_args={"options": expected_options})


def test_execute_sql_returns_rows(mocker, build_engine):
    build_engine.return_value = make_engine(mocker, ["id", "name"], [(1, "foo")])[0]

    result = execute_sql(DB_URL, "SELECT id, name FROM t", source="autometa_tables_db")

    assert result == QueryResult(columns=["id", "name"], rows=[[1, "foo"]], row_count=1)


@pytest.mark.parametrize(("rowcount", "expected"), [(3, 3), (-1, 0)])
def test_execute_sql_without_resultset_reports_rowcount(mocker, build_engine, rowcount, expected):
    build_engine.return_value = make_engine(mocker, returns_rows=False, rowcount=rowcount)[0]

    result = execute_sql(DB_URL, "UPDATE t SET x = 1", source="dashboard_storage", write=True)

    assert result == QueryResult(columns=[], rows=[], row_count=expected)


def test_execute_sql_binds_named_params(mocker, build_engine):
    engine, conn = make_engine(mocker, ["n"], [(1,)])
    build_engine.return_value = engine

    execute_sql(DB_URL, "SELECT :n", source="dashboard_storage", params={"n": 1}, write=True)

    assert conn.execute.call_args.args[1] == {"n": 1}


@pytest.mark.parametrize(
    ("write", "read_only", "transaction"),
    [(False, True, "connect"), (True, False, "begin")],
)
def test_execute_sql_read_only_unless_write(mocker, build_engine, write, read_only, transaction):
    engine, _ = make_engine(mocker)
    build_engine.return_value = engine

    execute_sql(DB_URL, "SELECT 1", source="dora_staging", write=write, timeout=30)

    build_engine.assert_called_once_with(DB_URL, 30, read_only=read_only)
    getattr(engine, transaction).assert_called_once()


def test_execute_sql_emits_signal(mocker):
    mocker.patch("lib.pg.build_engine", return_value=make_engine(mocker)[0])
    signal = mocker.patch("lib.pg.emit_api_signal")

    execute_sql(DB_URL, "SELECT 1", source="dora_staging", instance="staging")

    signal.assert_called_once_with(source="dora_staging", instance="staging", url=DB_URL, sql="SELECT 1")
