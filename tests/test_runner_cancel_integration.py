"""L'écoute de l'arrêt tient sur une vraie connexion Redis, délai de lecture compris."""

import asyncio

import pytest

from web.redis_conn import get_redis
from web.runner import TaskRunner

pytestmark = pytest.mark.integration


def test_dod_2_cancel_signal_reaches_a_run_after_a_long_silence(mocker):
    """Une écoute bloquante de l'abonnement retomberait sur le délai du client et tomberait au premier silence."""
    mocker.patch("web.redis_conn.SOCKET_TIMEOUT", 0.2)
    mocker.patch("web.redis_conn._pool", None)
    backend = mocker.MagicMock(cancel=mocker.AsyncMock())
    mocker.patch("web.runner.get_agent", return_value=backend)

    async def _run():
        listener = asyncio.create_task(TaskRunner()._listen_cancel("dod-2"))
        await asyncio.sleep(1)
        r = await get_redis()
        await r.publish("autometa:cancel:dod-2", "1")
        await asyncio.wait_for(listener, 3)
        await r.aclose()

    asyncio.run(_run())
    backend.cancel.assert_awaited_with("dod-2")
