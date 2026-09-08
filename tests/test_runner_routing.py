"""Tests du routage multi-moteurs — choix du moteur et verrou de limite d'usage."""

import asyncio
from datetime import datetime, timedelta, timezone

import fakeredis.aioredis
import pytest

from web import runner


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.mark.parametrize(
    "fallback, blocked, expected",
    [
        ("", False, "cli"),
        ("", True, "cli"),
        ("cli-ollama", False, "cli"),
        ("cli-ollama", True, "cli-ollama"),
    ],
)
def test_pick_backend(mocker, fake_redis, fallback, blocked, expected):
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    mocker.patch("web.runner.config.AGENT_FALLBACK_BACKEND", fallback)
    mocker.patch("web.runner.get_redis", return_value=fake_redis)

    async def _run():
        if blocked:
            await fake_redis.set(runner.limit_key("cli"), "1")
        assert await runner.pick_backend() == expected

    asyncio.run(_run())


def test_pick_backend_skips_redis_without_fallback(mocker):
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    mocker.patch("web.runner.config.AGENT_FALLBACK_BACKEND", "")
    spy = mocker.patch("web.runner.get_redis")

    async def _run():
        assert await runner.pick_backend() == "cli"

    asyncio.run(_run())
    spy.assert_not_called()


def test_mark_backend_limited_sets_key_expiring_at_reset(mocker, fake_redis):
    mocker.patch("web.runner.get_redis", return_value=fake_redis)
    reset = datetime.now(timezone.utc) + timedelta(hours=3)

    async def _run():
        await runner.mark_backend_limited("cli", reset.isoformat())
        assert await fake_redis.exists(runner.limit_key("cli"))
        ttl = await fake_redis.ttl(runner.limit_key("cli"))
        assert 3 * 3600 - 60 < ttl <= 3 * 3600

    asyncio.run(_run())


def test_mark_backend_limited_ignores_missing_reset(mocker, fake_redis):
    mocker.patch("web.runner.get_redis", return_value=fake_redis)

    async def _run():
        await runner.mark_backend_limited("cli", None)
        assert await fake_redis.keys("*") == []

    asyncio.run(_run())
