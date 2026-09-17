"""Le verrou de limite traverse deux clients Redis distincts : celui du runner et celui des prompts courts."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from web import llm, runner
from web.llm_errors import LLMError
from web.redis_conn import get_redis

pytestmark = pytest.mark.integration


def _play(coro_factory):
    async def _go():
        r = await get_redis()
        await r.delete(runner.limit_key("cli"))
        try:
            await coro_factory(r)
        finally:
            await r.delete(runner.limit_key("cli"))

    asyncio.run(_go())


def test_the_short_prompt_guard_reads_the_key_the_runner_writes():
    """Le runner pose la clé avec un client asyncio, le garde-fou la lit avec un client synchrone :
    un préfixe ou un encodage divergent laisserait le garde-fou muet sans que rien ne le signale."""
    reset = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    async def _steps(r):
        assert llm.backend_is_limited("cli") is False
        await runner.mark_backend_limited("cli", reset)
        assert llm.backend_is_limited("cli") is True
        await r.delete(runner.limit_key("cli"))
        assert llm.backend_is_limited("cli") is False

    _play(_steps)


def test_a_real_limit_window_abandons_the_title_instead_of_calling_the_cli(mocker):
    """Bout en bout du cas d'usage : limite posée par le runner, titre demandé, aucun appel CLI."""
    mocker.patch("web.llm.config.LLM_BACKEND", "cli")
    call = mocker.patch.object(llm, "llm_call")
    reset = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    async def _steps(_r):
        await runner.mark_backend_limited("cli", reset)
        with pytest.raises(LLMError):
            llm.generate_text("résume ceci")
        call.assert_not_called()

    _play(_steps)


def test_the_guard_lets_short_prompts_through_once_the_window_is_over(mocker):
    mocker.patch("web.llm.config.LLM_BACKEND", "cli")
    mocker.patch.object(llm, "llm_call", return_value="Un titre")

    async def _steps(r):
        await runner.mark_backend_limited("cli", (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat())
        await r.delete(runner.limit_key("cli"))
        assert llm.generate_text("résume ceci") == "Un titre"

    _play(_steps)
