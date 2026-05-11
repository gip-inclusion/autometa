"""Tests for web.database.store.list_dashboards (DB-backed inventory)."""

import shutil

import pytest

from lib.dashboards import create_dashboard, update_dashboard
from web.database import store
from web.db import test_transaction as _test_tx


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    import web.config as cfg

    interactive_dir = tmp_path / "interactive"
    interactive_dir.mkdir()
    monkeypatch.setattr(cfg, "INTERACTIVE_DIR", interactive_dir)
    with _test_tx():
        yield interactive_dir
    shutil.rmtree(interactive_dir, ignore_errors=True)


def _create(slug, **overrides):
    base = dict(
        slug=slug,
        title=f"T-{slug}",
        description="d",
        website="emplois",
        category="Test",
        tags=[],
        has_cron=False,
        first_author_email="alice@x",
        created_in_conversation_id="c1",
    )
    base.update(overrides)
    return create_dashboard(**base)


def test_list_dashboards_empty(isolated):
    assert store.list_dashboards() == []


def test_list_dashboards_returns_legacy_shape(isolated):
    _create("foo", tags=["a", "b"])
    apps = store.list_dashboards()
    assert len(apps) == 1
    app = apps[0]
    assert app["slug"] == "foo"
    assert app["title"] == "T-foo"
    assert app["description"] == "d"
    assert app["website"] == "emplois"
    assert app["category"] == "Test"
    assert sorted(app["tags"]) == ["a", "b"]
    assert app["authors"] == ["alice@x"]
    assert app["conversation_id"] == "c1"
    assert app["url"] == "/interactive/foo/"
    assert app["is_interactive"] is True
    assert app["updated"] is not None


def test_list_dashboards_excludes_archived(isolated):
    _create("a")
    _create("b")
    update_dashboard(slug="b", updater_email="x@x", in_conversation_id="c", is_archived=True)
    apps = store.list_dashboards()
    assert sorted(a["slug"] for a in apps) == ["a"]


def test_list_dashboards_orders_by_updated_desc(isolated):
    _create("first")
    _create("second")
    update_dashboard(slug="first", updater_email="x@x", in_conversation_id="c", title="bumped")
    apps = store.list_dashboards()
    assert [a["slug"] for a in apps] == ["first", "second"]


def test_list_dashboards_no_n_plus_1_on_tags(isolated):
    _create("x", tags=["a", "b", "c"])
    _create("y", tags=["b", "d"])
    apps = {a["slug"]: a for a in store.list_dashboards()}
    assert sorted(apps["x"]["tags"]) == ["a", "b", "c"]
    assert sorted(apps["y"]["tags"]) == ["b", "d"]
