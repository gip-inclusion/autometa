"""Tests for web/app.py lifespan — dashboard_storage schema bootstrap at startup."""

import asyncio

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


def test_lifespan_survives_schema_bootstrap_failure(mocker):
    _mock_lifespan_deps(mocker)
    mocker.patch("web.app.failure_detection.ensure_schema", side_effect=SQLAlchemyError("db down"))

    asyncio.run(_drive_lifespan())
