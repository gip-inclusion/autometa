"""Tests for cron task discovery, execution, and database logging."""

import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select, text

from web import config, cron
from web.cron import (
    discover_cron_tasks,
    discover_from_dir,
    get_app_runs,
    get_last_runs,
    get_schedule,
    get_timeout,
    is_enabled,
    notify_cron_status_change,
    parse_frontmatter,
    run_all,
    run_cron_task,
    set_cron_enabled,
)
from web.database import get_db
from web.models import Dashboard, DashboardPublication


@pytest.fixture
def interactive_dir(tmp_path, monkeypatch):
    d = tmp_path / "interactive"
    d.mkdir()
    cron_dir = tmp_path / "cron"
    cron_dir.mkdir()
    monkeypatch.setattr(config, "INTERACTIVE_DIR", d)
    monkeypatch.setattr(config, "CRON_DIR", cron_dir)
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr("web.cron.discover_from_s3", lambda: discover_from_dir(d, "APP.md", "app"))
    return d


@pytest.fixture
def db_setup(monkeypatch):
    yield

    with get_db() as session:
        session.execute(
            text("""
            TRUNCATE TABLE messages, conversation_tags, report_tags,
                uploaded_files, cron_runs, pinned_items,
                reports, conversations, tags, schema_version,
                dashboards
                CASCADE;
        """)
        )


def create_interactive_app(interactive_dir, slug, cron_script=None, app_md=None):
    app_dir = interactive_dir / slug
    app_dir.mkdir()

    if app_md is None:
        app_md = f"---\ntitle: {slug}\n---\n"
    (app_dir / "APP.md").write_text(app_md)

    if cron_script is not None:
        (app_dir / "cron.py").write_text(cron_script)

    return app_dir


def test_parse_frontmatter_no_file(tmp_path):
    assert parse_frontmatter(tmp_path / "nonexistent" / "APP.md") == {}


@pytest.mark.parametrize(
    "body,expected",
    [
        ("---\ntitle: Test\n---\n", True),
        ("---\ntitle: Test\ncron: true\n---\n", True),
        ("---\ntitle: Test\ncron: false\n---\n", False),
        ("---\ntitle: Test\ncron: no\n---\n", False),
        ("---\ntitle: Test\ncron: off\n---\n", False),
    ],
)
def test_parse_frontmatter_cron_enabled(tmp_path, body, expected):
    p = tmp_path / "APP.md"
    p.write_text(body)
    assert is_enabled(parse_frontmatter(p)) is expected


def test_parse_frontmatter_no_frontmatter(tmp_path):
    p = tmp_path / "APP.md"
    p.write_text("Just some text")
    assert is_enabled(parse_frontmatter(p)) is True


def test_parse_frontmatter_timeout_field(tmp_path):
    p = tmp_path / "CRON.md"
    p.write_text("---\ntimeout: 1200\n---\n")
    assert get_timeout(parse_frontmatter(p)) == 1200


def test_parse_frontmatter_schedule_field(tmp_path):
    p = tmp_path / "CRON.md"
    p.write_text("---\nschedule: weekly\n---\n")
    assert get_schedule(parse_frontmatter(p)) == "weekly"


def test_discover_empty_dir(interactive_dir):
    assert discover_cron_tasks() == []


def test_discover_app_without_cron_py(interactive_dir):
    create_interactive_app(interactive_dir, "no-cron")
    assert discover_cron_tasks() == []


def test_discover_app_with_cron_py(interactive_dir):
    create_interactive_app(interactive_dir, "my-app", cron_script="print('hi')")
    tasks = discover_cron_tasks()
    assert len(tasks) == 1
    assert tasks[0]["slug"] == "my-app"
    assert tasks[0]["enabled"] is True


def test_discover_disabled_app(interactive_dir):
    create_interactive_app(
        interactive_dir,
        "disabled-app",
        cron_script="print('hi')",
        app_md="---\ntitle: Disabled\ncron: false\n---\n",
    )
    tasks = discover_cron_tasks()
    assert len(tasks) == 1
    assert tasks[0]["slug"] == "disabled-app"
    assert tasks[0]["enabled"] is False


def test_discover_multiple_apps_sorted(interactive_dir):
    create_interactive_app(interactive_dir, "beta", cron_script="pass")
    create_interactive_app(interactive_dir, "alpha", cron_script="pass")
    tasks = discover_cron_tasks()
    assert [t["slug"] for t in tasks] == ["alpha", "beta"]


