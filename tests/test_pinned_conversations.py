"""Tests for conversation pinning."""

import pytest

from web.database import store


@pytest.fixture
def conversation(app):

    conv = store.create_conversation(user_id="owner@example.com")
    store.update_conversation(conv.id, title="Test conversation")
    store.add_message(conv.id, "user", "Hello")
    return conv


ADMIN_EMAIL = "admin@localhost"
NON_ADMIN_EMAIL = "user@example.com"


def test_pin_api_admin_can_pin(client, conversation):
    resp = client.post(
        f"/api/conversations/{conversation.id}/pin",
        json={"label": "Bonnes pratiques"},
        headers={"X-Forwarded-Email": ADMIN_EMAIL},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["label"] == "Bonnes pratiques"


def test_pin_api_non_admin_cannot_pin(client, conversation):
    resp = client.post(
        f"/api/conversations/{conversation.id}/pin",
        json={"label": "Test"},
        headers={"X-Forwarded-Email": NON_ADMIN_EMAIL},
    )
    assert resp.status_code == 403


def test_pin_api_admin_can_unpin(app, client, conversation):

    store.pin_conversation(conversation.id, "Pinned")

    resp = client.delete(
        f"/api/conversations/{conversation.id}/pin",
        headers={"X-Forwarded-Email": ADMIN_EMAIL},
    )
    assert resp.status_code == 200


def test_pin_api_non_admin_cannot_unpin(app, client, conversation):

    store.pin_conversation(conversation.id, "Pinned")

    resp = client.delete(
        f"/api/conversations/{conversation.id}/pin",
        headers={"X-Forwarded-Email": NON_ADMIN_EMAIL},
    )
    assert resp.status_code == 403


def test_pin_api_pin_nonexistent_conversation(client):
    resp = client.post(
        "/api/conversations/nonexistent-id/pin",
        json={"label": "Test"},
        headers={"X-Forwarded-Email": ADMIN_EMAIL},
    )
    assert resp.status_code == 404


def test_pin_api_pin_uses_title_when_no_label(client, conversation):
    resp = client.post(
        f"/api/conversations/{conversation.id}/pin",
        json={"label": ""},
        headers={"X-Forwarded-Email": ADMIN_EMAIL},
    )
    assert resp.status_code == 200
    assert resp.json()["label"] == "Test conversation"


def test_pin_database_pin_and_list(app, conversation):

    store.pin_conversation(conversation.id, "My label")
    pinned = store.list_pinned_conversations()
    assert len(pinned) == 1
    assert pinned[0].id == conversation.id
    assert pinned[0].pinned_label == "My label"
    assert pinned[0].pinned_at is not None


def test_pin_database_unpin(app, conversation):

    store.pin_conversation(conversation.id, "Label")
    store.unpin_conversation(conversation.id)
    pinned = store.list_pinned_conversations()
    assert len(pinned) == 0


def test_pin_database_multiple_pins(app):

    c1 = store.create_conversation(user_id="a@b.com")
    c2 = store.create_conversation(user_id="a@b.com")
    store.pin_conversation(c1.id, "First")
    store.pin_conversation(c2.id, "Second")
    pinned = store.list_pinned_conversations()
    assert len(pinned) == 2
    assert pinned[0].pinned_label == "First"
    assert pinned[1].pinned_label == "Second"


def test_pin_database_pinned_at_in_get_conversation(app, conversation):

    store.pin_conversation(conversation.id, "Label")
    conv = store.get_conversation(conversation.id, include_messages=False)
    assert conv.pinned_at is not None
    assert conv.pinned_label == "Label"


def test_pin_database_unpinned_conversation_has_none(app, conversation):

    conv = store.get_conversation(conversation.id, include_messages=False)
    assert conv.pinned_at is None
    assert conv.pinned_label is None


def test_pin_sidebar_pinned_visible_on_home(app, client, conversation):

    store.pin_conversation(conversation.id, "Bonnes pratiques")

    resp = client.get(
        "/",
        headers={"X-Forwarded-Email": NON_ADMIN_EMAIL},
    )
    assert resp.status_code == 200
    assert b"ri-pushpin-line" in resp.content
    # Pinned conversation shows its title (or label as fallback)
    assert b"Test conversation" in resp.content


def test_pin_sidebar_no_pins_no_pushpin(client):
    resp = client.get(
        "/",
        headers={"X-Forwarded-Email": NON_ADMIN_EMAIL},
    )
    assert resp.status_code == 200
    assert b"ri-pushpin-line" not in resp.content


def test_pin_sidebar_admin_sees_pin_button(app, client, conversation):
    resp = client.get(
        f"/explorations/{conversation.id}",
        headers={"X-Forwarded-Email": ADMIN_EMAIL},
    )
    assert resp.status_code == 200
    assert "pingler".encode() in resp.content  # Épingler contains "pingler"


def test_pin_sidebar_non_admin_no_pin_button(app, client, conversation):
    resp = client.get(
        f"/explorations/{conversation.id}",
        headers={"X-Forwarded-Email": NON_ADMIN_EMAIL},
    )
    assert resp.status_code == 200
    # The button element itself should not be rendered (JS handler refs are OK)
    assert b'id="pinConvBtn"' not in resp.content
    assert b'id="unpinConvBtn"' not in resp.content


def test_pin_sidebar_admin_sees_unpin_on_pinned(app, client, conversation):

    store.pin_conversation(conversation.id, "Test")

    resp = client.get(
        f"/explorations/{conversation.id}",
        headers={"X-Forwarded-Email": ADMIN_EMAIL},
    )
    assert resp.status_code == 200
    assert b"unpinConvBtn" in resp.content
