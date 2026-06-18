"""Tests for web.routes.query CORS handling."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.query import QueryResult
from web.config import CORS_ALLOWED_ORIGINS
from web.routes import query as query_route
from web.routes.query import coerce_timeout, cors_headers, validate_query_request


def _client():
    app = FastAPI()
    app.include_router(query_route.router)
    return TestClient(app)


def test_query_serializes_postgres_native_types(mocker):
    rows = [[date(2026, 6, 18), datetime(2026, 6, 18, 12, 0), Decimal("3.14")]]
    mocker.patch.object(
        query_route,
        "execute_query",
        return_value=QueryResult(
            success=True,
            data={"columns": ["day", "ts", "amount"], "rows": rows, "row_count": 1},
            execution_time_ms=1,
        ),
    )

    response = _client().post("/api/query", json={"source": "autometa_tables_db", "sql": "SELECT 1"})

    assert response.status_code == 200
    assert response.json()["data"]["rows"] == [["2026-06-18", "2026-06-18T12:00:00", 3.14]]


def test_cors_headers_allowed_origin_from_config():
    origin = next(iter(CORS_ALLOWED_ORIGINS))
    headers = cors_headers(origin)
    assert headers["Access-Control-Allow-Origin"] == origin
    assert headers["Access-Control-Allow-Methods"] == "POST, OPTIONS"
    assert headers["Access-Control-Allow-Headers"] == "Content-Type"
    assert headers["Access-Control-Allow-Credentials"] == "true"


@pytest.mark.parametrize("origin", [None, "", "https://evil.example.com", "http://localhost:9999"])
def test_cors_headers_rejects_unknown_origin(origin):
    assert cors_headers(origin) == {}


def test_cors_allowed_origins_parsed_from_env(monkeypatch):
    import importlib

    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", " https://a.example , https://b.example ,, ")
    import web.config

    importlib.reload(web.config)
    try:
        assert web.config.CORS_ALLOWED_ORIGINS == {"https://a.example", "https://b.example"}
    finally:
        monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
        importlib.reload(web.config)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, "source is required"),
        ({"source": "metabase"}, "instance is required for metabase and matomo sources"),
        ({"source": "matomo"}, "instance is required for metabase and matomo sources"),
        ({"source": "metabase", "instance": "stats"}, None),
        ({"source": "matomo", "instance": "inclusion"}, None),
        ({"source": "dashboard_storage", "sql": "SELECT 1"}, None),
        ({"source": "matometa_db", "sql": "SELECT 1"}, None),
        ({"source": "data_inclusion", "sql": "SELECT 1"}, None),
        ({"source": "autometa_tables_db", "sql": "SELECT 1"}, None),
        ({"source": "dashboard_storage"}, "sql is required for this source"),
        ({"source": "data_inclusion"}, "sql is required for this source"),
    ],
)
def test_validate_query_request(data, expected):
    assert validate_query_request(data) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (30, 30),
        ("45", 45),
        (60.9, 60),
        (0, 1),
        (-5, 1),
        (10_000, 600),
        ("evil", 60),
        (None, 60),
        ("0 -c search_path=public", 60),
    ],
)
def test_coerce_timeout(value, expected):
    assert coerce_timeout(value) == expected
