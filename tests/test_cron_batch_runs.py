"""Un lot tué (SIGKILL, OOM) laisse une trace : marqueur de lot et ligne `running` par tâche."""

import itertools
import textwrap
from datetime import timedelta

import pytest
from sqlalchemy import select, text

from web import cron
from web.db import get_db
from web.helpers import utcnow
from web.models import CronBatchRun, CronRun

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with get_db() as session:
        session.execute(text("TRUNCATE TABLE cron_runs, cron_batch_runs CASCADE"))


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
