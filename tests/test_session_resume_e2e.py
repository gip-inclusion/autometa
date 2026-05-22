"""End-to-end test: session resume with Redis task runner and parallel conversations."""

import asyncio
import json

import fakeredis.aioredis
import pytest

from web.agents.base import AgentMessage
from web.runner import TaskRunner


def make_session_store():
    return {}


def make_fake_session_sync(store, tmp_path):
    def get_session_dir():
        return tmp_path

    def get_session_path(session_id):
        return tmp_path / f"{session_id}.jsonl"

    def download_session(session_id):
        key = f"{session_id}.jsonl"
        if key not in store:
            return False
        path = tmp_path / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(store[key])
        return True

    def upload_session(session_id):
        path = tmp_path / f"{session_id}.jsonl"
        if not path.exists():
            return False
        store[f"{session_id}.jsonl"] = path.read_bytes()
        return True

    return {
        "get_session_dir": get_session_dir,
        "get_session_path": get_session_path,
        "download_session": download_session,
        "upload_session": upload_session,
    }


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def session_store():
    return make_session_store()


@pytest.fixture
def runner_with_sessions(mocker, fake_redis, tmp_path, session_store):
    sync_funcs = make_fake_session_sync(session_store, tmp_path)

    mocker.patch("web.runner.get_redis", return_value=fake_redis)
    mocker.patch("web.runner.config.MAX_CONCURRENT_AGENTS", 4)

    mock_sync = mocker.patch("web.runner.session_sync")
    mock_sync.download_session = mocker.MagicMock(side_effect=sync_funcs["download_session"])

    mock_cli_sync = mocker.patch("web.agents.cli.session_sync")
    mock_cli_sync.upload_session = mocker.MagicMock(side_effect=sync_funcs["upload_session"])
    mock_cli_sync.get_session_path = mocker.MagicMock(side_effect=sync_funcs["get_session_path"])

    calls = []

    async def mock_send_message(conversation_id, message, history, session_id=None, user_email=None):
        calls.append({
            "conversation_id": conversation_id,
            "message": message,
            "history": history,
            "session_id": session_id,
        })

        if session_id:
            session_file = sync_funcs["get_session_path"](session_id)
            session_file.parent.mkdir(parents=True, exist_ok=True)
            with open(session_file, "a") as f:
                f.write(json.dumps({"message": message}) + "\n")
            sync_funcs["upload_session"](session_id)

        yield AgentMessage(type="assistant", content=f"Reply to: {message}")

    mock_backend = mocker.MagicMock()
    mock_backend.send_message = mock_send_message
    mock_backend.cancel = mocker.AsyncMock()
    mocker.patch("web.runner.get_agent", return_value=mock_backend)

    mock_store = mocker.patch("web.runner.store")
    mock_msg = mocker.MagicMock()
    mock_msg.id = 1
    mock_store.add_message.return_value = mock_msg
    mock_conv = mocker.MagicMock()
    mock_conv.needs_response = True
    mock_store.get_conversation.return_value = mock_conv

    runner = TaskRunner()
    runner._calls = calls
    return runner


async def _run_consumer_cycle(runner, fake_redis, wait=0.5):
    consumer = asyncio.create_task(runner._consumer_loop())
    await asyncio.sleep(wait)
    consumer.cancel()
    for t in list(runner._running.values()):
        t.cancel()
    await asyncio.gather(consumer, *runner._running.values(), return_exceptions=True)


def test_single_conversation_two_turns(runner_with_sessions, fake_redis, session_store):
    runner = runner_with_sessions
    session_id = "sess-conv1"

    async def _run():
        await runner.submit("conv1", "What is IAE?", [], session_id=session_id)
        await _run_consumer_cycle(runner, fake_redis)

        assert f"{session_id}.jsonl" in session_store

        await runner.submit("conv1", "Tell me more", [], session_id=session_id)
        await _run_consumer_cycle(runner, fake_redis)

        assert len(runner._calls) == 2
        assert runner._calls[0]["session_id"] == session_id
        assert runner._calls[0]["message"] == "What is IAE?"
        assert runner._calls[1]["session_id"] == session_id
        assert runner._calls[1]["message"] == "Tell me more"

        session_data = session_store[f"{session_id}.jsonl"].decode()
        lines = [line for line in session_data.strip().split("\n") if line]
        assert len(lines) == 2

    asyncio.run(_run())


def test_two_parallel_conversations(runner_with_sessions, fake_redis, session_store):
    runner = runner_with_sessions

    async def _run():
        await runner.submit("conv-a", "Question A", [], session_id="sess-a")
        await runner.submit("conv-b", "Question B", [], session_id="sess-b")
        await _run_consumer_cycle(runner, fake_redis, wait=1.0)

        conv_ids = {c["conversation_id"] for c in runner._calls}
        assert conv_ids == {"conv-a", "conv-b"}

        assert "sess-a.jsonl" in session_store
        assert "sess-b.jsonl" in session_store

        assert b"Question A" in session_store["sess-a.jsonl"]
        assert b"Question B" in session_store["sess-b.jsonl"]
        assert b"Question B" not in session_store["sess-a.jsonl"]
        assert b"Question A" not in session_store["sess-b.jsonl"]

    asyncio.run(_run())


def test_session_download_called_before_agent(runner_with_sessions, fake_redis, session_store, mocker):
    runner = runner_with_sessions
    session_id = "sess-existing"
    session_store[f"{session_id}.jsonl"] = b'{"type":"existing"}\n'

    download_spy = mocker.patch("web.runner.session_sync").download_session

    async def _run():
        await runner.submit("conv1", "Follow-up", [], session_id=session_id)
        await _run_consumer_cycle(runner, fake_redis)
        download_spy.assert_called_once_with(session_id)

    asyncio.run(_run())


def test_no_session_id_skips_sync(runner_with_sessions, fake_redis, mocker):
    runner = runner_with_sessions
    download_spy = mocker.patch("web.runner.session_sync").download_session

    async def _run():
        await runner.submit("conv1", "No session", [])
        await _run_consumer_cycle(runner, fake_redis)
        download_spy.assert_not_called()

    asyncio.run(_run())
