"""Tests for web/sentry.py — Sentry SDK initialization and helpers."""

import asyncio
import json

import fakeredis.aioredis
import pytest
import sentry_sdk


@pytest.fixture(autouse=True)
def reset_sentry():
    """Ensure Sentry is clean before/after each test."""
    yield
    scope = sentry_sdk.get_current_scope()
    scope.clear()
    sentry_sdk.init()


def test_init_sentry_noop_without_dsn(monkeypatch):
    monkeypatch.setattr("web.config.SENTRY_DSN", "")
    from web.sentry import init_sentry

    init_sentry()
    assert not sentry_sdk.get_client().is_active()


def test_init_sentry_activates_with_dsn(monkeypatch):
    monkeypatch.setattr("web.config.SENTRY_DSN", "https://examplePublicKey@o0.ingest.sentry.io/0")
    monkeypatch.setattr("web.config.SENTRY_ENVIRONMENT", "prod")
    monkeypatch.setattr("web.config.SENTRY_TRACES_SAMPLE_RATE", 1.0)
    from web.sentry import init_sentry

    init_sentry()
    client = sentry_sdk.get_client()
    assert client.is_active()
    assert client.options["environment"] == "prod"


def test_set_user_context():
    from web.sentry import set_user_context

    set_user_context("alice@example.com")
    scope = sentry_sdk.get_isolation_scope()
    assert (scope._user or {}).get("email") == "alice@example.com"


def test_before_send_scrubs_headers(monkeypatch):
    monkeypatch.setattr("web.config.SENTRY_DSN", "https://fake@sentry.io/0")
    from web.sentry import _before_send

    event = {
        "request": {
            "headers": {
                "x-forwarded-email": "alice@example.com",
                "x-forwarded-user": "alice",
                "cookie": "session=abc",
                "authorization": "Bearer xyz",
                "content-type": "application/json",
            }
        }
    }
    result = _before_send(event, {})
    assert result is not None
    headers = result["request"]["headers"]
    assert headers["x-forwarded-email"] == "[filtered]"
    assert headers["x-forwarded-user"] == "[filtered]"
    assert headers["cookie"] == "[filtered]"
    assert headers["authorization"] == "[filtered]"
    assert headers["content-type"] == "application/json"


def test_before_send_drops_when_no_dsn(monkeypatch):
    monkeypatch.setattr("web.config.SENTRY_DSN", "")
    from web.sentry import _before_send

    assert _before_send({"request": {}}, {}) is None


@pytest.mark.parametrize(
    "raw,expected_marker",
    [
        ("traceback: Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig", "[scrubbed]"),
        ("auth failed for sk-ant-api03-XYZabc123_DEFghi456jklMNOpqr789-stuVWXyz", "[scrubbed]"),
        ("aws creds AKIAIOSFODNN7EXAMPLE rotated", "[scrubbed]"),
        ('config error: api_key="my-very-secret-value-here"', "[scrubbed]"),
    ],
)
def test_before_send_scrubs_secret_patterns_from_extras(monkeypatch, raw, expected_marker):
    monkeypatch.setattr("web.config.SENTRY_DSN", "https://fake@sentry.io/0")
    from web.sentry import _before_send

    event = {"extra": {"stderr": raw, "last_events": [raw, "harmless line"]}}
    result = _before_send(event, {})
    assert result is not None
    assert expected_marker in result["extra"]["stderr"]
    assert raw not in result["extra"]["stderr"]
    assert expected_marker in result["extra"]["last_events"][0]
    assert result["extra"]["last_events"][1] == "harmless line"


def test_before_send_preserves_non_secret_extras(monkeypatch):
    monkeypatch.setattr("web.config.SENTRY_DSN", "https://fake@sentry.io/0")
    from web.sentry import _before_send

    event = {"extra": {"conversation_id": "conv-42", "exit_code": 1, "stderr": "regular log output"}}
    result = _before_send(event, {})
    assert result["extra"]["conversation_id"] == "conv-42"
    assert result["extra"]["exit_code"] == 1
    assert result["extra"]["stderr"] == "regular log output"


def test_before_send_transaction_scrubs_span_attributes(monkeypatch):
    monkeypatch.setattr("web.config.SENTRY_DSN", "https://fake@sentry.io/0")
    from web.sentry import _before_send_transaction

    event = {
        "contexts": {"trace": {"data": {"stderr": "Authorization: Bearer leaked.jwt.token"}}},
        "spans": [{"data": {"stderr": "error: token=abc-secret-value-12345"}}, {"data": None}],
    }
    result = _before_send_transaction(event, {})
    assert "[scrubbed]" in result["contexts"]["trace"]["data"]["stderr"]
    assert "[scrubbed]" in result["spans"][0]["data"]["stderr"]


def test_before_send_transaction_drops_when_no_dsn(monkeypatch):
    monkeypatch.setattr("web.config.SENTRY_DSN", "")
    from web.sentry import _before_send_transaction

    assert _before_send_transaction({"spans": []}, {}) is None


def test_cron_sentry_monitor_config():
    from web.cron import _sentry_monitor_config

    daily_task = {"schedule": "daily", "timeout": 300}
    cfg = _sentry_monitor_config(daily_task)
    assert cfg["schedule"]["value"] == "0 6 * * *"
    assert cfg["max_runtime"] == 6

    weekly_task = {"schedule": "weekly", "timeout": 600}
    cfg = _sentry_monitor_config(weekly_task)
    assert cfg["schedule"]["value"] == "0 6 * * 1"
    assert cfg["max_runtime"] == 11


def test_runner_submit_includes_trace_headers(mocker):
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    mocker.patch("web.runner.get_redis", return_value=fake_redis)
    mocker.patch("web.runner.get_agent")
    mocker.patch("web.runner.inject_trace_headers", return_value={"sentry-trace": "abc-123"})

    from web.runner import TaskRunner

    runner = TaskRunner()

    async def _run():
        await runner.submit("conv-1", "hello", [], user_email="test@test.com")
        payload_str = await fake_redis.lpop("autometa:tasks")
        payload = json.loads(payload_str)
        assert payload["trace_headers"]["sentry-trace"] == "abc-123"

    asyncio.run(_run())
