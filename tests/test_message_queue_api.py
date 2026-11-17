"""Tests des routes de la file d'attente dans web/routes/conversations.py."""

import pytest

from web.database import store

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

ALICE = "alice@example.com"
BOB = "bob@example.com"


def headers(email=ALICE):
    return {"X-Forwarded-Email": email}


@pytest.fixture
def runner(mocker):
    mocker.patch("web.routes.conversations.generate_conversation_title")
    mocker.patch("web.routes.conversations.generate_conversation_tags")
    runner = mocker.patch("web.routes.conversations.runner")
    runner.submit = mocker.AsyncMock()
    runner.notify = mocker.AsyncMock()
    return runner


def running_conversation(*queued: str, conv_type: str = "exploration"):
    conv = store.create_conversation(user_id=ALICE, conv_type=conv_type)
    store.start_turn(conv.id, "q0")
    for text in queued:
        store.queue_message(conv.id, text)
    return conv


def send_later(client, conv_id, content):
    return client.post(
        f"/api/conversations/{conv_id}/messages", headers=headers(), json={"content": content, "queue": True}
    )


def test_a_message_sent_during_a_turn_waits(client, runner):
    conv = running_conversation()

    r = send_later(client, conv.id, "q1")

    assert r.status_code == 200
    assert r.json()["status"] == "queued"
    assert [e["content"] for e in r.json()["queue"]] == ["q1"]
    runner.submit.assert_not_called()
    runner.notify.assert_awaited_once_with(conv.id, "queue")


def test_a_message_sent_later_on_an_idle_conversation_starts_a_turn(client, runner):
    conv = store.create_conversation(user_id=ALICE)

    r = send_later(client, conv.id, "q0")

    assert r.json()["status"] == "started"
    runner.submit.assert_awaited_once()
    assert store.pending_messages(conv.id) == []


def test_the_queue_holds_at_most_20000_characters(client, runner):
    conv = running_conversation("x" * 15_000)

    r = send_later(client, conv.id, "y" * 5_001)

    assert r.status_code == 409
    assert r.json()["code"] == "queue_full"
    assert len(store.pending_messages(conv.id)) == 1


def test_a_knowledge_conversation_does_not_queue(client, runner):
    conv = running_conversation(conv_type="knowledge")

    r = send_later(client, conv.id, "q1")

    assert r.status_code == 409
    assert r.json()["code"] == "conversation_running"


@pytest.mark.parametrize("returned", [False, True], ids=["en attente", "rendu"])
def test_taking_a_message_back_hands_its_text(client, runner, returned):
    conv = running_conversation("q1")
    entry_id = store.pending_messages(conv.id)[0]["id"]
    if returned:
        store.end_turn(conv.id, flush=False)

    r = client.delete(f"/api/conversations/{conv.id}/queue/{entry_id}", headers=headers())

    assert r.json() == {"content": "q1"}
    assert store.pending_messages(conv.id) == []
    runner.notify.assert_awaited_once_with(conv.id, "queue")


def test_a_message_already_sent_cannot_be_taken_back(client, runner):
    conv = running_conversation("q1")
    entry_id = store.pending_messages(conv.id)[0]["id"]
    store.end_turn(conv.id, flush=True)

    r = client.delete(f"/api/conversations/{conv.id}/queue/{entry_id}", headers=headers())

    assert r.status_code == 409
    assert r.json()["code"] == "already_sent"


def test_acknowledged_returned_messages_are_forgotten(client, runner):
    conv = running_conversation("q1")
    store.end_turn(conv.id, flush=False)
    entry_id = store.pending_messages(conv.id)[0]["id"]

    r = client.post(f"/api/conversations/{conv.id}/queue/returned/ack", headers=headers(), json={"ids": [entry_id]})

    assert r.status_code == 200
    assert store.pending_messages(conv.id) == []


@pytest.mark.parametrize(
    ("method", "path"), [("DELETE", "/queue/{entry}"), ("POST", "/queue/returned/ack")], ids=["reprendre", "acquitter"]
)
def test_only_the_owner_touches_the_queue(client, runner, method, path):
    conv = running_conversation("q1")
    store.end_turn(conv.id, flush=False)
    entry_id = store.pending_messages(conv.id)[0]["id"]

    url = f"/api/conversations/{conv.id}{path.format(entry=entry_id)}"
    r = client.request(method, url, headers=headers(BOB), json={"ids": [entry_id]})

    assert r.status_code == 403
    assert len(store.pending_messages(conv.id)) == 1


@pytest.mark.parametrize(("email", "visible"), [(ALICE, True), (BOB, False)], ids=["propriétaire", "lecteur"])
def test_only_the_owner_sees_the_queue(client, runner, email, visible):
    conv = running_conversation("q1", "q2")
    store.end_turn(conv.id, flush=False)
    store.update_conversation(conv.id, needs_response=True)
    store.queue_message(conv.id, "q3")

    body = client.get(f"/api/conversations/{conv.id}", headers=headers(email)).json()

    assert [e["content"] for e in body["queue"]] == (["q3"] if visible else [])
    assert [e["content"] for e in body["returned"]] == (["q1", "q2"] if visible else [])


def test_stop_hands_the_waiting_messages_back(client):
    conv = running_conversation("q1")

    r = client.post(f"/api/conversations/{conv.id}/cancel", headers=headers())

    assert r.json()["status"] == "cancelled"
    assert [e["content"] for e in r.json()["returned"]] == ["q1"]