def test_discover_extracts_title(interactive_dir):
    create_interactive_app(
        interactive_dir,
        "titled-app",
        cron_script="pass",
        app_md="---\ntitle: My Great App\n---\n",
    )
    tasks = discover_cron_tasks()
    assert tasks[0]["title"] == "My Great App"


def test_discover_nonexistent_dir(monkeypatch):
    monkeypatch.setattr(config, "INTERACTIVE_DIR", Path("/nonexistent"))
    monkeypatch.setattr(config, "CRON_DIR", Path("/nonexistent"))
    assert discover_cron_tasks() == []


def test_discover_system_tasks_come_first(interactive_dir, tmp_path, monkeypatch):
    """System tasks (cron/) are listed before app tasks (interactive/)."""
    cron_dir = tmp_path / "cron"
    monkeypatch.setattr(config, "CRON_DIR", cron_dir)

    sys_dir = cron_dir / "sys-task"
    sys_dir.mkdir(parents=True)
    (sys_dir / "cron.py").write_text("pass")
    (sys_dir / "CRON.md").write_text("---\ntitle: System Task\nschedule: weekly\n---\n")

    create_interactive_app(interactive_dir, "app-task", cron_script="pass")

    tasks = discover_cron_tasks()
    assert len(tasks) == 2
    assert tasks[0]["slug"] == "sys-task"
    assert tasks[0]["tier"] == "system"
    assert tasks[0]["schedule"] == "weekly"
    assert tasks[1]["slug"] == "app-task"
    assert tasks[1]["tier"] == "app"


def test_run_cron_success(interactive_dir, db_setup):
    create_interactive_app(interactive_dir, "good-app", cron_script="print('hello world')")
    result = run_cron_task("good-app", trigger="manual")
    assert result["status"] == "success"
    assert "hello world" in result["output"]
    assert result["duration_ms"] >= 0


def test_run_cron_failure_exit_code(interactive_dir, db_setup):
    create_interactive_app(interactive_dir, "bad-app", cron_script="import sys; sys.exit(1)")
    result = run_cron_task("bad-app", trigger="manual")
    assert result["status"] == "failure"


def test_run_cron_stderr_captured(interactive_dir, db_setup):
    create_interactive_app(
        interactive_dir,
        "stderr-app",
        cron_script="import sys; print('err', file=sys.stderr)",
    )
    result = run_cron_task("stderr-app", trigger="manual")
    assert "err" in result["output"]


def test_run_cron_nonexistent_app(interactive_dir, db_setup):
    result = run_cron_task("no-such-app")
    assert result["status"] == "failure"
    assert "not found" in result["output"]


def test_run_cron_writes_data_file(interactive_dir, db_setup):
    script = textwrap.dedent("""\
        import json
        with open('data.json', 'w') as f:
            json.dump({"updated": True}, f)
    """)
    create_interactive_app(interactive_dir, "writer-app", cron_script=script)
    result = run_cron_task("writer-app")
    assert result["status"] == "success"

    data_file = interactive_dir / "writer-app" / "data.json"
    assert data_file.exists()
    assert json.loads(data_file.read_text())["updated"] is True


def test_run_cron_timeout(interactive_dir, db_setup):
    create_interactive_app(
        interactive_dir,
        "slow-app",
        cron_script="import time; time.sleep(10)",
        app_md="---\ntitle: Slow\ntimeout: 1\n---\n",
    )
    result = run_cron_task("slow-app")
    assert result["status"] == "timeout"


def test_run_cron_records_in_database(interactive_dir, db_setup):
    create_interactive_app(interactive_dir, "db-app", cron_script="print('ok')")
    run_cron_task("db-app", trigger="manual")

    with get_db() as session:
        row = (
            session
            .execute(
                text("SELECT * FROM cron_runs WHERE app_slug = :slug"),
                {"slug": "db-app"},
            )
            .mappings()
            .first()
        )
        assert row is not None
        assert row["status"] == "success"
        assert row["trigger"] == "manual"


