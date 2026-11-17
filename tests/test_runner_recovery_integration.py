"""Démarré pendant une coupure de la file, le runner reprend seul la distribution à son retour."""

import asyncio
import socket
from urllib.parse import urlparse

import pytest

from web import config
from web.runner import TaskRunner

pytestmark = pytest.mark.integration


async def pipe(reader, writer):
    while data := await reader.read(65536):
        writer.write(data)
        await writer.drain()
    writer.close()


@pytest.mark.parametrize("outage", ["refused", "silent"])
def test_dod_1_dod_4_runner_dispatches_a_message_sent_after_redis_comes_back(mocker, outage):
    """Une file qui refuse ou qui se tait, puis revient : le message suivant est distribué sans redémarrage."""
    upstream = urlparse(config.REDIS_URL)
    with socket.create_server(("127.0.0.1", 0)) as probe:
        port = probe.getsockname()[1]
    mocker.patch("web.config.REDIS_URL", f"redis://127.0.0.1:{port}{upstream.path}")
    mocker.patch("web.redis_conn.SOCKET_TIMEOUT", 1.5)
    mocker.patch("web.redis_conn._pool", None)
    mocker.patch("web.runner.PREFIX", f"test-recovery-{outage}")
    mocker.patch("web.runner.get_agent")
    mocker.patch("web.runner.schema_ready", return_value=True)
    store = mocker.patch("web.runner.store")
    store.get_running_conversation_ids.return_value = []
    store.get_conversation.return_value = None
    runner = TaskRunner()

    async def _run():
        restored = asyncio.Event()

        async def relay(reader, writer):
            # Why: une connexion acceptée pendant le silence reste muette pour de bon, comme pendant l'incident.
            if not restored.is_set():
                await asyncio.Event().wait()
            up_reader, up_writer = await asyncio.open_connection(upstream.hostname, upstream.port)
            await asyncio.gather(pipe(reader, up_writer), pipe(up_reader, writer), return_exceptions=True)

        if outage == "silent":
            server = await asyncio.start_server(relay, "127.0.0.1", port)
        await runner.startup()
        await asyncio.sleep(2)
        if outage == "refused":
            server = await asyncio.start_server(relay, "127.0.0.1", port)
        restored.set()
        await runner.submit("dod-recovery", "bonjour", [])
        for _ in range(100):
            if store.get_conversation.called:
                break
            await asyncio.sleep(0.1)
        loops = [runner._consumer_task, runner._heartbeat_task, runner._sweep_task]
        for task in loops:
            task.cancel()
        await asyncio.gather(*loops, return_exceptions=True)
        server.close()

    asyncio.run(_run())
    store.get_conversation.assert_called_with("dod-recovery", include_messages=False)
