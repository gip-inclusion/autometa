"""Tests for SSE streaming and event storage."""

import asyncio
import importlib
import json
import re
import threading
import time

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


@pytest.fixture(scope="module")
def app():
    """Module-scoped FastAPI app with fresh database."""
    from web import database

    importlib.reload(database)

    from web.app import app as fastapi_app

    yield fastapi_app

    from sqlalchemy import text

    from web.db import get_db

    with get_db() as session:
        session.execute(
            text("""
            TRUNCATE TABLE messages, conversation_tags, report_tags,
                uploaded_files, cron_runs, pinned_items,
                reports, conversations, tags
                CASCADE;
        """)
        )


@pytest.fixture
def client(app):
    from starlette.testclient import TestClient

    return TestClient(app)


@pytest.fixture
def conversation(app):
    from web.database import store

    conv = store.create_conversation(user_id="test@example.com")
    store.add_message(conv.id, "user", "Hello agent")
    store.update_conversation(conv.id, needs_response=True)
    return conv


@pytest.fixture
def responded_conversation(app):
    from web.database import store

    conv = store.create_conversation(user_id="test@example.com")
    store.add_message(conv.id, "user", "Hello agent")
    store.add_message(conv.id, "assistant", "Hello! How can I help?")
    return conv


@pytest.fixture(autouse=True)
def _render_at_each_signal(monkeypatch):
    monkeypatch.setattr("web.routes.conversations.config.SSE_RENDER_INTERVAL", 0)


def _texts(html: str) -> list[str]:
    """The text of each block of a blocks event, or of each pill."""
    parts = re.split(r'<div class="(?:event-block|action-pill)[ "][^>]*>', html)[1:]
    return [" ".join(re.sub(r"<[^>]+>", " ", part).split()) for part in parts]


def _blocks(response) -> list[dict]:
    return [e["data"] for e in _parse_sse_events(response.content) if e["event"] == "blocks"]


def _parse_sse_events(response_data: bytes) -> list[dict]:
    events = []
    current_event = None
    current_data = None

    for line in response_data.decode("utf-8").split("\n"):
        if line.startswith("event: "):
            current_event = line[7:]
        elif line.startswith("data: "):
            current_data = line[6:]
        elif line == "" and current_event is not None:
            entry = {"event": current_event}
            if current_data:
                try:
                    entry["data"] = json.loads(current_data)
                except json.JSONDecodeError:
                    entry["data"] = current_data
            events.append(entry)
            current_event = None
            current_data = None

    return events


def _simulate_pm(conv_id, messages, delay=0.1):
    """Simulate the task runner writing messages then signaling done via Redis."""

    def _run():
        time.sleep(delay)
        import redis as sync_redis

        from web import config
        from web.database import store

        r = sync_redis.from_url(config.REDIS_URL, decode_responses=True)
        for msg_type, content in messages:
            store.add_message(conv_id, msg_type, content if isinstance(content, str) else json.dumps(content))
            r.publish(f"autometa:conv:{conv_id}", "update")
        store.update_conversation(conv_id, needs_response=False)
        question_id = store.last_user_message_id(conv_id)
        r.set(f"autometa:done:{conv_id}", str(question_id), ex=600)
        r.publish(f"autometa:conv:{conv_id}", f"done:{question_id}")
        r.close()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


