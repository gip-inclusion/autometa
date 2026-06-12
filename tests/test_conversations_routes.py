from web.database import store


def make_running_conversation(user_id):
    conv = store.create_conversation(user_id=user_id)
    store.update_conversation(conv.id, needs_response=True)
    return conv


def headers(email="alice@example.com"):
    return {"X-Forwarded-Email": email}


def test_running_returns_only_own_conversations(client):
    own = make_running_conversation("alice@example.com")
    other = make_running_conversation("bob@example.com")

    running = client.get("/api/conversations/running", headers=headers()).json()["running"]

    assert own.id in running
    assert other.id not in running


def test_running_excludes_idle_conversations(client):
    idle = store.create_conversation(user_id="alice@example.com")

    running = client.get("/api/conversations/running", headers=headers()).json()["running"]

    assert idle.id not in running


def test_running_includes_legacy_conversations_without_owner(client):
    legacy = make_running_conversation(None)

    running = client.get("/api/conversations/running", headers=headers()).json()["running"]

    assert legacy.id in running
