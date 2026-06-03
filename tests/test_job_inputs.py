"""Tests for publishing query results as job-accessible datasets."""

import importlib.util
import sqlite3
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from lib import job_inputs
from lib.query import QueryResult


@pytest.fixture
def fake_s3(mocker):
    up = mocker.patch("lib.job_inputs.s3.job_inputs.upload", return_value=True)
    mocker.patch("lib.job_inputs.s3.job_inputs.get_url", return_value="https://signed.example/data")
    return up


def _uploaded_bytes(up) -> bytes:
    return up.call_args.args[1]


def _query_sqlite(content: bytes, query: str):
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as tmp:
        Path(tmp.name).write_bytes(content)
        conn = sqlite3.connect(tmp.name)
        try:
            return conn.execute(query).fetchall()
        finally:
            conn.close()


def test_publish_sqlite_roundtrip(fake_s3):
    out = job_inputs.publish_dataset("dora-services", ["id", "name"], [[1, "A"], [2, "B"]])
    assert out["url"] == "https://signed.example/data"
    assert out["format"] == "sqlite"
    assert out["table"] == "data"
    assert out["row_count"] == 2
    assert out["columns"] == ["id", "name"]
    assert out["s3_path"] == "job-inputs/dora-services.sqlite"
    assert fake_s3.call_args.args[0] == "dora-services.sqlite"
    assert fake_s3.call_args.kwargs["content_type"] == "application/x-sqlite3"
    assert _query_sqlite(_uploaded_bytes(fake_s3), "SELECT id, name FROM data ORDER BY id") == [(1, "A"), (2, "B")]


def test_publish_jsonl(fake_s3):
    out = job_inputs.publish_dataset("d", ["a", "b"], [[1, "x"]], fmt="jsonl")
    assert out["s3_path"] == "job-inputs/d.jsonl"
    assert out["table"] is None
    assert _uploaded_bytes(fake_s3).decode().strip() == '{"a": 1, "b": "x"}'
    assert fake_s3.call_args.kwargs["content_type"] == "application/x-ndjson"


def test_publish_csv(fake_s3):
    job_inputs.publish_dataset("d", ["a", "b"], [[1, "x"]], fmt="csv")
    assert _uploaded_bytes(fake_s3).decode().splitlines() == ["a,b", "1,x"]
    assert fake_s3.call_args.kwargs["content_type"] == "text/csv"


def test_coerces_nonprimitive_values(fake_s3):
    job_inputs.publish_dataset("d", ["amount", "day"], [[Decimal("3.50"), date(2026, 6, 3)]], fmt="jsonl")
    content = _uploaded_bytes(fake_s3).decode()
    assert '"3.50"' in content
    assert '"2026-06-03"' in content


def test_quotes_identifiers_with_special_chars(fake_s3):
    job_inputs.publish_dataset("d", ['weird "col"', "order"], [[1, 2]])
    assert _query_sqlite(_uploaded_bytes(fake_s3), 'SELECT "order" FROM data') == [(2,)]


@pytest.mark.parametrize("bad", ["", "../x", "UPPER", "with space", "with/slash", "-leading"])
def test_rejects_bad_slug(fake_s3, bad):
    with pytest.raises(ValueError):
        job_inputs.publish_dataset(bad, ["a"], [[1]])


def test_rejects_bad_format(fake_s3):
    with pytest.raises(ValueError):
        job_inputs.publish_dataset("d", ["a"], [[1]], fmt="parquet")


def test_upload_failure_raises(mocker):
    mocker.patch("lib.job_inputs.s3.job_inputs.upload", return_value=False)
    with pytest.raises(RuntimeError):
        job_inputs.publish_dataset("d", ["a"], [[1]])


def test_publish_query_runs_source_then_publishes(mocker):
    mocker.patch(
        "lib.job_inputs.execute_autometa_tables_query",
        return_value=QueryResult(success=True, data={"columns": ["id"], "rows": [[1]], "row_count": 1}),
    )
    pub = mocker.patch("lib.job_inputs.publish_dataset", return_value={"url": "u"})
    out = job_inputs.publish_query("dora", "autometa_tables_db", "SELECT 1")
    assert out == {"url": "u"}
    assert pub.call_args.args[0] == "dora"
    assert pub.call_args.args[1] == ["id"]
    assert pub.call_args.args[2] == [[1]]


def test_publish_query_failed_query_raises(mocker):
    mocker.patch(
        "lib.job_inputs.execute_autometa_tables_query",
        return_value=QueryResult(success=False, data=None, error="boom"),
    )
    with pytest.raises(RuntimeError, match="boom"):
        job_inputs.publish_query("d", "autometa_tables_db", "SELECT bad")


def test_publish_query_unknown_source_raises():
    with pytest.raises(ValueError):
        job_inputs.publish_query("d", "matomo", "SELECT 1")


def _load_cli():
    path = Path("skills/publish_dataset/scripts/publish_dataset.py")
    spec = importlib.util.spec_from_file_location("publish_dataset_cli", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cli_publishes_and_prints(mocker, capsys):
    mocker.patch("lib.job_inputs.publish_query", return_value={"url": "https://x", "format": "sqlite"})
    rc = _load_cli().main(["--slug", "dora", "--source", "autometa_tables_db", "--sql", "SELECT 1"])
    assert rc == 0
    assert "https://x" in capsys.readouterr().out


def test_cli_error_returns_1(mocker, capsys):
    mocker.patch("lib.job_inputs.publish_query", side_effect=RuntimeError("query failed"))
    rc = _load_cli().main(["--slug", "d", "--source", "autometa_tables_db", "--sql", "SELECT bad"])
    assert rc == 1
    assert "query failed" in capsys.readouterr().err
