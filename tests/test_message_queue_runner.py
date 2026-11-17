"""Parcours de la file d'attente avec le vrai runner, la vraie base et le moteur factice."""

import asyncio

import fakeredis.aioredis
import pytest

from web.agents.fake import FakeBackend
from web.database import store
from web.runner import TaskRunner

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

ALICE = "alice@example.com"


@pytest.fixture
def redis(mocker):
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    mocker.patch("web.runner.get_redis", return_value=fake)
    return fake


@pytest.fixture
def sends(mocker, redis, tmp_path):
    """Les appels au moteur factice, sur une session que le moteur sait reprendre."""
    mocker.patch("web.runner.config.AGENT_FALLBACK_BACKEND", "")
    sync = mocker.patch("web.runner.session_sync")
    # Why: une session reprise ne reçoit en rattrapage que ce qui suit la dernière question vue.
    sync.get_session_path.return_value = tmp_path
    backend = FakeBackend()
    mocker.patch("web.runner.get_agent", return_value=backend)
    return mocker.spy(backend, "send_message")


def start(question: str, *queued: str) -> str:
    conv = store.create_conversation(user_id=ALICE)
    store.start_turn(conv.id, question)
    for text in queued:
        store.queue_message(conv.id, text)
    return conv.id


def returned(conv_id: str) -> list[str]:
    return [e["content"] for e in store.pending_messages(conv_id) if e["status"] == "returned"]


async def run_until_done(runner: TaskRunner, redis, conv_id: str, question: str) -> str:
    """Fait tourner le consommateur jusqu'au signal de fin de la conversation, et le rend."""
    await runner.submit(conv_id, question, [], ALICE)
    consumer = asyncio.create_task(runner._consumer_loop())
    async with asyncio.timeout(30):
        while not (done := await redis.get(f"autometa:done:{conv_id}")):
            await asyncio.sleep(0.02)
    consumer.cancel()
    await asyncio.gather(consumer, *runner._running.values(), return_exceptions=True)
    return done


def test_a_clean_end_sends_the_waiting_messages_in_one_more_turn(sends, redis):
    conv_id = start("q0", "q1", "q2")

    done = asyncio.run(run_until_done(TaskRunner(), redis, conv_id, "q0"))

    messages = store.get_conversation(conv_id).messages
    assert [(m.type, m.content) for m in messages] == [
        ("user", "q0"),
        ("assistant", "Réponse factice : q0"),
        ("user", "q1"),
        ("user", "q2"),
        ("assistant", "Réponse factice : q2"),
    ]
    assert [c.kwargs["message"] for c in sends.call_args_list] == ["q0", "q2"]
    assert sends.call_args_list[1].kwargs["history"] == [{"role": "user", "content": "q1"}]
    assert sends.call_args_list[1].kwargs["user_email"] == ALICE
    assert done == str(messages[3].id)
    assert store.pending_messages(conv_id) == []


@pytest.mark.parametrize("question", ["[error] q0", "[limit] q0", "[tools:3] q0"], ids=["erreur", "limite", "budget"])
def test_any_other_end_of_turn_hands_the_waiting_messages_back(sends, redis, mocker, question):
    mocker.patch("web.runner.config.MAX_TOOL_CALLS", 2)
    conv_id = start(question, "q1")

    asyncio.run(run_until_done(TaskRunner(), redis, conv_id, question))

    assert returned(conv_id) == ["q1"]
    assert sends.call_count == 1


@pytest.mark.parametrize("ending", ["arrêt", "balayage", "extinction"])
def test_stop_sweep_and_shutdown_hand_the_waiting_messages_back(sends, redis, ending):
    conv_id = start("[hang] q0", "q1")
    runner = TaskRunner()
    endings = {
        "arrêt": lambda: runner.cancel(conv_id),
        "balayage": lambda: runner._release_conversation(redis, conv_id, "*Interrompu (tâche bloquée).*"),
        "extinction": runner.shutdown,
    }

    async def scenario():
        await runner.submit(conv_id, "[hang] q0", [], ALICE)
        runner._consumer_task = asyncio.create_task(runner._consumer_loop())
        async with asyncio.timeout(10):
            while conv_id not in runner._running:
                await asyncio.sleep(0.02)
        await endings[ending]()
        # Why: lu avant l'extinction finale, qui rendrait la file d'elle-même et masquerait l'issue testée.
        outcome = store.get_conversation(conv_id, include_messages=False).needs_response, returned(conv_id)
        await runner.shutdown()
        return outcome

    assert asyncio.run(scenario()) == (False, ["q1"])
    assert sends.call_count == 1
