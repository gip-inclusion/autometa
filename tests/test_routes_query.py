"""Tests for web.routes.query CORS handling."""

import pytest

from web.config import CORS_ALLOWED_ORIGINS
from web.routes.query import cors_headers


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
