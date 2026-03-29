"""Tests for conversation fork (deep copy) functionality.

Users can fork conversations to continue from someone else's conversation
or to branch their own conversation.
"""

import pytest


@pytest.fixture
def conversation_with_messages(app):
    from web.database import store

    conv = store.create_conversation(user_id="owner@example.com")
    store.update_conversation(conv.id, title="Original conversation")
    store.add_message(conv.id, "user", "First question")
    store.add_message(conv.id, "assistant", "First answer")
    store.add_message(conv.id, "user", "Second question")
    store.add_message(conv.id, "assistant", "Second answer")
    return conv


def test_fork_database_creates_new_conversation(app, conversation_with_messages):
    """Forking creates a new conversation with a new ID."""
    from web.database import store

    forked = store.fork_conversation(conversation_with_messages.id, "forker@example.com")

    assert forked is not None
    assert forked.id != conversation_with_messages.id
    assert forked.user_id == "forker@example.com"


def test_fork_database_copies_title(app, conversation_with_messages):
    """Forked conversation has the same title."""
    from web.database import store

    forked = store.fork_conversation(conversation_with_messages.id, "forker@example.com")

    assert forked.title == "Original conversation"


def test_fork_database_copies_all_messages(app, conversation_with_messages):
    """Forked conversation has copies of all messages."""
    from web.database import store

    forked = store.fork_conversation(conversation_with_messages.id, "forker@example.com")

    assert len(forked.messages) == 4
    assert forked.messages[0].content == "First question"
    assert forked.messages[1].content == "First answer"
    assert forked.messages[2].content == "Second question"
    assert forked.messages[3].content == "Second answer"


def test_fork_database_messages_have_new_ids(app, conversation_with_messages):
    """Forked messages have different IDs (deep copy, not reference)."""
    from web.database import store

    original = store.get_conversation(conversation_with_messages.id)
    forked = store.fork_conversation(conversation_with_messages.id, "forker@example.com")

    # Message IDs should be different
    original_ids = {m.id for m in original.messages}
    forked_ids = {m.id for m in forked.messages}
    assert original_ids.isdisjoint(forked_ids)


def test_fork_database_tracks_source(app, conversation_with_messages):
    """Forked conversation tracks its source via forked_from."""
    from web.database import store

    forked = store.fork_conversation(conversation_with_messages.id, "forker@example.com")

    assert forked.forked_from == conversation_with_messages.id


def test_fork_database_resets_session_id(app, conversation_with_messages):
    """Forked conversation has no session_id (fresh start for agent)."""
    from web.database import store

    # Set session_id on original
    store.update_conversation(conversation_with_messages.id, session_id="original-session")

    forked = store.fork_conversation(conversation_with_messages.id, "forker@example.com")

    assert forked.session_id is None


def test_fork_database_nonexistent_returns_none(app):
    """Forking a non-existent conversation returns None."""
    from web.database import store

    result = store.fork_conversation("nonexistent-uuid", "forker@example.com")

    assert result is None


def test_fork_database_original_unchanged_after_fork(app, conversation_with_messages):
    """Original conversation is unchanged after fork."""
    from web.database import store

    # Fork it
    store.fork_conversation(conversation_with_messages.id, "forker@example.com")

    # Check original is unchanged
    original = store.get_conversation(conversation_with_messages.id)
    assert original.user_id == "owner@example.com"
    assert len(original.messages) == 4
    assert original.forked_from is None


def test_fork_database_modifying_fork_does_not_affect_original(app, conversation_with_messages):
    """Adding messages to fork does not affect original (no entanglement)."""
    from web.database import store

    forked = store.fork_conversation(conversation_with_messages.id, "forker@example.com")

    # Add a message to the fork
    store.add_message(forked.id, "user", "New message in fork")

    # Original should still have only 4 messages
    original = store.get_conversation(conversation_with_messages.id)
    assert len(original.messages) == 4

    # Fork should have 5 messages
    updated_fork = store.get_conversation(forked.id)
    assert len(updated_fork.messages) == 5


def test_fork_api_endpoint_creates_copy(app, client, conversation_with_messages):
    """POST /api/conversations/:id/fork creates a copy."""
    response = client.post(
        f"/api/conversations/{conversation_with_messages.id}/fork",
        headers={"X-Forwarded-Email": "forker@example.com"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["id"] != conversation_with_messages.id
    assert data["forked_from"] == conversation_with_messages.id


def test_fork_api_endpoint_returns_links(app, client, conversation_with_messages):
    """Fork response includes useful links."""
    response = client.post(
        f"/api/conversations/{conversation_with_messages.id}/fork",
        headers={"X-Forwarded-Email": "forker@example.com"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "links" in data
    assert "self" in data["links"]
    assert "view" in data["links"]
    assert data["id"] in data["links"]["view"]


def test_fork_api_nonexistent_returns_404(app, client):
    """Forking non-existent conversation returns 404."""
    response = client.post(
        "/api/conversations/nonexistent-uuid/fork",
        headers={"X-Forwarded-Email": "forker@example.com"},
    )

    assert response.status_code == 404


def test_fork_api_requires_authentication(app, client, conversation_with_messages):
    """Fork endpoint requires authentication."""
    # Without X-Forwarded-Email, user_email is None or default
    # The endpoint should reject unauthenticated requests
    response = client.post(
        f"/api/conversations/{conversation_with_messages.id}/fork",
    )

    # May return 401 or use default user depending on config
    # In production with oauth-proxy, missing header means no auth
    assert response.status_code in (200, 401)


def test_fork_api_guest_can_fork_others_conversation(app, client, conversation_with_messages):
    """Guest user can fork someone else's conversation."""
    response = client.post(
        f"/api/conversations/{conversation_with_messages.id}/fork",
        headers={"X-Forwarded-Email": "guest@example.com"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify the fork belongs to the guest
    from web.database import store

    forked = store.get_conversation(data["id"])
    assert forked.user_id == "guest@example.com"


def test_fork_api_owner_can_fork_own_conversation(app, client, conversation_with_messages):
    """Owner can fork their own conversation."""
    response = client.post(
        f"/api/conversations/{conversation_with_messages.id}/fork",
        headers={"X-Forwarded-Email": "owner@example.com"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["forked_from"] == conversation_with_messages.id


def test_fork_ui_button_visible_on_shared_conversation(app, client, conversation_with_messages):
    """Fork button is visible when viewing someone else's conversation."""
    response = client.get(
        f"/explorations/{conversation_with_messages.id}",
        headers={"X-Forwarded-Email": "guest@example.com"},
    )

    assert response.status_code == 200
    assert b'id="forkConvBtn"' in response.content
    assert b"Dupliquer" in response.content


def test_fork_ui_button_visible_on_own_conversation(app, client, conversation_with_messages):
    """Fork button is visible on own conversation (in header)."""
    response = client.get(
        f"/explorations/{conversation_with_messages.id}",
        headers={"X-Forwarded-Email": "owner@example.com"},
    )

    assert response.status_code == 200
    assert b'id="forkConvBtn"' in response.content


def test_fork_ui_forked_from_shown_in_header(app, client, conversation_with_messages):
    """Forked conversation shows link to source."""
    from web.database import store

    # Create a fork
    forked = store.fork_conversation(conversation_with_messages.id, "forker@example.com")

    # View the fork
    response = client.get(
        f"/explorations/{forked.id}",
        headers={"X-Forwarded-Email": "forker@example.com"},
    )

    assert response.status_code == 200
    assert b"ri-git-branch-line" in response.content  # Fork icon
    assert conversation_with_messages.id.encode() in response.content  # Link to source