def test_run_cron_pythonpath_includes_project_root(interactive_dir, db_setup):
    script = textwrap.dedent("""\
        import sys
        print(sys.path)
    """)
    create_interactive_app(interactive_dir, "path-app", cron_script=script)
    result = run_cron_task("path-app")
    assert result["status"] == "success"
    assert str(config.BASE_DIR) in result["output"]


def test_get_last_runs_empty(interactive_dir, db_setup):
    assert get_last_runs() == {}


def test_get_last_runs_returns_latest(interactive_dir, db_setup):
    create_interactive_app(interactive_dir, "multi-app", cron_script="print('run')")
    run_cron_task("multi-app")
    run_cron_task("multi-app")

    runs = get_last_runs(limit_per_app=1)
    assert "multi-app" in runs
    assert len(runs["multi-app"]) == 1


def test_get_last_runs_limit_per_app(interactive_dir, db_setup):
    create_interactive_app(interactive_dir, "many-app", cron_script="print('x')")
    for _ in range(5):
        run_cron_task("many-app")

    runs = get_last_runs(limit_per_app=3)
    assert len(runs["many-app"]) == 3


def test_get_app_runs_empty(interactive_dir, db_setup):
    assert get_app_runs("nonexistent") == []


def test_get_app_runs_returns_runs(interactive_dir, db_setup):
    create_interactive_app(interactive_dir, "log-app", cron_script="print('logged')")
    run_cron_task("log-app")
    runs = get_app_runs("log-app")
    assert len(runs) == 1
    assert runs[0]["status"] == "success"


def test_set_cron_enabled_disable(interactive_dir):
    create_interactive_app(interactive_dir, "toggle-app", cron_script="pass")
    assert set_cron_enabled("toggle-app", False) is True

    content = (interactive_dir / "toggle-app" / "APP.md").read_text()
    assert "cron: false" in content


def test_set_cron_enabled_enable(interactive_dir):
    create_interactive_app(
        interactive_dir,
        "off-app",
        cron_script="pass",
        app_md="---\ntitle: Off\ncron: false\n---\n",
    )
    assert set_cron_enabled("off-app", True) is True

    content = (interactive_dir / "off-app" / "APP.md").read_text()
    assert "cron: true" in content


def test_set_cron_enabled_nonexistent_app(interactive_dir):
    assert set_cron_enabled("nope", True) is False


def test_set_cron_enabled_adds_field_when_missing(interactive_dir):
    create_interactive_app(
        interactive_dir,
        "no-field",
        cron_script="pass",
        app_md="---\ntitle: No Field\n---\n",
    )
    set_cron_enabled("no-field", False)

    content = (interactive_dir / "no-field" / "APP.md").read_text()
    assert "cron: false" in content


def test_set_cron_enabled_roundtrip(interactive_dir):
    create_interactive_app(interactive_dir, "rt-app", cron_script="pass")

    set_cron_enabled("rt-app", False)
    tasks = discover_cron_tasks()
    assert tasks[0]["enabled"] is False

    set_cron_enabled("rt-app", True)
    tasks = discover_cron_tasks()
    assert tasks[0]["enabled"] is True


@pytest.fixture
def s3_cron_env(tmp_path, monkeypatch, db_setup):
    """Simulate an S3-backed server with mocked S3 functions."""
    cron_dir = tmp_path / "cron"
    cron_dir.mkdir()
    interactive_dir = tmp_path / "interactive"
    monkeypatch.setattr(config, "INTERACTIVE_DIR", interactive_dir)
    monkeypatch.setattr(config, "CRON_DIR", cron_dir)
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(config, "S3_BUCKET", "test-bucket")
    return {"cron_dir": cron_dir, "interactive_dir": interactive_dir}


def _seed_dashboard(slug: str, *, has_cron: bool = True, title: str | None = None) -> None:
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(
            Dashboard(
                slug=slug,
                title=title or slug,
                first_author_email="test@x",
                created_in_conversation_id="test",
                has_cron=has_cron,
                is_archived=False,
                has_api_access=False,
                has_persistence=False,
                created_at=now,
                updated_at=now,
            )
        )


def mock_s3_app(slug, cron_script="print('hello')", app_md=None):
    if app_md is None:
        app_md = f"---\ntitle: {slug}\n---\n"
    return {
        "slug": slug,
        "files": {
            f"{slug}/cron.py": cron_script.encode(),
            f"{slug}/APP.md": app_md.encode(),
        },
    }