@pytest.mark.parametrize(("after", "expected"), [(0, ["Hello agent", "Hello! How can I help?"]), (None, [])])
def test_the_stream_of_a_finished_conversation_brings_what_the_page_lacks_then_done(
    app, client, responded_conversation, after, expected
):
    from web.database import store

    last = store.get_messages_since(responded_conversation.id, 0)[-1].id
    response = client.get(
        f"/api/conversations/{responded_conversation.id}/stream?after={last if after is None else after}",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    events = [e for e in _parse_sse_events(response.content) if e["event"] != "queue"]

    assert [e["event"] for e in events] == ["blocks", "done"]
    assert _texts(events[0]["data"]["blocks"]) == expected
    assert (events[0]["data"]["settled"], events[0]["data"]["running"]) == (last, False)


def test_sse_format_stream_ends_with_done(app, client, conversation):
    """SSE stream must end with a done event."""
    t = _simulate_pm(conversation.id, [("assistant", "Hello")])
    response = client.get(
        f"/api/conversations/{conversation.id}/stream",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    t.join()
    events = _parse_sse_events(response.content)
    assert events[-1]["event"] == "done"


def test_an_answer_arrives_rendered_and_whole_once_its_turn_ends(app, client, conversation):
    t = _simulate_pm(conversation.id, [("assistant", "## Ma réponse")])
    response = client.get(
        f"/api/conversations/{conversation.id}/stream",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    t.join()
    last = _blocks(response)[-1]

    assert 'class="event-block event-assistant event-final-answer"' in last["blocks"]
    assert "data-partial" not in last["blocks"] and "<h2 data-anchor=" in last["blocks"]
    assert (last["running"], last["status"]) == (False, "")


def test_tool_calls_arrive_as_pills_referred_to_under_the_answer(app, client, conversation):
    messages = [
        ("tool_use", json.dumps({"tool": "Read", "input": {"file_path": "/tmp/x.md"}, "category": "Read: other"})),
        ("tool_result", json.dumps({"output": "data"})),
        ("assistant", "Done"),
    ]
    t = _simulate_pm(conversation.id, messages)
    response = client.get(
        f"/api/conversations/{conversation.id}/stream",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    t.join()
    sent = _blocks(response)

    assert [_texts(event["pills"]) for event in sent if event["pills"]] == [["x.md FILE_PATH /tmp/x.md"]]
    assert (
        '<div class="action-footnotes"><span class="action-footnote" data-action-index="1" title="x.md">'
        in sent[-1]["blocks"]
    )
    assert "Outil · Read" in [event["status"] for event in sent]


def _sync_redis():
    import redis as sync_redis

    from web import config

    return sync_redis.from_url(config.REDIS_URL, decode_responses=True)


def test_race_condition_pm_writes_before_sse_connect(app, client):
    from web.database import store

    conv = store.create_conversation(user_id="test@example.com")
    user_msg = store.add_message(conv.id, "user", "Hello")
    store.update_conversation(conv.id, needs_response=True)

    store.add_message(conv.id, "assistant", "Fast response")
    r = _sync_redis()
    r.publish(f"autometa:conv:{conv.id}", "update")

    t = _simulate_pm(conv.id, [("assistant", "Second part")])
    response = client.get(
        f"/api/conversations/{conv.id}/stream?after={user_msg.id}",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    t.join()
    r.close()
    first = _blocks(response)[0]

    assert _texts(first["blocks"]) == ["Fast response"]
    assert "data-partial" in first["blocks"]


def test_race_condition_pm_finishes_before_sse_connect(app, client):
    from web.database import store

    conv = store.create_conversation(user_id="test@example.com")
    user_msg = store.add_message(conv.id, "user", "Hello")
    store.update_conversation(conv.id, needs_response=True)

    store.add_message(conv.id, "assistant", "Instant answer")
    r = _sync_redis()
    r.publish(f"autometa:conv:{conv.id}", "update")
    store.update_conversation(conv.id, needs_response=False)
    r.set(f"autometa:done:{conv.id}", str(user_msg.id), ex=600)
    r.publish(f"autometa:conv:{conv.id}", f"done:{user_msg.id}")
    r.close()

    response = client.get(
        f"/api/conversations/{conv.id}/stream?after={user_msg.id}",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    events = _parse_sse_events(response.content)

    assert [_texts(event["blocks"]) for event in _blocks(response)] == [["Instant answer"]]
    assert "event-final-answer" in _blocks(response)[0]["blocks"], "PM finished before SSE connect: answer not whole"
    assert events[-1]["event"] == "done"


def test_resend_after_cancel_does_not_lose_answer(app, client):
    """Resending after a cancel clears the stale done key so the answer streams."""
    from web.database import store

    conv = store.create_conversation(user_id="test@example.com")
    store.add_message(conv.id, "user", "Q1")  # not the first message -> no title/tag LLM calls

    r = _sync_redis()
    r.set("autometa:done:" + conv.id, "1", ex=600)  # leftover marker from a previous cancel

    resp = client.post(
        f"/api/conversations/{conv.id}/messages",
        json={"content": "ma nouvelle question"},
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert resp.status_code == 200
    after_id = resp.json()["after_id"]
    assert not r.exists("autometa:done:" + conv.id), "submit did not clear the stale done key"

    t = _simulate_pm(conv.id, [("assistant", "Real answer")])
    response = client.get(
        f"/api/conversations/{conv.id}/stream?after={after_id}",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    t.join()
    r.close()
    assert _texts(_blocks(response)[-1]["blocks"]) == ["Real answer"], "new run's answer was lost"
    assert "data-partial" not in _blocks(response)[-1]["blocks"]


def test_needs_response_true_streams_messages(app, client):
    """Conversation with needs_response=True streams PM messages."""
    from web.database import store

    conv = store.create_conversation(user_id="test@example.com")
    store.add_message(conv.id, "user", "Hello")
    store.update_conversation(conv.id, needs_response=True)

    t = _simulate_pm(conv.id, [("assistant", "Response")])
    response = client.get(
        f"/api/conversations/{conv.id}/stream",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    t.join()

    assert _texts(_blocks(response)[-1]["blocks"]) == ["Response"]


def test_needs_response_update_conversation_clears_needs_response(app):
    """update_conversation(needs_response=False) works correctly."""
    from web.database import store

    conv = store.create_conversation(user_id="test@example.com")
    store.add_message(conv.id, "user", "Hello")
    store.update_conversation(conv.id, needs_response=True)

    updated = store.get_conversation(conv.id)
    assert updated.needs_response is True

    store.update_conversation(conv.id, needs_response=False)
    updated = store.get_conversation(conv.id)
    assert updated.needs_response is False


def test_append_mode_ollama_append_concatenates_without_newline(app):
    """Ollama streaming: append=True -> "".join (no newlines)."""
    from web.agents.base import AgentMessage
    from web.database import store

    conv = store.create_conversation(user_id="test@example.com")
    store.add_message(conv.id, "user", "Hello")

    assistant_text_parts = []
    assistant_msg_id = None

    for event in [
        AgentMessage(type="assistant", content="Hello ", raw={"append": True}),
        AgentMessage(type="assistant", content="world!", raw={"append": True}),
    ]:
        assistant_text_parts.append(str(event.content))
        append_mode = bool(getattr(event, "raw", {}).get("append"))
        full_text = "".join(assistant_text_parts) if append_mode else "\n".join(assistant_text_parts)
        if assistant_msg_id is None:
            msg = store.add_message(conv.id, "assistant", full_text)
            assistant_msg_id = msg.id
        else:
            store.update_message(assistant_msg_id, full_text)

    conv = store.get_conversation(conv.id)
    assistant_msgs = [m for m in conv.messages if m.type == "assistant"]
    assert len(assistant_msgs) == 1
    assert assistant_msgs[0].content == "Hello world!"


def test_append_mode_cli_joins_with_newlines(app):
    """CLI backend: no append flag -> "\\n".join."""
    from web.agents.base import AgentMessage
    from web.database import store

    conv = store.create_conversation(user_id="test@example.com")
    store.add_message(conv.id, "user", "Hello")

    assistant_text_parts = []
    assistant_msg_id = None

    for event in [
        AgentMessage(type="assistant", content="First paragraph"),
        AgentMessage(type="assistant", content="Second paragraph"),
    ]:
        assistant_text_parts.append(str(event.content))
        append_mode = bool(getattr(event, "raw", {}).get("append"))
        full_text = "".join(assistant_text_parts) if append_mode else "\n".join(assistant_text_parts)
        if assistant_msg_id is None:
            msg = store.add_message(conv.id, "assistant", full_text)
            assistant_msg_id = msg.id
        else:
            store.update_message(assistant_msg_id, full_text)

    conv = store.get_conversation(conv.id)
    assistant_msgs = [m for m in conv.messages if m.type == "assistant"]
    assert len(assistant_msgs) == 1
    assert assistant_msgs[0].content == "First paragraph\nSecond paragraph"


def test_assistant_text_reset_tool_use_creates_separate_assistant_messages(app):
    from web.agents.base import AgentMessage
    from web.database import store

    conv = store.create_conversation(user_id="test@example.com")
    store.add_message(conv.id, "user", "Hello")

    assistant_text_parts = []
    assistant_msg_id = None

    events = [
        AgentMessage(type="assistant", content="Let me check"),
        AgentMessage(type="tool_use", content={"tool": "Read", "input": {}}, raw={}),
        AgentMessage(type="tool_result", content={"output": "data"}, raw={}),
        AgentMessage(type="assistant", content="Here is what I found"),
    ]

    for event in events:
        if event.type == "assistant":
            assistant_text_parts.append(str(event.content))
            append_mode = bool(getattr(event, "raw", {}).get("append"))
            full_text = "".join(assistant_text_parts) if append_mode else "\n".join(assistant_text_parts)
            if assistant_msg_id is None:
                msg = store.add_message(conv.id, "assistant", full_text)
                assistant_msg_id = msg.id
            else:
                store.update_message(assistant_msg_id, full_text)

        elif event.type in ("tool_use", "tool_result"):
            if event.type == "tool_use":
                assistant_msg_id = None
                assistant_text_parts = []
            store.add_message(conv.id, event.type, json.dumps(event.content))

    conv = store.get_conversation(conv.id)
    assistant_msgs = [m for m in conv.messages if m.type == "assistant"]
    assert len(assistant_msgs) == 2
    assert assistant_msgs[0].content == "Let me check"
    assert assistant_msgs[1].content == "Here is what I found"


def test_client_disconnect_agent_survives_client_disconnect(app, conversation):
    """Agent must keep running after client disconnects mid-stream."""
    from web.database import store
    from web.routes.conversations import stream_conversation

    store.add_message(conversation.id, "assistant", "Working on it...")

    async def _run():
        response = await stream_conversation(
            conv_id=conversation.id,
            after=0,
            user_email="test@example.com",
        )
        gen = response.body_iterator
        chunks_read = 0
        async for chunk in gen:
            chunks_read += 1
            if chunks_read >= 2:
                break
        await gen.aclose()
        await asyncio.sleep(0.1)

    asyncio.run(_run())

    conv = store.get_conversation(conversation.id, include_messages=False)
    assert conv.needs_response, "Agent was stopped by client disconnect!"


def test_a_done_for_an_older_question_does_not_close_the_stream(app, client):
    from web.database import store

    conv = store.create_conversation(user_id="test@example.com")
    older = store.add_message(conv.id, "user", "Première question")
    store.add_message(conv.id, "user", "Seconde question")
    store.update_conversation(conv.id, needs_response=True)

    def stale_then_real():
        r = _sync_redis()
        while not r.pubsub_numsub(f"autometa:conv:{conv.id}")[0][1]:
            time.sleep(0.01)
        r.publish(f"autometa:conv:{conv.id}", f"done:{older.id}")
        time.sleep(0.2)
        store.add_message(conv.id, "assistant", "Réponse à la seconde")
        r.publish(f"autometa:conv:{conv.id}", "update")
        store.update_conversation(conv.id, needs_response=False)
        newest = store.last_user_message_id(conv.id)
        r.set(f"autometa:done:{conv.id}", str(newest), ex=600)
        r.publish(f"autometa:conv:{conv.id}", f"done:{newest}")
        r.close()

    t = threading.Thread(target=stale_then_real, daemon=True)
    t.start()
    response = client.get(f"/api/conversations/{conv.id}/stream", headers={"X-Forwarded-Email": "test@example.com"})
    t.join()
    events = _parse_sse_events(response.content)

    kinds = [e["event"] for e in events if e["event"] not in ("heartbeat", "queue")]
    assert kinds[-1] == "done" and set(kinds[:-1]) == {"blocks"}
    assert _texts(_blocks(response)[-1]["blocks"]) == ["Réponse à la seconde"]
    assert events[-1]["data"]["question_id"] == store.last_user_message_id(conv.id)


def test_a_block_carries_the_ids_of_its_messages(app, client, conversation):
    from web.database import store

    t = _simulate_pm(conversation.id, [("assistant", "Bonjour"), ("assistant", " à vous")])
    response = client.get(
        f"/api/conversations/{conversation.id}/stream", headers={"X-Forwarded-Email": "test@example.com"}
    )
    t.join()
    question, first, second = (row.id for row in store.get_messages_since(conversation.id, 0))

    assert f'data-msg-id="{first} {second}"' in _blocks(response)[-1]["blocks"]
    assert _blocks(response)[-1]["settled"] == second
    assert {event["settled"] for event in _blocks(response)[:-1]} == {question - 1}


def _grow(conv_id, texts, pause):
    """Le runner qui écrit une réponse, l'allonge sur place à chaque texte, puis clôt le tour."""
    from web.database import store

    def _run():
        r = _sync_redis()
        while not r.pubsub_numsub(f"autometa:conv:{conv_id}")[0][1]:
            time.sleep(0.01)
        row = store.add_message(conv_id, "assistant", texts[0])
        r.publish(f"autometa:conv:{conv_id}", "update")
        for text in texts[1:]:
            time.sleep(pause)
            store.update_message(row.id, text)
            r.publish(f"autometa:conv:{conv_id}", "update")
        time.sleep(pause)
        store.update_conversation(conv_id, needs_response=False)
        question_id = store.last_user_message_id(conv_id)
        r.set(f"autometa:done:{conv_id}", str(question_id), ex=600)
        r.publish(f"autometa:conv:{conv_id}", f"done:{question_id}")
        r.close()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


def test_an_answer_rewritten_in_place_is_sent_again_partial_until_its_turn_ends(app, client, conversation):
    t = _grow(conversation.id, ["Début", "Début, puis la suite"], 0.2)
    response = client.get(
        f"/api/conversations/{conversation.id}/stream", headers={"X-Forwarded-Email": "test@example.com"}
    )
    t.join()
    answers = [event["blocks"] for event in _blocks(response)[1:]]

    assert [_texts(html) for html in answers] == [["Début"], ["Début, puis la suite"], ["Début, puis la suite"]]
    assert ["data-partial" in html for html in answers] == [True, True, False]
    assert len({re.search(r'data-msg-id="(\d+)"', html)[1] for html in answers}) == 1


def test_an_answer_growing_faster_than_the_interval_is_rendered_less_often_but_always_at_its_end(
    app, client, conversation, monkeypatch
):
    monkeypatch.setattr("web.routes.conversations.config.SSE_RENDER_INTERVAL", 0.3)
    texts = ["mot " * n for n in range(1, 31)]

    t = _grow(conversation.id, texts, 0.01)
    response = client.get(
        f"/api/conversations/{conversation.id}/stream", headers={"X-Forwarded-Email": "test@example.com"}
    )
    t.join()
    answers = [event["blocks"] for event in _blocks(response)[1:]]

    assert 2 <= len(answers) <= 5
    assert _texts(answers[-1]) == [texts[-1].strip()] and "data-partial" not in answers[-1]


def test_the_stream_rotation_sends_a_timeout_event(app, client, conversation, monkeypatch):
    monkeypatch.setattr("web.routes.conversations.config.SSE_MAX_SECONDS", 0.2)
    response = client.get(
        f"/api/conversations/{conversation.id}/stream", headers={"X-Forwarded-Email": "test@example.com"}
    )
    events = [e["event"] for e in _parse_sse_events(response.content) if e["event"] != "heartbeat"]

    assert events[-1] == "timeout"


def test_a_resumed_stream_sends_the_rows_it_missed_at_once(app, client, conversation, monkeypatch):
    from web.database import store

    monkeypatch.setattr("web.routes.conversations.config.SSE_MAX_SECONDS", 0.2)
    seen = store.last_user_message_id(conversation.id)
    store.add_message(conversation.id, "assistant", "Écrit pendant la coupure")
    response = client.get(
        f"/api/conversations/{conversation.id}/stream?after={seen}", headers={"X-Forwarded-Email": "test@example.com"}
    )
    events = [e for e in _parse_sse_events(response.content) if e["event"] not in ("heartbeat", "queue")]

    assert [e["event"] for e in events] == ["blocks", "timeout"]
    assert _texts(events[0]["data"]["blocks"]) == ["Écrit pendant la coupure"]


def test_a_turn_ending_just_before_the_stream_subscribes_closes_it_at_once(app, client, conversation, monkeypatch):
    from web.database import store
    from web.runner import runner

    subscribe = runner.subscribe

    async def end_turn_then_subscribe(conv_id):
        store.update_conversation(conv_id, needs_response=False)
        question_id = store.last_user_message_id(conv_id)
        r = _sync_redis()
        r.set(f"autometa:done:{conv_id}", str(question_id), ex=600)
        r.publish(f"autometa:conv:{conv_id}", f"done:{question_id}")
        r.close()
        return await subscribe(conv_id)

    monkeypatch.setattr(runner, "subscribe", end_turn_then_subscribe)
    started = time.monotonic()
    response = client.get(
        f"/api/conversations/{conversation.id}/stream", headers={"X-Forwarded-Email": "test@example.com"}
    )

    assert _parse_sse_events(response.content)[-1]["event"] == "done"
    assert time.monotonic() - started < 2


def _end_turn(conv_id, flush, delay=0.3):
    """Le runner qui clôt un tour : la file part dans un tour de plus, ou revient à la page."""

    def _run():
        time.sleep(delay)
        import redis as sync_redis

        from web import config
        from web.database import store

        r = sync_redis.from_url(config.REDIS_URL, decode_responses=True)
        if store.end_turn(conv_id, flush=flush):
            r.publish(f"autometa:conv:{conv_id}", "queue")
            time.sleep(0.2)
            store.add_message(conv_id, "assistant", "Réponse groupée")
            store.end_turn(conv_id, flush=False)
        question_id = store.last_user_message_id(conv_id)
        r.set(f"autometa:done:{conv_id}", str(question_id), ex=600)
        r.publish(f"autometa:conv:{conv_id}", f"done:{question_id}")
        r.close()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


def _queued_stream(client, conv_id, *queued, flush, email="test@example.com"):
    """Le flux d'un tour pendant lequel des messages attendaient, résumé en (événement, contenu)."""
    from web.database import store

    for text in queued:
        store.queue_message(conv_id, text)
    thread = _end_turn(conv_id, flush=flush)
    response = client.get(f"/api/conversations/{conv_id}/stream", headers={"X-Forwarded-Email": email})
    thread.join()
    summary = {
        "queue": lambda data: [e["content"] for e in data["queue"]],
        "returned": lambda data: [e["content"] for e in data["returned"]],
        "done": lambda data: None,
        "blocks": lambda data: _texts(data["blocks"]),
    }
    return [
        (e["event"], summary[e["event"]](e["data"]))
        for e in _parse_sse_events(response.content)
        if e["event"] != "heartbeat"
    ]


def test_a_sent_queue_arrives_as_questions_in_the_same_stream(app, client, conversation):
    events = _queued_stream(client, conversation.id, "q1", "q2", flush=True)

    assert events == [
        ("blocks", ["Hello agent"]),
        ("queue", ["q1", "q2"]),
        ("blocks", ["q1", "q2"]),
        ("queue", []),
        ("blocks", ["Réponse groupée"]),
        ("done", None),
    ]


def test_a_returned_queue_arrives_before_the_end_of_the_turn(app, client, conversation):
    events = _queued_stream(client, conversation.id, "q1", flush=False)

    assert events == [
        ("blocks", ["Hello agent"]),
        ("queue", ["q1"]),
        ("queue", []),
        ("returned", ["q1"]),
        ("done", None),
    ]


def test_a_reader_never_sees_the_queue(app, client, conversation):
    events = _queued_stream(client, conversation.id, "q1", flush=False, email="reader@example.com")

    assert events == [("blocks", ["Hello agent"]), ("done", None)]


def test_a_waiting_message_comes_with_the_html_of_its_bubble(app, client, conversation, monkeypatch):
    from web.database import store

    monkeypatch.setattr("web.routes.conversations.config.SSE_MAX_SECONDS", 0.2)
    store.queue_message(conversation.id, "**plus tard** <b>")
    response = client.get(
        f"/api/conversations/{conversation.id}/stream", headers={"X-Forwarded-Email": "test@example.com"}
    )
    waiting = next(e["data"]["queue"] for e in _parse_sse_events(response.content) if e["event"] == "queue")

    assert [(entry["content"], entry["html"]) for entry in waiting] == [
        ("**plus tard** <b>", '<div class="user-text"><p><strong>plus tard</strong> &lt;b&gt;</p>\n</div>')
    ]
