import pytest

from lib.dora_staging import ReadOnlyViolation, assert_read_only, execute_sql
from lib.pg import QueryResult

DB_URL = "postgresql://user:pass@db:5432/dora_staging"


def make_engine(mocker, columns, rows):
    result = mocker.MagicMock()
    result.keys.return_value = columns
    result.fetchall.return_value = rows
    conn = mocker.MagicMock()
    conn.__enter__ = mocker.MagicMock(return_value=conn)
    conn.__exit__ = mocker.MagicMock(return_value=False)
    conn.execute.return_value = result
    engine = mocker.MagicMock()
    engine.connect.return_value = conn
    return engine


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "  select id from structures_structure  ",
        "WITH t AS (SELECT 1) SELECT * FROM t",
        "EXPLAIN SELECT 1",
        "SHOW statement_timeout",
        "TABLE django_migrations",
        "SELECT 1;",
    ],
)
def test_assert_read_only_accepts_reads(sql):
    assert_read_only(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO t VALUES (1)",
        "update structures_structure set siret = null",
        "DELETE FROM t",
        "TRUNCATE t",
        "DROP TABLE t",
        "ALTER TABLE t ADD COLUMN c int",
        "CREATE TABLE t (id int)",
        "GRANT ALL ON t TO public",
        "SELECT 1; DROP TABLE t",
        "",
    ],
)
def test_assert_read_only_rejects_writes(sql):
    with pytest.raises(ReadOnlyViolation):
        assert_read_only(sql)


def test_execute_sql_returns_query_result(mocker):
    mocker.patch("lib.dora_staging.build_engine", return_value=make_engine(mocker, ["id"], [(1,)]))
    mocker.patch("lib.dora_staging.emit_api_signal")

    assert execute_sql(database_url=DB_URL, sql="SELECT id FROM t") == QueryResult(
        columns=["id"], rows=[[1]], row_count=1
    )


def test_execute_sql_opens_a_read_only_engine(mocker):
    build_engine = mocker.patch("lib.dora_staging.build_engine", return_value=make_engine(mocker, [], []))
    mocker.patch("lib.dora_staging.emit_api_signal")

    execute_sql(database_url=DB_URL, sql="SELECT 1", timeout=30)

    build_engine.assert_called_once_with(DB_URL, 30, read_only=True)


def test_execute_sql_emits_signal(mocker):
    mocker.patch("lib.dora_staging.build_engine", return_value=make_engine(mocker, [], []))
    signal = mocker.patch("lib.dora_staging.emit_api_signal")

    execute_sql(database_url=DB_URL, sql="SELECT 1")

    signal.assert_called_once_with(source="dora_staging", instance="staging", url=DB_URL, sql="SELECT 1")


def test_execute_sql_never_connects_for_a_write(mocker):
    build_engine = mocker.patch("lib.dora_staging.build_engine")
    signal = mocker.patch("lib.dora_staging.emit_api_signal")

    with pytest.raises(ReadOnlyViolation):
        execute_sql(database_url=DB_URL, sql="DELETE FROM structures_structure")

    build_engine.assert_not_called()
    signal.assert_not_called()


def test_query_wrapper_requires_configuration(mocker):
    from lib.query import CallerType, execute_dora_staging_query

    mocker.patch("web.config.DORA_STAGING_DB_URL", "")

    result = execute_dora_staging_query(sql="SELECT 1", caller=CallerType.AGENT)

    assert not result.success
    assert "DORA_STAGING_DB_URL" in result.error


def test_query_wrapper_reports_read_only_violation(mocker):
    from lib.query import CallerType, execute_dora_staging_query

    mocker.patch("web.config.DORA_STAGING_DB_URL", DB_URL)
    engine = mocker.patch("lib.dora_staging.build_engine")

    result = execute_dora_staging_query(sql="UPDATE t SET a = 1", caller=CallerType.AGENT)

    assert not result.success
    assert "lecture seule" in result.error
    engine.assert_not_called()


def test_query_wrapper_returns_rows(mocker):
    from lib.query import CallerType, execute_dora_staging_query

    mocker.patch("web.config.DORA_STAGING_DB_URL", DB_URL)
    mocker.patch("lib.dora_staging.build_engine", return_value=make_engine(mocker, ["n"], [(3,)]))
    mocker.patch("lib.dora_staging.emit_api_signal")

    result = execute_dora_staging_query(sql="SELECT count(*) AS n FROM t", caller=CallerType.AGENT)

    assert result.success
    assert result.data == {"columns": ["n"], "rows": [[3]], "row_count": 1}