def make_s3_mocks(apps: list[dict]):
    """Create mock functions for web.s3 that serve the given apps."""
    all_files = {}
    for app in apps:
        all_files.update(app["files"])
    slugs = [app["slug"] for app in apps]

    def mock_list_directories(prefix=""):
        return sorted(slugs)

    def mock_exists(path):
        return path in all_files

    def mock_download(path):
        return all_files.get(path)

    def mock_list_files(prefix=""):
        results = []
        for key, content in all_files.items():
            if key.startswith(prefix):
                results.append({"path": key, "size": len(content), "last_modified": None})
        return results

    def mock_upload(path, content, content_type=None):
        all_files[path] = content
        return True

    return {
        "list_directories": mock_list_directories,
        "exists": mock_exists,
        "download": mock_download,
        "list_files": mock_list_files,
        "upload": mock_upload,
        "_all_files": all_files,
    }


def _patch_s3(mocker, mocks):
    mocker.patch("web.cron.s3.interactive.list_files", side_effect=mocks["list_files"])
    mocker.patch("web.cron.s3.interactive.download", side_effect=mocks["download"])


def _patch_s3_full(mocker, mocks):
    _patch_s3(mocker, mocks)
    mocker.patch("web.cron.s3.interactive.upload", side_effect=mocks["upload"])


def test_discover_s3_apps(mocker, s3_cron_env):
    _seed_dashboard("my-s3-app")
    mocks = make_s3_mocks([mock_s3_app("my-s3-app")])
    _patch_s3(mocker, mocks)
    tasks = discover_cron_tasks()
    assert len(tasks) == 1
    assert tasks[0]["slug"] == "my-s3-app"
    assert tasks[0]["tier"] == "app"


def test_discover_s3_app_skipped_without_cron_py(mocker, s3_cron_env):
    _seed_dashboard("no-cron-app")
    app = mock_s3_app("no-cron-app")
    del app["files"]["no-cron-app/cron.py"]
    mocks = make_s3_mocks([app])
    _patch_s3(mocker, mocks)
    tasks = discover_cron_tasks()
    assert len(tasks) == 0


def test_discover_s3_app_skipped_when_not_in_db(mocker, s3_cron_env):
    mocks = make_s3_mocks([mock_s3_app("ghost-app")])
    _patch_s3(mocker, mocks)
    assert discover_cron_tasks() == []


def test_discover_s3_app_skipped_when_has_cron_false(mocker, s3_cron_env):
    _seed_dashboard("declared-no-cron", has_cron=False)
    mocks = make_s3_mocks([mock_s3_app("declared-no-cron")])
    _patch_s3(mocker, mocks)
    assert discover_cron_tasks() == []


def test_discover_s3_app_metadata_parsed(mocker, s3_cron_env):
    _seed_dashboard("titled-app", title="My S3 App")
    app = mock_s3_app(
        "titled-app",
        app_md="---\ntitle: ignored\ntimeout: 600\nschedule: weekly\n---\n",
    )
    mocks = make_s3_mocks([app])
    _patch_s3(mocker, mocks)
    tasks = discover_cron_tasks()
    assert tasks[0]["title"] == "My S3 App"
    assert tasks[0]["timeout"] == 600
    assert tasks[0]["schedule"] == "weekly"


def test_discover_s3_disabled_app(mocker, s3_cron_env):
    _seed_dashboard("off-app")
    app = mock_s3_app("off-app", app_md="---\ntitle: Off\ncron: false\n---\n")
    mocks = make_s3_mocks([app])
    _patch_s3(mocker, mocks)
    tasks = discover_cron_tasks()
    assert tasks[0]["enabled"] is False


def test_discover_s3_and_system_crons_merged(mocker, s3_cron_env):
    sys_dir = s3_cron_env["cron_dir"] / "sys-task"
    sys_dir.mkdir()
    (sys_dir / "cron.py").write_text("pass")
    (sys_dir / "CRON.md").write_text("---\ntitle: System\n---\n")

    _seed_dashboard("s3-app")
    mocks = make_s3_mocks([mock_s3_app("s3-app")])
    _patch_s3(mocker, mocks)
    tasks = discover_cron_tasks()
    assert len(tasks) == 2
    assert tasks[0]["tier"] == "system"
    assert tasks[0]["slug"] == "sys-task"
    assert tasks[1]["tier"] == "app"
    assert tasks[1]["slug"] == "s3-app"


