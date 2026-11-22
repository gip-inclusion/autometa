"""Tests de la file des messages en attente dans web/stores/conversations.py."""

import json
import threading
import uuid

import pytest

from web.database import page_entries, store

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

    taken = store.ack_returned(conv.id, [first, waiting])

    assert [e["content"] for e in taken] == ["q1"]
    assert [e["id"] for e in store.pending_messages(conv.id)] == [second, waiting]


def test_returned_messages_go_to_one_acknowledgement_when_two_race():
    for _ in range(20):
        conv = make_conversation()
        store.queue_message(conv.id, "q1")
        store.end_turn(conv.id, flush=False)
        ids = [e["id"] for e in store.pending_messages(conv.id)]
        barrier = threading.Barrier(2)
        taken = []

        def ack(conv_id=conv.id, ids=ids, barrier=barrier, taken=taken):
            barrier.wait()
            taken.append(store.ack_returned(conv_id, ids))

        threads = [threading.Thread(target=ack) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sorted(len(t) for t in taken) == [0, 1]


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


def kinds(conv_id: str) -> list[tuple[str, str]]:
    return [(m.type, m.content) for m in store.get_conversation(conv_id).messages]


def thread(*texts: str, through: str = "1700000000.0", note: str = "") -> str:
    messages = [{"author": "Louis", "at": "22/11 14:05", "text": text} for text in texts]
    return json.dumps({"messages": messages, "note": note, "left_out": "", "through": through}, ensure_ascii=False)


def test_queued_slack_mentions_leave_with_their_threads_as_one_message_and_the_agent_reads_thread_and_request():
    conv = make_conversation()
    store.queue_message(conv.id, "q1", slack=thread("a", through="1.0"))
    store.queue_message(conv.id, "Louis : q2", slack=thread("b", "c", through="2.0", note="Canal privé."))

    sent = store.end_turn(conv.id, flush=True)

    assert [m.content for m in sent][0] == "q1"
    assert sent[1].content.startswith("Contexte :") and "\nLouis : q2\n" in sent[1].content
    assert [line for line in sent[1].content.split("\n") if line.startswith("> ")] == [
        "> Louis, 22/11 14:05 : a",
        "> Louis, 22/11 14:05 : b",
        "> Louis, 22/11 14:05 : c",
    ]
    stored = kinds(conv.id)[1:]
    assert [kind for kind, _ in stored] == ["user", "user", "slack_context"]
    assert stored[1] == ("user", "Louis : q2")
    kept = json.loads(stored[2][1])
    assert [m["text"] for m in kept["messages"]] == ["a", "b", "c"]
    assert (kept["through"], kept["note"]) == ("2.0", "Canal privé.")
    assert store.pending_messages(conv.id) == []


def test_a_message_queued_from_the_page_after_a_mention_is_read_as_typed_and_the_thread_is_kept():
    conv = make_conversation()
    store.queue_message(conv.id, "q1", slack=thread("a"))
    store.queue_message(conv.id, "q2")

    sent = store.end_turn(conv.id, flush=True)

    assert [m.content for m in sent] == ["q1", "q2"]
    assert json.loads(kinds(conv.id)[-1][1])["messages"][0]["text"] == "a"


def test_a_queued_mention_without_thread_still_keeps_how_far_the_thread_was_read():
    conv = make_conversation()
    store.queue_message(conv.id, "q1", slack=thread(through="5.0"))

    sent = store.end_turn(conv.id, flush=True)

    assert sent[0].content == "q1"
    assert store.slack_contexts(conv.id) == [thread(through="5.0")]


def test_the_page_neither_sees_takes_nor_gets_back_a_mention_waiting_from_slack():
    conv = make_conversation()
    store.queue_message(conv.id, "de la page")
    store.queue_message(conv.id, "de Slack", slack=thread("a"))
    mention = next(e["id"] for e in store.pending_messages(conv.id) if e.get("slack"))

    assert [e["content"] for e in page_entries(store.pending_messages(conv.id), "waiting")] == ["de la page"]
    assert store.take_queued(conv.id, mention) is None
    store.end_turn(conv.id, flush=False)

    pending = store.pending_messages(conv.id)
    assert [e["content"] for e in page_entries(pending, "returned")] == ["de la page"]
    assert [e["content"] for e in store.ack_returned(conv.id, [e["id"] for e in pending])] == ["de la page"]
    assert [e["content"] for e in store.pending_messages(conv.id)] == ["de Slack"]
    assert store.take_queued(conv.id, mention, slack=True) == "de Slack"
    assert store.pending_messages(conv.id) == []


def test_a_conversation_opened_from_slack_keeps_its_thread_and_is_found_by_it():
    conv_id, created = store.slack_thread_conversation("C0QUEUE", "1700000000.000100", ALICE)
    store.update_conversation(conv_id, slack_message_ts="1700000001.000200")

    read = store.get_conversation(conv_id)

    assert created is True
    assert (read.origin, read.slack_channel, read.slack_thread_ts) == ("slack", "C0QUEUE", "1700000000.000100")
    assert store.slack_conversation("C0QUEUE", "1700000000.000100") == conv_id
    assert store.slack_conversation("C0QUEUE", "1700000000.999999") is None
    assert conv_id in store.slack_live_conversations()
    assert store.get_conversation(make_conversation().id).origin == "web"


def test_a_slack_thread_never_has_two_conversations_even_asked_for_at_once():
    thread_ts = f"{uuid.uuid4().int % 10**10}.000100"
    barrier, found = threading.Barrier(4), []

    def ask():
        barrier.wait()
        found.append(store.slack_thread_conversation("C0RACE", thread_ts, ALICE))

    threads = [threading.Thread(target=ask) for _ in range(4)]
    for one in threads:
        one.start()
    for one in threads:
        one.join()

    assert len({conv_id for conv_id, _ in found}) == 1
    assert sorted(created for _, created in found) == [False, False, False, True]


def test_direct_conversations_without_thread_are_as_many_as_asked():
    first = store.create_conversation(user_id=ALICE, slack_thread=("D0DIRECT", None))
    second = store.create_conversation(user_id=ALICE, slack_thread=("D0DIRECT", None))

    assert first.id != second.id
    assert store.get_conversation(first.id).origin == "slack"


def test_two_requests_at_once_on_an_idle_conversation_give_one_turn():
    conv = make_conversation(running=False)
    barrier, started = threading.Barrier(2), []

    def ask(text):
        barrier.wait()
        started.append(store.start_turn(conv.id, text))

    threads = [threading.Thread(target=ask, args=(text,)) for text in ("une", "deux")]
    for one in threads:
        one.start()
    for one in threads:
        one.join()

    assert sum(turn is not None for turn in started) == 1
    assert len([kind for kind, _ in kinds(conv.id) if kind == "user"]) == 2


def test_the_living_message_is_forgotten_only_if_it_is_still_the_one_completed():
    conv_id, _ = store.slack_thread_conversation("C0QUEUE", f"{uuid.uuid4().int % 10**10}.000100", ALICE)
    store.update_conversation(conv_id, slack_message_ts="2.0")

    assert store.clear_slack_message(conv_id, "1.0") is False
    assert store.get_conversation(conv_id).slack_message_ts == "2.0"
    assert store.clear_slack_message(conv_id, "2.0") is True
    assert store.get_conversation(conv_id).slack_message_ts is None
    assert conv_id not in store.slack_live_conversations()


def test_the_threads_kept_by_a_conversation_are_read_in_order_and_from_a_message_on():
    conv = make_conversation(running=False)
    store.add_message(conv.id, "slack_context", "un")
    later = store.add_message(conv.id, "user", "q")
    store.add_message(conv.id, "slack_context", "deux")

    assert store.slack_contexts(conv.id) == ["un", "deux"]
    assert store.slack_contexts(conv.id, later.id) == ["deux"]


def test_a_person_owns_conversations_whatever_the_case_of_their_address():
    make_conversation()

    assert store.owns_conversations("Alice@Example.com") is True
    assert store.owns_conversations("personne@example.com") is False
