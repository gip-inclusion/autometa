"""Tests for web/routes/conversations.py — ownership and permission rules."""

import pytest

from web.config import ADMIN_USERS
from web.database import store
from web.db import get_db
from web.models import Tag

ALICE = "alice@example.com"
BOB = "bob@example.com"
ADMIN = ADMIN_USERS[0]


def headers(email=ALICE):
    return {"X-Forwarded-Email": email}


def make_tag(name, type="product", label=None):
    with get_db() as session:
        session.add(Tag(name=name, type=type, label=label or name))


def test_create_conversation_owned_by_current_user(client):
    r = client.post("/api/conversations", headers=headers())
    assert r.status_code == 200
    conv = store.get_conversation(r.json()["id"])
    assert conv.user_id == ALICE


def test_list_conversations_only_own(client):
    own = store.create_conversation(user_id=ALICE)
    other = store.create_conversation(user_id=BOB)

    ids = [c["id"] for c in client.get("/api/conversations", headers=headers()).json()["conversations"]]

    assert own.id in ids
    assert other.id not in ids


@pytest.mark.parametrize(
    "owner,viewer,is_owner",
    [
        (ALICE, ALICE, True),
        (ALICE, BOB, False),
        (None, BOB, True),
    ],
)
def test_get_conversation_shared_read_with_is_owner_flag(client, owner, viewer, is_owner):
    conv = store.create_conversation(user_id=owner)

    r = client.get(f"/api/conversations/{conv.id}", headers=headers(viewer))

    assert r.status_code == 200
    assert r.json()["is_owner"] is is_owner


def test_get_conversation_not_found(client):
    r = client.get("/api/conversations/nope", headers=headers())

    assert r.status_code == 404


def test_delete_conversation_denied_for_non_owner(client):
    conv = store.create_conversation(user_id=ALICE)

    r = client.delete(f"/api/conversations/{conv.id}", headers=headers(BOB))

    assert r.status_code == 403
    assert store.get_conversation(conv.id) is not None


@pytest.mark.parametrize("deleter", [ALICE, ADMIN])
def test_delete_conversation_allowed_for_owner_and_admin(client, deleter):
    conv = store.create_conversation(user_id=ALICE)

    r = client.delete(f"/api/conversations/{conv.id}", headers=headers(deleter))

    assert r.status_code == 200
    assert store.get_conversation(conv.id) is None


def test_pin_requires_admin(client):
    conv = store.create_conversation(user_id=ALICE)

    r = client.post(f"/api/conversations/{conv.id}/pin", headers=headers(ALICE))

    assert r.status_code == 403


def test_pin_and_unpin_as_admin(client):
    conv = store.create_conversation(user_id=ALICE)

    r = client.post(f"/api/conversations/{conv.id}/pin", headers=headers(ADMIN), json={"label": "Suivi"})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "label": "Suivi"}

    r = client.delete(f"/api/conversations/{conv.id}/pin", headers=headers(ADMIN))
    assert r.json() == {"ok": True}


def test_unpin_requires_admin(client):
    conv = store.create_conversation(user_id=ALICE)

    r = client.delete(f"/api/conversations/{conv.id}/pin", headers=headers(ALICE))

    assert r.status_code == 403


def test_fork_creates_copy_owned_by_forker(client):
    conv = store.create_conversation(user_id=ALICE)
    store.add_message(conv.id, "user", "question")

    r = client.post(f"/api/conversations/{conv.id}/fork", headers=headers(BOB))

    assert r.status_code == 200
    forked = store.get_conversation(r.json()["id"], include_messages=True)
    assert forked.user_id == BOB
    assert forked.forked_from == conv.id
    assert [m.content for m in forked.messages] == ["question"]


def test_cancel_idle_conversation_is_noop(client):
    conv = store.create_conversation(user_id=ALICE)

    r = client.post(f"/api/conversations/{conv.id}/cancel", headers=headers())

    assert r.json() == {"status": "not_running"}


@pytest.mark.parametrize(
    "payload,expected_error",
    [
        ({}, "Missing 'tags' field"),
        ({"tags": "emplois"}, "'tags' must be a list"),
    ],
)
def test_set_tags_validates_payload(client, payload, expected_error):
    conv = store.create_conversation(user_id=ALICE)

    r = client.put(f"/api/conversations/{conv.id}/tags", headers=headers(), json=payload)

    assert r.status_code == 400
    assert r.json()["error"] == expected_error


def test_set_tags_keeps_known_tags_only(client):
    make_tag("emplois")
    conv = store.create_conversation(user_id=ALICE)

    r = client.put(f"/api/conversations/{conv.id}/tags", headers=headers(), json={"tags": ["emplois", "inconnu"]})

    assert r.status_code == 200
    assert [t["name"] for t in r.json()["tags"]] == ["emplois"]


@pytest.fixture
def submit_mock(mocker):
    mocker.patch("web.routes.conversations.generate_conversation_title")
    mocker.patch("web.routes.conversations.generate_conversation_tags")
    runner = mocker.patch("web.routes.conversations.runner")
    runner.submit = mocker.AsyncMock()
    return runner.submit


def test_send_message_denied_for_non_owner(client, submit_mock):
    conv = store.create_conversation(user_id=ALICE)

    r = client.post(f"/api/conversations/{conv.id}/messages", headers=headers(BOB), json={"content": "hi"})

    assert r.status_code == 403
    submit_mock.assert_not_called()


def test_send_message_requires_content(client, submit_mock):
    conv = store.create_conversation(user_id=ALICE)

    r = client.post(f"/api/conversations/{conv.id}/messages", headers=headers(), json={})

    assert r.status_code == 400


def test_send_message_conflict_while_running(client, submit_mock):
    conv = store.create_conversation(user_id=ALICE)
    store.update_conversation(conv.id, needs_response=True)

    r = client.post(f"/api/conversations/{conv.id}/messages", headers=headers(), json={"content": "hi"})

    assert r.status_code == 409
    submit_mock.assert_not_called()


def test_send_message_persists_and_submits(client, submit_mock):
    conv = store.create_conversation(user_id=ALICE)

    r = client.post(f"/api/conversations/{conv.id}/messages", headers=headers(), json={"content": "salut"})

    assert r.status_code == 200
    assert r.json()["status"] == "started"
    submit_mock.assert_awaited_once()

    updated = store.get_conversation(conv.id, include_messages=True)
    assert updated.needs_response
    assert updated.session_id
    assert [m.content for m in updated.messages] == ["salut"]


def test_auth_status_reports_backend(client):
    r = client.get("/api/auth/status")

    assert r.status_code == 200
    body = r.json()
    assert {"backend", "auth_required", "authenticated"} <= set(body)