def test_discover_s3_multiple_apps_sorted(mocker, s3_cron_env):
    _seed_dashboard("zeta-app")
    _seed_dashboard("alpha-app")
    mocks = make_s3_mocks([
        mock_s3_app("zeta-app"),
        mock_s3_app("alpha-app"),
    ])
    _patch_s3(mocker, mocks)
    tasks = discover_cron_tasks()
    assert [t["slug"] for t in tasks] == ["alpha-app", "zeta-app"]


def test_discover_lists_bucket_once_regardless_of_dashboard_count(mocker, s3_cron_env):
    for slug in ("a-app", "b-app", "c-app"):
        _seed_dashboard(slug)
    mocks = make_s3_mocks([mock_s3_app(s) for s in ("a-app", "b-app", "c-app")])
    list_files = mocker.patch("web.cron.s3.interactive.list_files", side_effect=mocks["list_files"])
    mocker.patch("web.cron.s3.interactive.download", side_effect=mocks["download"])

    tasks = discover_cron_tasks()

    assert len(tasks) == 3
    assert list_files.call_count == 1


def test_run_all_does_not_rediscover_per_task(mocker, s3_cron_env):
    for slug in ("one-app", "two-app"):
        _seed_dashboard(slug)
    mocks = make_s3_mocks([mock_s3_app(s) for s in ("one-app", "two-app")])
    _patch_s3_full(mocker, mocks)
    find_task = mocker.spy(cron, "find_task")

    results = run_all(dry_run=False)

    assert {r["slug"] for r in results} == {"one-app", "two-app"}
    assert find_task.call_count == 0


def test_run_s3_executes_script(mocker, s3_cron_env):
    _seed_dashboard("s3-runner")
    app = mock_s3_app("s3-runner", cron_script="print('s3 hello')")
    mocks = make_s3_mocks([app])
    _patch_s3_full(mocker, mocks)
    result = run_cron_task("s3-runner", trigger="manual")
    assert result["status"] == "success"
    assert "s3 hello" in result["output"]


def test_run_s3_script_failure(mocker, s3_cron_env):
    _seed_dashboard("s3-fail")
    app = mock_s3_app("s3-fail", cron_script="import sys; sys.exit(1)")
    mocks = make_s3_mocks([app])
    _patch_s3_full(mocker, mocks)
    result = run_cron_task("s3-fail", trigger="manual")
    assert result["status"] == "failure"


def test_run_s3_script_uploads_output(mocker, s3_cron_env):
    _seed_dashboard("s3-writer")
    script = textwrap.dedent("""\
        import json
        from pathlib import Path
        Path("data.json").write_text(json.dumps({"updated": True}))
        print("done")
    """)
    app = mock_s3_app("s3-writer", cron_script=script)
    mocks = make_s3_mocks([app])
    _patch_s3_full(mocker, mocks)
    result = run_cron_task("s3-writer", trigger="manual")
    assert result["status"] == "success"
    assert "s3-writer/data.json" in mocks["_all_files"]
    uploaded = json.loads(mocks["_all_files"]["s3-writer/data.json"])
    assert uploaded["updated"] is True


def test_run_s3_script_has_pythonpath(mocker, s3_cron_env):
    _seed_dashboard("s3-path")
    script = textwrap.dedent("""\
        import sys
        print(sys.path)
    """)
    app = mock_s3_app("s3-path", cron_script=script)
    mocks = make_s3_mocks([app])
    _patch_s3_full(mocker, mocks)
    result = run_cron_task("s3-path", trigger="manual")
    assert result["status"] == "success"
    assert str(config.BASE_DIR) in result["output"]


@pytest.mark.parametrize(
    "status,previous,should_notify",
    [
        ("failure", "success", True),
        ("timeout", "success", True),
        ("failure", None, True),
        ("failure", "failure", False),
        ("timeout", "failure", False),
        ("success", "failure", True),
        ("success", "timeout", True),
        ("success", "success", False),
        ("success", None, False),
    ],
)
def test_cron_alert_fires_only_on_status_change(mocker, status, previous, should_notify):
    notify = mocker.patch("web.cron.alerts.notify_alert_channel")

    notify_cron_status_change("my-app", status, previous, "some output")

    assert notify.called == should_notify


