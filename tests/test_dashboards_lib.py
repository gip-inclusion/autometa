"""Tests for lib/dashboards (create_dashboard, update_dashboard, normalize_tag_name)."""

import os
import shutil
from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, select

from lib.dashboards import (
    DashboardNotFound,
    cleanup_orphan_scaffolds,
    create_dashboard,
    normalize_tag_name,
    normalize_tags,
    update_dashboard,
)
from web.db import get_db
from web.db import test_transaction as _test_tx
from web.models import Dashboard, DashboardTag, Tag


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
        title="T",
        description="D",
        website="emplois",
        category="Test",
        tags=[],
        has_cron=False,
        first_author_email="alice@x",
        created_in_conversation_id="c1",
    )
    base.update(overrides)
    return create_dashboard(**base)


def test_create_dashboard_happy_path(isolated):
    d = _create("happy", tags=["foo", "bar"], has_cron=True)
    assert d.slug == "happy"
    assert d.has_cron is True
    assert d.first_author_email == "alice@x"
    assert d.created_in_conversation_id == "c1"

    slug_dir = isolated / "happy"
    files = sorted(p.name for p in slug_dir.iterdir())
    assert "APP.md" in files
    assert "cron.py" in files
    assert "index.html" in files

    with get_db() as session:
        tag_names = sorted(
            session.scalars(
                select(Tag.name)
                .join(DashboardTag, DashboardTag.tag_id == Tag.id)
                .where(DashboardTag.dashboard_slug == "happy")
            ).all()
        )
    assert tag_names == ["bar", "foo"]


def test_create_dashboard_no_cron_skips_cronpy(isolated):
    _create("nocron", has_cron=False)
    files = {p.name for p in (isolated / "nocron").iterdir()}
    assert "cron.py" not in files


@pytest.mark.parametrize("bad_slug", ["BadCase", "with space", "trailing-", "with_underscore", ""])
def test_create_dashboard_invalid_slug(isolated, bad_slug):
    with pytest.raises(ValueError, match="Invalid slug"):
        _create(bad_slug)


def test_create_dashboard_existing_dir(isolated):
    (isolated / "exists").mkdir()
    with pytest.raises(ValueError, match="already exists on disk"):
        _create("exists")


def test_create_dashboard_existing_db_row(isolated):
    _create("dup")
    shutil.rmtree(isolated / "dup")
    with pytest.raises(ValueError, match="already exists in DB"):
        _create("dup")


def test_create_dashboard_returns_detached_orm_with_loaded_attrs(isolated):
    # Why: vérifie que les attributs (notamment ceux peuplés par le flush) restent
    # accessibles après fermeture de la session. Sans refresh+expunge dans la lib,
    # l'accès depuis un caller hors test_transaction lèverait DetachedInstanceError.
    d = _create("expunge-test", has_cron=True)
    assert inspect(d).detached
    assert d.slug == "expunge-test"
    assert d.has_cron is True
    assert d.created_at is not None
    assert d.first_author_email == "alice@x"


def test_create_dashboard_normalizes_tags(isolated):
    _create("norm", tags=["FOO", "  Bar  ", "Foo", "with spaces"])
    with get_db() as session:
        tag_names = sorted(
            session.scalars(
                select(Tag.name)
                .join(DashboardTag, DashboardTag.tag_id == Tag.id)
                .where(DashboardTag.dashboard_slug == "norm")
            ).all()
        )
    assert tag_names == ["bar", "foo", "with-spaces"]


def test_update_dashboard_not_found(isolated):
    with pytest.raises(DashboardNotFound):
        update_dashboard(slug="nope", updater_email="bob@x", in_conversation_id="c2", title="X")


def test_update_dashboard_no_change(isolated):
    _create("uc")
    r = update_dashboard(slug="uc", updater_email="bob@x", in_conversation_id="c2")
    assert r.fields_changed == []
    assert r.originating_user_email == "alice@x"
    assert r.updater_email == "bob@x"


def test_update_dashboard_scalar_changes(isolated):
    _create("us", title="V1")
    r = update_dashboard(
        slug="us",
        updater_email="bob@x",
        in_conversation_id="c2",
        title="V2",
        has_api_access=True,
        is_archived=True,
    )
    assert sorted(r.fields_changed) == ["has_api_access", "is_archived", "title"]


def test_update_dashboard_set_tags_replaces(isolated):
    _create("ut", tags=["a", "b"])
    update_dashboard(slug="ut", updater_email="bob@x", in_conversation_id="c2", set_tags=["x", "y"])
    with get_db() as session:
        tag_names = sorted(
            session.scalars(
                select(Tag.name)
                .join(DashboardTag, DashboardTag.tag_id == Tag.id)
                .where(DashboardTag.dashboard_slug == "ut")
            ).all()
        )
    assert tag_names == ["x", "y"]


def test_update_dashboard_add_remove_tags(isolated):
    _create("ar", tags=["a", "b"])
    update_dashboard(
        slug="ar",
        updater_email="bob@x",
        in_conversation_id="c2",
        add_tags=["c"],
        remove_tags=["a"],
    )
    with get_db() as session:
        tag_names = sorted(
            session.scalars(
                select(Tag.name)
                .join(DashboardTag, DashboardTag.tag_id == Tag.id)
                .where(DashboardTag.dashboard_slug == "ar")
            ).all()
        )
    assert tag_names == ["b", "c"]


