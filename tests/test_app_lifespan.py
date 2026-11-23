"""Tests for web/app.py lifespan — dashboard_storage schema bootstrap at startup."""

import asyncio

import pytest
from sqlalchemy.exc import SQLAlchemyError

from web import app as app_module


def _mock_lifespan_deps(mocker):
    mocker.patch("web.app.warmup")
    mocker.patch("web.app.sync_to_s3.start_sync_watcher")
    mocker.patch("web.app.runner.startup", new=mocker.AsyncMock())
    mocker.patch("web.app.runner.shutdown", new=mocker.AsyncMock())
    mocker.patch("web.app.close_redis", new=mocker.AsyncMock())
    mocker.patch("web.app.config.MEMORY_PROFILE_INTERVAL", 0)


async def _drive_lifespan():
    async with app_module.lifespan(app_module.app):
        pass


def test_lifespan_bootstraps_dashboard_storage_schema(mocker):
    _mock_lifespan_deps(mocker)
    ensure = mocker.patch("web.app.failure_detection.ensure_schema")

    asyncio.run(_drive_lifespan())

    ensure.assert_called_once()


def test_lifespan_survives_schema_bootstrap_failure(mocker, caplog):
    _mock_lifespan_deps(mocker)
    mocker.patch("web.app.failure_detection.ensure_schema", side_effect=SQLAlchemyError("db down"))

    asyncio.run(_drive_lifespan())

    assert "dashboard_storage" in caplog.text


def test_lifespan_opens_the_slack_listener_and_closes_it_on_shutdown(mocker):
    _mock_lifespan_deps(mocker)
    mocker.patch("web.app.failure_detection.ensure_schema")
    start = mocker.patch("web.app.slack_listener.start")

    asyncio.run(_drive_lifespan())

    start.return_value.close.assert_called_once()


def test_lifespan_closes_slack_after_the_runner_and_still_closes_redis_when_that_fails(mocker):
    _mock_lifespan_deps(mocker)
    mocker.patch("web.app.failure_detection.ensure_schema")
    start = mocker.patch("web.app.slack_listener.start")
    order = []
    app_module.runner.shutdown.side_effect = lambda: order.append("runner")

    def failing_close():
        order.append("slack")
        raise RuntimeError("close failed")

    start.return_value.close.side_effect = failing_close
    app_module.close_redis.side_effect = lambda: order.append("redis")

    with pytest.raises(RuntimeError, match="close failed"):
        asyncio.run(_drive_lifespan())

    assert order == ["runner", "slack", "redis"]


def test_lifespan_runs_without_a_slack_listener(mocker):
    _mock_lifespan_deps(mocker)
    mocker.patch("web.app.failure_detection.ensure_schema")
    mocker.patch("web.app.slack_listener.start", return_value=None)

    asyncio.run(_drive_lifespan())

    app_module.runner.shutdown.assert_awaited_once()