def test_cron_alert_message_distinguishes_break_and_recovery(mocker):
    notify = mocker.patch("web.cron.alerts.notify_alert_channel")

    notify_cron_status_change("my-app", "failure", "success", "stacktrace here")
    broken_msg = notify.call_args[0][0]
    assert "my-app" in broken_msg
    assert "stacktrace here" in broken_msg

    notify_cron_status_change("my-app", "success", "failure", "")
    recovered_msg = notify.call_args[0][0]
    assert "my-app" in recovered_msg
    assert recovered_msg != broken_msg


def test_run_cron_scheduled_failure_triggers_alert(interactive_dir, db_setup, mocker):
    create_interactive_app(interactive_dir, "bad-app", cron_script="import sys; sys.exit(1)")
    notify = mocker.patch("web.cron.notify_cron_status_change")

    run_cron_task("bad-app", trigger="scheduled")

    notify.assert_called_once()
    slug, status, previous, _output = notify.call_args[0]
    assert slug == "bad-app"
    assert status == "failure"
    assert previous is None


def test_run_cron_manual_run_does_not_alert(interactive_dir, db_setup, mocker):
    create_interactive_app(interactive_dir, "bad-app", cron_script="import sys; sys.exit(1)")
    notify = mocker.patch("web.cron.notify_cron_status_change")

    run_cron_task("bad-app", trigger="manual")

    notify.assert_not_called()


def test_cron_alert_snippet_escapes_triple_backticks(mocker):
    notify = mocker.patch("web.cron.alerts.notify_alert_channel")

    notify_cron_status_change("my-app", "failure", "success", "before ``` after")

    sent = notify.call_args[0][0]
    assert sent.count("```") == 2
    assert "ʼʼʼ" in sent


def test_run_all_emits_task_log_with_typed_duration(mocker, caplog):
    import logging

    mocker.patch(
        "web.cron.discover_cron_tasks",
        return_value=[
            {
                "slug": "my-task",
                "enabled": True,
                "schedule": "daily",
                "timeout": 60,
                "cron_path": "/x",
                "tier": "app",
            }
        ],
    )
    mocker.patch("web.cron.is_due", return_value=True)
    mocker.patch(
        "web.cron.execute_task",
        return_value={"slug": "my-task", "status": "success", "duration_ms": 1234, "output": ""},
    )

    with caplog.at_level(logging.INFO, logger="web.cron"):
        run_all(dry_run=False)

    matches = [r for r in caplog.records if r.message == "cron.task"]
    assert len(matches) == 1
    record = matches[0]
    assert getattr(record, "cron.task.name") == "my-task"
    assert getattr(record, "cron.task.status") == "success"
    assert getattr(record, "cron.task.duration") == 1234


