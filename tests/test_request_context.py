import pytest
import sentry_sdk
from fastapi import FastAPI
from fastapi.testclient import TestClient

from web.request_context import (
    REQUEST_ID_HEADER,
    current_client_ip,
    current_conversation_id,
    current_request_id,
    current_user_id,
    request_id_middleware,
    reset_conversation_id,
    set_conversation_id,
)


@pytest.fixture
def client():
    app = FastAPI()
    app.middleware("http")(request_id_middleware)

    @app.get("/echo")
    def echo():
        return {
            "request_id": current_request_id.get(),
            "user_id": current_user_id.get(),
            "client_ip": current_client_ip.get(),
        }

    return TestClient(app)


def test_generates_request_id_when_missing(client):
    response = client.get("/echo")
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] is not None
    assert len(body["request_id"]) == 32
    assert response.headers[REQUEST_ID_HEADER] == body["request_id"]


def test_propagates_incoming_request_id(client):
    response = client.get("/echo", headers={REQUEST_ID_HEADER: "given-id"})
    assert response.json()["request_id"] == "given-id"
    assert response.headers[REQUEST_ID_HEADER] == "given-id"


def test_request_id_isolated_across_requests(client):
    r1 = client.get("/echo")
    r2 = client.get("/echo")
    assert r1.json()["request_id"] != r2.json()["request_id"]


def test_binds_user_id_and_client_ip_from_request(client):
    response = client.get("/echo", headers={"X-Forwarded-User": "alice"})
    body = response.json()
    assert body["user_id"] == "alice"
    assert body["client_ip"] == "testclient"


def test_user_id_and_client_ip_default_to_none_when_absent(client):
    body = client.get("/echo").json()
    assert body["user_id"] is None
    assert body["client_ip"] == "testclient"


@pytest.mark.parametrize(
    ("header_value", "expected"),
    [
        ("203.0.113.42", "203.0.113.42"),
        ("203.0.113.42, 10.0.0.1, 10.0.0.2", "203.0.113.42"),
        ("  203.0.113.42  , 10.0.0.1", "203.0.113.42"),
    ],
)
def test_client_ip_uses_leftmost_x_forwarded_for(client, header_value, expected):
    body = client.get("/echo", headers={"X-Forwarded-For": header_value}).json()
    assert body["client_ip"] == expected


def test_set_conversation_id_updates_contextvar_and_sentry_tag():
    token = set_conversation_id("conv-42")
    try:
        assert current_conversation_id.get() == "conv-42"
        scope_tags = sentry_sdk.get_isolation_scope()._tags or {}
        assert scope_tags.get("conversation_id") == "conv-42"
    finally:
        reset_conversation_id(token)
    assert current_conversation_id.get() is None


def test_set_conversation_id_skips_sentry_tag_when_none():
    scope = sentry_sdk.get_isolation_scope()
    scope._tags = (scope._tags or {}) | {"conversation_id": "previous"}

    token = set_conversation_id(None)
    try:
        # Tag is not overwritten when conversation_id is None — set_tag was not called.
        assert (scope._tags or {}).get("conversation_id") == "previous"
    finally:
        reset_conversation_id(token)
        scope._tags.pop("conversation_id", None)


def test_reset_conversation_id_restores_previous_value():
    outer = set_conversation_id("outer")
    inner = set_conversation_id("inner")
    assert current_conversation_id.get() == "inner"

    reset_conversation_id(inner)
    assert current_conversation_id.get() == "outer"
    reset_conversation_id(outer)
