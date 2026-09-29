"""Un lot tué (SIGKILL, OOM) laisse une trace : marqueur de lot et ligne `running` par tâche."""

import itertools
import textwrap
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text

from web import cron
from web.db import get_db
from web.helpers import utcnow
from web.models import CronBatchRun, CronRun

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


def truncate_runs():
    with get_db() as session:
        session.execute(text("TRUNCATE TABLE cron_runs, cron_batch_runs CASCADE"))


@pytest.fixture(autouse=True)
def clean_tables():
    truncate_runs()
    yield
    truncate_runs()


def batch_statuses(batch):
    with get_db() as session:
        return session.scalars(
            select(CronBatchRun.status).where(CronBatchRun.batch == batch).order_by(CronBatchRun.id)
        ).all()


def run_statuses():
    with get_db() as session:
        return dict(session.execute(select(CronRun.app_slug, CronRun.status)).all())


def killed_during(batch, slug):
    """Un lot qui démarre une tâche puis meurt sans rien écrire d'autre."""
    batch_run_id = cron.open_batch_run(batch)
    cron.open_run(slug, utcnow(), "scheduled", batch_run_id)


def write_system_task(tmp_path, slug, body):
    script = tmp_path / slug / "cron.py"
    script.parent.mkdir()
    script.write_text(textwrap.dedent(body))
    return {
        "slug": slug,
        "title": slug,
        "tier": "system",
        "source": None,
        "path": str(script.parent),
        "cron_path": str(script),
        "enabled": True,
        "timeout": 30,
        "schedule": "daily",
        "batch": "maintenance",
    }


def test_the_next_run_of_a_killed_batch_marks_it_and_its_task_interrupted(mocker):
    mocker.patch.object(cron.alerts, "notify_alert_channel")
    killed_during("tableaux", "tdb-x")

    cron.open_batch_run("tableaux")

    assert batch_statuses("tableaux") == ["interrupted", "running"]
    assert run_statuses() == {"tdb-x": "interrupted"}


def test_a_batch_never_closes_the_run_of_another_batch(mocker):
    mocker.patch.object(cron.alerts, "notify_alert_channel")
    killed_during("tableaux", "tdb-x")

    cron.open_batch_run("xl")

    assert batch_statuses("tableaux") == ["running"]
    assert run_statuses() == {"tdb-x": "running"}


def test_slack_hears_of_an_interruption_once_then_of_the_recovery(mocker):
    notify = mocker.patch.object(cron.alerts, "notify_alert_channel")

    killed_during("tableaux", "tdb-x")
    killed_during("tableaux", "tdb-y")
    killed_during("tableaux", "tdb-z")
    cron.close_batch_run(cron.open_batch_run("tableaux"), "finished")
    cron.close_batch_run(cron.open_batch_run("tableaux"), "finished")

    messages = [call.args[0] for call in notify.call_args_list]
    assert len(messages) == 2
    assert "interrompu" in messages[0] and "`tdb-x`" in messages[0]
    assert "rétabli" in messages[1]


def test_a_batch_run_to_its_end_is_recorded_with_its_tasks(mocker, tmp_path):
    mocker.patch.object(cron.sentry_sdk.crons.api, "capture_checkin", return_value="cid")
    task = write_system_task(tmp_path, "sys-ok", "print('ok')")
    mocker.patch.object(cron, "discover_cron_tasks", return_value=[task])
    mocker.patch.object(cron, "is_due", return_value=True)

    cron.run_all(batch="maintenance")

    assert batch_statuses("maintenance") == ["finished"]
    with get_db() as session:
        batch_run_id, run_batch_id = session.execute(
            select(CronBatchRun.id, CronRun.batch_run_id).join(CronRun, CronRun.batch_run_id == CronBatchRun.id)
        ).one()
    assert run_batch_id == batch_run_id
    assert run_statuses() == {"sys-ok": "success"}


def test_a_batch_over_its_budget_still_reaches_its_end(mocker):
    mocker.patch.object(cron, "discover_cron_tasks", return_value=[write_task_stub("a"), write_task_stub("b")])
    mocker.patch.object(cron, "is_due", return_value=True)
    mocker.patch.object(cron.alerts, "notify_alert_channel")
    mocker.patch.object(cron.sentry_sdk.crons.api, "capture_checkin", return_value="cid")
    mocker.patch.object(cron.time, "monotonic", side_effect=itertools.count(0, 100))

    cron.run_all(batch="maintenance", budget=10)

    assert batch_statuses("maintenance") == ["over_budget"]


def write_task_stub(slug):
    return {"slug": slug, "enabled": True, "schedule": "daily", "timeout": 60, "batch": "maintenance"}


def test_a_task_shows_as_running_while_it_runs(mocker, tmp_path):
    mocker.patch.object(cron.sentry_sdk.crons.api, "capture_checkin", return_value="cid")
    seen = {}

    def spy(*args, **kwargs):
        seen.update(run_statuses())
        return 0, "", ""

    mocker.patch.object(cron, "run_task_process", side_effect=spy)

    cron.execute_task(write_system_task(tmp_path, "sys-slow", "print('ok')"), trigger="manual")

    assert seen == {"sys-slow": "running"}
    assert run_statuses() == {"sys-slow": "success"}