def _seed_dashboard_and_publication(slug, pub_id, *, snapshot_has_cron=True, unpublished=False, paused=False):
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(
            Dashboard(
                slug=slug,
                title=f"Title for {slug}",
                description="d",
                website="emplois",
                category="c",
                first_author_email="alice@x",
                is_archived=False,
                has_api_access=False,
                has_cron=False,
                has_persistence=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            DashboardPublication(
                dashboard_slug=slug,
                publication_id=pub_id,
                environment="staging",
                published_by="bob@x",
                published_at=now,
                snapshot_has_cron=snapshot_has_cron,
                unpublished_at=now if unpublished else None,
                refresh_paused_at=now if paused else None,
            )
        )


@pytest.mark.parametrize(
    "snapshot_has_cron,unpublished,paused,included",
    [
        (True, False, False, True),
        (False, False, False, False),
        (True, True, False, False),
        (True, False, True, False),
    ],
)
def test_discover_publications_filters(client, mocker, snapshot_has_cron, unpublished, paused, included):
    from web.cron import discover_publications

    slug = f"disco-{int(snapshot_has_cron)}-{int(unpublished)}-{int(paused)}"
    pub_id = "discp1"
    _seed_dashboard_and_publication(
        slug,
        pub_id,
        snapshot_has_cron=snapshot_has_cron,
        unpublished=unpublished,
        paused=paused,
    )
    mocker.patch("web.cron.s3.publications.download", return_value=b"---\ntitle: x\n---\n")

    tasks = discover_publications()
    slugs = [t["slug"] for t in tasks]
    assert (f"{slug}-{pub_id}" in slugs) is included


def test_discover_publications_task_dict_shape(client, mocker):
    from web.cron import discover_publications

    _seed_dashboard_and_publication("shape-tdb", "shape1")
    mocker.patch(
        "web.cron.s3.publications.download",
        return_value=b"---\ntitle: Shape\nschedule: weekly\ntimeout: 600\n---\n",
    )

    tasks = discover_publications()
    assert len(tasks) == 1
    task = tasks[0]
    assert task["slug"] == "shape-tdb-shape1"
    assert task["source"] == "s3-publication"
    assert task["tier"] == "publication"
    assert task["path"] == "shape-tdb/shape1/"
    assert task["cron_path"] == "shape-tdb/shape1/cron.py"
    assert task["dashboard_slug"] == "shape-tdb"
    assert task["publication_id"] == "shape1"
    assert task["schedule"] == "weekly"
    assert task["timeout"] == 600
    assert task["enabled"] is True


def test_run_cron_task_dispatches_publication_source_and_refreshes(client, mocker):
    """Subprocess rc=0 → upload to snapshot + publications.refresh() → last_refresh_status=success."""
    import subprocess as sp

    from web.cron import run_cron_task

    _seed_dashboard_and_publication("dispatch-tdb", "disp01")
    mocker.patch("web.cron.s3.publications.download", return_value=b"---\ntitle: D\n---\n")
    mocker.patch("web.cron.s3.publications.list_files", return_value=[])
    mocker.patch("web.cron.s3.publications.upload", return_value=True)
    sync = mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.alerts.notify_alert_channel")

    completed = sp.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
    mocker.patch("web.cron.subprocess.run", return_value=completed)

    result = run_cron_task("dispatch-tdb-disp01", trigger="manual")
    assert result["status"] == "success"
    assert sync.called
    with get_db() as session:
        row = session.scalar(select(DashboardPublication).where(DashboardPublication.publication_id == "disp01"))
        assert row.last_refresh_status == "success"


def test_run_cron_task_publication_no_refresh_on_subprocess_failure(client, mocker):
    import subprocess as sp

    from web.cron import run_cron_task

    _seed_dashboard_and_publication("fail-tdb", "fail01")
    mocker.patch("web.cron.s3.publications.download", return_value=b"---\ntitle: F\n---\n")
    mocker.patch("web.cron.s3.publications.list_files", return_value=[])
    sync = mocker.patch("web.publications.s3.sync_prefix")
    completed = sp.CompletedProcess(args=[], returncode=1, stdout="boom", stderr="")
    mocker.patch("web.cron.subprocess.run", return_value=completed)

    result = run_cron_task("fail-tdb-fail01", trigger="manual")
    assert result["status"] == "failure"
    sync.assert_not_called()
    with get_db() as session:
        row = session.scalar(select(DashboardPublication).where(DashboardPublication.publication_id == "fail01"))
        assert row.last_refresh_status is None


def test_run_cron_task_publication_two_states_independent(client, mocker):
    """Cron succeeds, public re-push fails → cron_runs.status='success' AND last_refresh_status='failure'."""
    import subprocess as sp

    from botocore.exceptions import ClientError

    from web.cron import run_cron_task
    from web.models import CronRun

    _seed_dashboard_and_publication("two-tdb", "two001")
    mocker.patch("web.cron.s3.publications.download", return_value=b"---\ntitle: T\n---\n")
    mocker.patch("web.cron.s3.publications.list_files", return_value=[])
    err = ClientError({"Error": {"Code": "AccessDenied", "Message": "x"}}, "PutObject")
    mocker.patch("web.publications.s3.sync_prefix", side_effect=err)
    notify = mocker.patch("web.publications.alerts.notify_alert_channel")
    completed = sp.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
    mocker.patch("web.cron.subprocess.run", return_value=completed)

    result = run_cron_task("two-tdb-two001", trigger="manual")
    assert result["status"] == "success"
    with get_db() as session:
        run = session.scalar(select(CronRun).where(CronRun.app_slug == "two-tdb-two001").order_by(CronRun.id.desc()))
        assert run.status == "success"
        row = session.scalar(select(DashboardPublication).where(DashboardPublication.publication_id == "two001"))
        assert row.last_refresh_status == "failure"
    assert notify.called
