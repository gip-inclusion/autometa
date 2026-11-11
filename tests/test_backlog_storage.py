from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from lib import backlog_storage
from lib.backlog_storage import backlog_context
from web.db import get_engine


def context(age=timedelta(0), teams=None):
    return {"generated_at": (datetime.now(UTC) - age).isoformat(), "teams": teams or []}


def test_dod_2_current_context_reads_notion_and_stores_when_nothing_is_fresh(mocker):
    new_context = context()
    mocker.patch.object(backlog_storage, "read_context", return_value=None)
    load = mocker.patch.object(backlog_storage.backlog, "load_context", return_value=new_context)
    store = mocker.patch.object(backlog_storage, "save_context")
    assert backlog_storage.current_context() == new_context
    load.assert_called_once()
    store.assert_called_once_with(new_context)


def test_dod_2_fresh_current_context_does_not_read_notion(mocker):
    fresh_context = context(timedelta(hours=3))
    mocker.patch.object(backlog_storage, "read_context", return_value=fresh_context)
    load = mocker.patch.object(backlog_storage.backlog, "load_context")
    store = mocker.patch.object(backlog_storage, "save_context")
    assert backlog_storage.current_context() == fresh_context
    load.assert_not_called()
    store.assert_not_called()


def test_main_without_config_does_not_read_notion(mocker):
    mocker.patch.object(backlog_storage.config, "NOTION_BACKLOG_DB", None)
    load = mocker.patch.object(backlog_storage.backlog, "load_context")
    backlog_storage.main()
    load.assert_not_called()


def test_main_configured_loads_once_and_stores(mocker):
    new_context = context()
    mocker.patch.object(backlog_storage.config, "NOTION_BACKLOG_DB", "db-factice")
    load = mocker.patch.object(backlog_storage.backlog, "load_context", return_value=new_context)
    store = mocker.patch.object(backlog_storage, "save_context")
    backlog_storage.main()
    load.assert_called_once()
    store.assert_called_once_with(new_context)


@pytest.fixture
def empty_table():
    backlog_storage.ensure_schema()
    with get_engine().begin() as conn:
        conn.execute(delete(backlog_context))
    yield


@pytest.mark.integration
@pytest.mark.usefixtures("_db", "empty_table")
class TestStorage:
    def test_dod_2_save_then_read_returns_the_same_context(self):
        ctx = context(timedelta(hours=1), [{"id": "e1", "name": "Equipe", "epics": [], "recent_titles": ["t"]}])
        backlog_storage.save_context(ctx)
        assert backlog_storage.read_context() == ctx

    def test_read_without_table_returns_none(self):
        backlog_context.drop(get_engine(), checkfirst=True)
        assert backlog_storage.read_context() is None

    def test_read_without_row_returns_none(self):
        assert backlog_storage.read_context() is None

    @pytest.mark.parametrize(
        ("offset", "expected_present"),
        [(timedelta(minutes=-1), True), (timedelta(minutes=1), False)],
    )
    def test_dod_2_freshness_around_30_hours(self, offset, expected_present):
        ctx = context(timedelta(hours=30) + offset)
        backlog_storage.save_context(ctx)
        assert (backlog_storage.read_context() == ctx) is expected_present

    def test_an_older_load_does_not_overwrite_a_newer_one(self):
        recent = context(timedelta(hours=1), [{"id": "recent"}])
        older = context(timedelta(hours=5), [{"id": "ancien"}])
        backlog_storage.save_context(recent)
        backlog_storage.save_context(older)
        assert backlog_storage.read_context() == recent
