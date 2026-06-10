"""Tests for ownership checks on conversation mutation routes."""

import pytest

from web.database import store

ALICE = "alice@example.com"
BOB = "bob@example.com"


def headers(email):
    return {"X-Forwarded-Email": email}


def make_request(client, method, path, email, running=False):
    conv = store.create_conversation(user_id=ALICE)
    if running:
        store.update_conversation(conv.id, needs_response=True)
    payloads = {"PATCH": {"title": "pirate"}, "PUT": {"tags": []}}
    kwargs = {"json": payloads[method]} if method in payloads else {}
    return conv, client.request(method, f"/api/conversations/{conv.id}{path}", headers=headers(email), **kwargs)


@pytest.mark.parametrize(
    "method,path,running",
    [
        ("PATCH", "", False),
        ("POST", "/generate-title", False),
        ("PUT", "/tags", False),
        ("POST", "/cancel", True),
    ],
)
def test_mutations_denied_for_non_owner(client, method, path, running):
    conv, r = make_request(client, method, path, BOB, running=running)

    assert r.status_code == 403
    if method == "PATCH":
        assert store.get_conversation(conv.id).title != "pirate"


@pytest.mark.parametrize(
    "method,path,running",
    [
        ("PATCH", "", False),
        ("PUT", "/tags", False),
        ("POST", "/cancel", True),
    ],
)
def test_mutations_allowed_for_owner(client, mocker, method, path, running):
    mocker.patch("web.routes.conversations.runner.cancel", mocker.AsyncMock())
    conv, r = make_request(client, method, path, ALICE, running=running)

    assert r.status_code == 200
    if method == "PATCH":
        assert store.get_conversation(conv.id).title == "pirate"


def test_patch_unknown_conversation_is_404(client):
    r = client.patch("/api/conversations/nope", headers=headers(ALICE), json={"title": "x"})

    assert r.status_code == 404
