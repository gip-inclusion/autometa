"""Tests de la file des messages en attente dans web/stores/conversations.py."""

import threading

import pytest

from web.database import store

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

ALICE = "alice@example.com"


def make_conversation(running: bool = True):
    conv = store.create_conversation(user_id=ALICE)
    store.add_message(conv.id, "user", "q0")
    if running:
        store.update_conversation(conv.id, needs_response=True)
    return conv


def contents(conv_id: str, status: str) -> list[str]:
    return [e["content"] for e in store.pending_messages(conv_id) if e["status"] == status]


def test_queue_message_adds_to_a_running_conversation_in_order():
    conv = make_conversation()

    store.queue_message(conv.id, "q1")
    waiting = store.queue_message(conv.id, "q2")

    assert [e["content"] for e in waiting] == ["q1", "q2"]
    assert contents(conv.id, "waiting") == ["q1", "q2"]


def test_queue_message_on_an_idle_conversation_stores_nothing():
    conv = make_conversation(running=False)

    assert store.queue_message(conv.id, "q1") is None
    assert store.pending_messages(conv.id) == []


def test_a_flushing_end_of_turn_sends_the_waiting_messages_and_keeps_the_turn_running():
    conv = make_conversation()
    store.queue_message(conv.id, "q1")
    store.queue_message(conv.id, "q2")

    sent = store.end_turn(conv.id, flush=True)

    reloaded = store.get_conversation(conv.id)
    assert [m.content for m in sent] == ["q1", "q2"]
    assert [(m.type, m.content) for m in reloaded.messages] == [("user", "q0"), ("user", "q1"), ("user", "q2")]
    assert [m.id for m in sent] == [m.id for m in reloaded.messages[1:]]
    assert reloaded.needs_response
    assert reloaded.pending_messages == []


@pytest.mark.parametrize(
    ("flush", "returned"), [(True, []), (False, ["q1"])], ids=["fin propre, file vide", "autre fin"]
)
def test_an_end_of_turn_that_sends_nothing_frees_the_conversation(flush, returned):
    conv = make_conversation()
    if returned:
        store.queue_message(conv.id, "q1")

    assert store.end_turn(conv.id, flush=flush) == []

    assert not store.get_conversation(conv.id).needs_response
    assert contents(conv.id, "returned") == returned


def test_returned_messages_stay_through_later_turns_until_acknowledged():
    conv = make_conversation()
    store.queue_message(conv.id, "q1")
    store.end_turn(conv.id, flush=False)
    store.update_conversation(conv.id, needs_response=True)
    store.queue_message(conv.id, "q2")

    store.end_turn(conv.id, flush=True)

    assert contents(conv.id, "returned") == ["q1"]


@pytest.mark.parametrize("returned", [False, True], ids=["en attente", "rendu"])
def test_take_queued_hands_the_text_back_once(returned):
    conv = make_conversation()
    entry_id = store.queue_message(conv.id, "q1")[0]["id"]
    if returned:
        store.end_turn(conv.id, flush=False)

    assert store.take_queued(conv.id, entry_id) == "q1"
    assert store.take_queued(conv.id, entry_id) is None
    assert store.pending_messages(conv.id) == []


def test_ack_returned_forgets_only_the_acknowledged_returned_messages():
    conv = make_conversation()
    store.queue_message(conv.id, "q1")
    store.queue_message(conv.id, "q2")
    store.end_turn(conv.id, flush=False)
    first, second = (e["id"] for e in store.pending_messages(conv.id))
    store.update_conversation(conv.id, needs_response=True)
    waiting = store.queue_message(conv.id, "q3")[0]["id"]

    store.ack_returned(conv.id, [first, waiting])

    assert [e["id"] for e in store.pending_messages(conv.id)] == [second, waiting]


@pytest.mark.parametrize("flush", [False, True], ids=["file rendue", "file envoyée"])
def test_a_message_queued_as_the_turn_ends_never_waits_on_an_idle_conversation(flush):
    for _ in range(20):
        conv = make_conversation()
        barrier = threading.Barrier(2)

        def queue(conv_id=conv.id):
            barrier.wait()
            store.queue_message(conv_id, "q1")

        def end(conv_id=conv.id):
            barrier.wait()
            store.end_turn(conv_id, flush=flush)

        threads = [threading.Thread(target=queue), threading.Thread(target=end)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        reloaded = store.get_conversation(conv.id)
        assert reloaded.needs_response or not contents(conv.id, "waiting")


def test_a_fork_leaves_the_queue_behind():
    conv = make_conversation()
    store.queue_message(conv.id, "q1")

    fork = store.fork_conversation(conv.id, "bob@example.com")

    assert [e["content"] for e in store.get_conversation(conv.id).pending_messages] == ["q1"]
    assert fork.pending_messages == []
