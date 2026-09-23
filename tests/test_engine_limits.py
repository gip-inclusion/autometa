"""Clé de limite partagée par les workers, lue par les prompts courts, pilotable à la main."""

import fakeredis
import pytest

from web import engine_limits


@pytest.fixture
def fake_redis(mocker):
    client = fakeredis.FakeRedis(decode_responses=True)
    mocker.patch.object(engine_limits.redis.Redis, "from_url", return_value=client)
    return client


def test_backend_is_limited_reads_the_key_the_runner_writes(fake_redis):
    """Une clé divergente rendrait le garde-fou muet sans que rien ne le signale."""
    assert engine_limits.backend_is_limited("cli") is False
    fake_redis.set("autometa:limit:cli", "1")
    assert engine_limits.backend_is_limited("cli") is True


def test_a_redis_outage_does_not_block_short_prompts(mocker):
    """Panne Redis : on préfère un titre qui échoue en aval à un titre jamais tenté."""
    mocker.patch.object(engine_limits.redis.Redis, "from_url", side_effect=engine_limits.redis.RedisError("down"))

    assert engine_limits.backend_is_limited("cli") is False


def test_an_operator_can_simulate_then_clear_a_limit(fake_redis):
    engine_limits.main(["simulate", "cli", "--seconds", "600"])
    assert 590 < fake_redis.ttl("autometa:limit:cli") <= 600

    engine_limits.main(["clear", "cli"])
    assert not fake_redis.exists("autometa:limit:cli")