def test_update_dashboard_set_tags_mutex(isolated):
    _create("mx")
    with pytest.raises(ValueError, match="mutually exclusive"):
        update_dashboard(
            slug="mx",
            updater_email="bob@x",
            in_conversation_id="c2",
            set_tags=["a"],
            add_tags=["b"],
        )


def test_update_dashboard_syncs_app_md_for_syncable_fields(isolated):
    _create("sy", title="V1")
    update_dashboard(slug="sy", updater_email="bob@x", in_conversation_id="c2", title="V2")
    fm = (isolated / "sy" / "APP.md").read_text().split("---", 2)[1]
    assert "title: V2" in fm


def test_update_dashboard_archive_does_not_sync_app_md(isolated):
    _create("ar2", title="V1")
    fm_before = (isolated / "ar2" / "APP.md").read_text()
    update_dashboard(slug="ar2", updater_email="bob@x", in_conversation_id="c2", is_archived=True)
    fm_after = (isolated / "ar2" / "APP.md").read_text()
    assert fm_before == fm_after


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("foo", "foo"),
        ("FOO", "foo"),
        ("  foo  ", "foo"),
        ("with space", "with-space"),
        ("Mixed Case 123", "mixed-case-123"),
        ("", None),
        ("   ", None),
    ],
)
def test_normalize_tag_name(raw, expected):
    assert normalize_tag_name(raw) == expected


def test_normalize_tags_dedupes_and_filters_empty():
    assert normalize_tags(["foo", "FOO", "  foo  ", "", "Bar"]) == ["foo", "bar"]


def test_create_dashboard_db_failure_cleans_staging(isolated, mocker):
    mocker.patch("lib.dashboards._upsert_tag", side_effect=RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        _create("staged", tags=["foo"])
    assert not (isolated / "staged").exists()
    assert [p.name for p in isolated.iterdir() if p.name.startswith(".tmp-")] == []


def test_create_dashboard_template_copy_failure_no_partial_state(isolated, mocker):
    mocker.patch("lib.dashboards.shutil.copy2", side_effect=OSError("disk full"))
    with pytest.raises(OSError, match="disk full"):
        _create("nodisk")
    assert not (isolated / "nodisk").exists()
    assert [p.name for p in isolated.iterdir() if p.name.startswith(".tmp-")] == []
    with get_db() as session:
        assert session.scalar(select(Dashboard).where(Dashboard.slug == "nodisk")) is None


def test_create_dashboard_rename_failure_cleans_staging_no_db_row(isolated, mocker):
    mocker.patch("lib.dashboards.os.rename", side_effect=OSError("rename failed"))
    with pytest.raises(OSError, match="rename failed"):
        _create("rename-fail")
    assert not (isolated / "rename-fail").exists()
    assert [p.name for p in isolated.iterdir() if p.name.startswith(".tmp-")] == []
    with get_db() as session:
        assert session.scalar(select(Dashboard).where(Dashboard.slug == "rename-fail")) is None


def test_cleanup_dry_run_flags_old_staging_without_deleting(isolated):
    old = isolated / ".tmp-foo-deadbeef"
    old.mkdir()
    old_ts = datetime.now(timezone.utc).timestamp() - 30 * 60
    os.utime(old, (old_ts, old_ts))
    result = cleanup_orphan_scaffolds(staging_max_age_minutes=10)
    assert ".tmp-foo-deadbeef" in result["staging"]
    assert result["dry_run"] is True
    assert old.exists()


def test_cleanup_keeps_recent_staging(isolated):
    recent = isolated / ".tmp-foo-cafebabe"
    recent.mkdir()
    result = cleanup_orphan_scaffolds(staging_max_age_minutes=10)
    assert recent.exists()
    assert result["staging"] == []


def test_cleanup_dry_run_flags_orphan_without_deleting(isolated):
    orphan = isolated / "orphan-slug"
    orphan.mkdir()
    result = cleanup_orphan_scaffolds()
    assert "orphan-slug" in result["orphan"]
    assert orphan.exists()


def test_cleanup_keeps_known_dashboard(isolated):
    _create("kept")
    result = cleanup_orphan_scaffolds()
    assert (isolated / "kept").exists()
    assert "kept" not in result["orphan"]


@pytest.mark.parametrize(
    "dir_name,key,age_offset_min",
    [
        (".tmp-bar-feedface", "staging", -30),
        ("orphan-bar", "orphan", 0),
    ],
)
def test_cleanup_deletes_when_dry_run_false(isolated, dir_name, key, age_offset_min):
    target = isolated / dir_name
    target.mkdir()
    if age_offset_min:
        ts = datetime.now(timezone.utc).timestamp() + age_offset_min * 60
        os.utime(target, (ts, ts))
    result = cleanup_orphan_scaffolds(dry_run=False)
    assert dir_name in result[key]
    assert result["dry_run"] is False
    assert not target.exists()


def test_main_logs_warning_when_orphans_found(isolated, caplog):
    (isolated / "orphan-bar").mkdir()
    from lib.dashboards import main

    with caplog.at_level("WARNING", logger="lib.dashboards"):
        main()
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert warnings, "expected a warning when orphans are flagged"
    assert "orphan-bar" in str(warnings[0].args)
