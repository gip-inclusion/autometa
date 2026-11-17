"""Tests for the atomic turn start in web/stores/conversations.py."""

import threading

import pytest

from web.database import store

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


def make_conversation(running: bool = False):
    conv = store.create_conversation(user_id="alice@example.com")
    if running:
        store.update_conversation(conv.id, needs_response=True)
    return conv


def test_start_turn_claims_the_conversation_and_stores_the_question():
    conv = make_conversation()

    msg = store.start_turn(conv.id, "salut")

    reloaded = store.get_conversation(conv.id)
    assert reloaded.needs_response
    assert [(m.id, m.content) for m in reloaded.messages] == [(msg.id, "salut")]


def test_start_turn_on_a_running_conversation_stores_nothing():
    conv = make_conversation(running=True)

    assert store.start_turn(conv.id, "salut") is None
    assert store.get_conversation(conv.id).messages == []


def test_concurrent_starts_store_a_single_question():
    conv = make_conversation()
    barrier = threading.Barrier(2)
    results = []

    def start(text):
        barrier.wait()
        results.append(store.start_turn(conv.id, text))

    threads = [threading.Thread(target=start, args=(text,)) for text in ("un", "deux")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sum(r is not None for r in results) == 1
    assert len(store.get_conversation(conv.id).messages) == 1


def test_restart_turn_claims_only_once():
    conv = make_conversation()

    assert store.restart_turn(conv.id) is True
    assert store.restart_turn(conv.id) is False


def test_restart_turn_moves_the_conversation_up():
    conv = make_conversation()
    before = store.get_conversation(conv.id).updated_at

    store.restart_turn(conv.id)

    assert store.get_conversation(conv.id).updated_at > before


@pytest.mark.parametrize(("types", "expected_index"), [([], None), (["user", "assistant"], 0), (["user", "user"], 1)])
def test_last_user_message_id(types, expected_index):
    conv = make_conversation()
    ids = [store.add_message(conv.id, t, "x").id for t in types]

    assert store.last_user_message_id(conv.id) == (0 if expected_index is None else ids[expected_index])
