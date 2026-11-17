"""Tests for web/agents/fake.py — the scripted engine of the browser suite."""

import asyncio
from datetime import datetime, timezone

import pytest

from web import config
from web.agents import get_agent
from web.agents.fake import FakeBackend, stopped
from web.environment import Environment
from web.llm import generate_text


def collect(message: str, backend: FakeBackend | None = None) -> list:
    async def run():
        return [e async for e in (backend or FakeBackend()).send_message("c1", message, [])]

    return asyncio.run(run())


@pytest.mark.parametrize(
    ("message", "types"),
    [
        ("[tools:2] go", ["tool_use", "tool_result", "tool_use", "tool_result", "assistant"]),
        ("[slow:2] go", ["assistant", "assistant", "assistant"]),
        ("[error] go", ["error"]),
        ("[limit] go", ["limit"]),
    ],
)
def test_markers_script_the_turn(mocker, message, types):
    mocker.patch("web.agents.fake.stopped", mocker.AsyncMock(return_value=False))
    assert [e.type for e in collect(message)] == types


def test_default_answer_echoes_the_message():
    assert [(e.type, e.content) for e in collect("bonjour")] == [("assistant", "Réponse factice : bonjour")]


def test_limit_resets_in_the_future():
    (event,) = collect("[limit]")
    assert datetime.fromisoformat(event.raw["reset"]) > datetime.now(timezone.utc)


def test_a_stop_during_slow_chunks_ends_the_turn(mocker):
    mocker.patch("web.agents.fake.stopped", mocker.AsyncMock(side_effect=[False, True]))
    assert [e.content for e in collect("[slow:3] go")] == ["Morceau 1."]


@pytest.mark.parametrize(("is_set", "result"), [(True, True), (False, False)])
def test_stopped_reports_whether_the_turn_was_stopped(is_set, result):
    async def run():
        stop = asyncio.Event()
        if is_set:
            stop.set()
        return await stopped(stop, 0.01)

    assert asyncio.run(run()) is result


def test_hang_runs_until_cancelled():
    backend = FakeBackend()

    async def run():
        events = []

        async def consume():
            async for event in backend.send_message("c1", "[hang]", []):
                events.append(event)

        turn = asyncio.create_task(consume())
        async with asyncio.timeout(1):
            while not backend.is_running("c1"):
                await asyncio.sleep(0)
        assert await backend.cancel("c1")
        await asyncio.wait_for(turn, 1)
        return events, backend.is_running("c1")

    assert asyncio.run(run()) == ([], False)


def test_cancel_without_a_turn_reports_nothing_to_stop():
    assert asyncio.run(FakeBackend().cancel("absent")) is False


def test_fake_engine_is_allowed_locally(mocker):
    mocker.patch.object(config, "ENV", Environment.DEV)
    assert isinstance(get_agent("fake"), FakeBackend)


@pytest.mark.parametrize("env", [Environment.REVIEW, Environment.STAGING, Environment.PROD])
def test_fake_engine_is_refused_on_servers(mocker, env):
    mocker.patch.object(config, "ENV", env)
    with pytest.raises(ValueError, match="fake"):
        get_agent("fake")


def test_short_prompts_get_a_fixed_answer_on_the_fake_engine(mocker):
    mocker.patch.object(config, "LLM_BACKEND", "fake")
    mocker.patch("web.llm.backend_is_limited", return_value=False)
    assert generate_text("Titre ?") == "Conversation factice"