def test_a_task_that_raises_closes_its_own_running_row(mocker):
    mocker.patch.object(cron.sentry_sdk.crons.api, "capture_checkin", return_value="cid")
    mocker.patch.object(cron, "prepare_s3_workdir", side_effect=RuntimeError("bug"))
    task = {**write_task_stub("tdb-x"), "source": "s3", "tier": "app"}

    result = cron.execute_task(task, trigger="manual")

    assert result["status"] == "failure"
    with get_db() as session:
        assert session.execute(select(CronRun.status)).scalars().all() == ["failure"]


def test_a_scheduled_success_after_a_failure_still_announces_the_recovery(mocker, tmp_path):
    mocker.patch.object(cron.sentry_sdk.crons.api, "capture_checkin", return_value="cid")
    notify = mocker.patch.object(cron, "notify_cron_status_change")
    task = write_system_task(tmp_path, "sys-back", "print('ok')")
    cron.record_run(
        {
            "slug": "sys-back",
            "status": "failure",
            "output": "",
            "duration_ms": 1,
            "started_at": utcnow() - timedelta(days=1),
            "finished_at": utcnow() - timedelta(days=1),
        },
        "scheduled",
    )

    cron.execute_task(task)

    assert notify.call_args.args[:3] == ("sys-back", "success", "failure")


@pytest.mark.parametrize(
    "age,expected",
    [(timedelta(seconds=10), "running"), (timedelta(hours=2), "interrupted")],
)
def test_a_running_row_older_than_its_timeout_reads_as_interrupted(age, expected):
    run = {"status": "running", "started_at": utcnow() - age}

    assert cron.displayed_status(run, timeout=60) == expected


def record_past_run(slug, status, started_at, trigger="scheduled"):
    cron.record_run(
        {
            "slug": slug,
            "status": status,
            "output": "",
            "duration_ms": 1,
            "started_at": started_at,
            "finished_at": started_at,
        },
        trigger,
    )


TUESDAY = datetime(2026, 9, 29, 6, 5, tzinfo=timezone.utc)
MONDAY_BATCH = datetime(2026, 9, 28, 6, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("history", "expected"),
    [
        ([], True),
        ([("interrupted", MONDAY_BATCH, "scheduled")], True),
        ([("skipped", MONDAY_BATCH, "scheduled")], True),
        ([("success", MONDAY_BATCH - timedelta(days=7), "scheduled")], True),
        ([("success", MONDAY_BATCH, "scheduled")], False),
        ([("failure", MONDAY_BATCH, "scheduled")], False),
        ([("timeout", MONDAY_BATCH, "scheduled")], False),
        ([("success", MONDAY_BATCH + timedelta(hours=5), "manual")], False),
    ],
)
def test_a_weekly_task_catches_up_when_monday_never_really_ran_it(mocker, history, expected):
    mocker.patch.object(cron, "utcnow", return_value=TUESDAY)
    for status, started_at, trigger in history:
        record_past_run("hebdo", status, started_at, trigger)

    assert cron.missed_last_due({"slug": "hebdo", "schedule": "weekly"}, "tableaux") is expected


def test_the_next_batch_runs_a_weekly_task_whose_monday_was_missed(mocker, tmp_path):
    mocker.patch.object(cron, "utcnow", return_value=TUESDAY)
    mocker.patch.object(cron.sentry_sdk.crons.api, "capture_checkin", return_value="cid")
    task = {**write_system_task(tmp_path, "hebdo", "print('ok')"), "schedule": "weekly"}
    mocker.patch.object(cron, "discover_cron_tasks", return_value=[task])

    results = cron.run_all(batch="maintenance")

    assert [r["slug"] for r in results] == ["hebdo"]


def test_the_history_purge_empties_old_outputs_then_drops_year_old_rows(mocker):
    now = datetime(2026, 9, 29, 6, 0, tzinfo=timezone.utc)
    mocker.patch.object(cron, "utcnow", return_value=now)
    for slug, age in [("recent", 29), ("old", 31), ("ancient", 366)]:
        cron.record_run(
            {
                "slug": slug,
                "status": "success",
                "output": "sortie",
                "duration_ms": 1,
                "started_at": now - timedelta(days=age),
                "finished_at": now - timedelta(days=age),
            },
            "scheduled",
        )
    with get_db() as session:
        session.add(CronBatchRun(batch="tableaux", started_at=now - timedelta(days=366), status="finished"))
        session.add(CronBatchRun(batch="tableaux", started_at=now - timedelta(days=364), status="finished"))

    cron.purge_cron_history()

    with get_db() as session:
        assert dict(session.execute(select(CronRun.app_slug, CronRun.output)).all()) == {
            "recent": "sortie",
            "old": None,
        }
        assert session.scalar(select(func.count()).select_from(CronBatchRun)) == 1


def test_the_history_purge_runs_every_day_in_the_maintenance_batch():
    tasks = {task["slug"]: task for task in cron.discover_from_dir(cron.config.CRON_DIR, "CRON.md", "system")}

    assert (tasks["purge-cron-history"]["batch"], tasks["purge-cron-history"]["schedule"]) == ("maintenance", "daily")
