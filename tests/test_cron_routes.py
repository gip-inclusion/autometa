"""Tests for cron route slug validation — guards against path-injection in downstream tempfile/S3 keys."""

from datetime import datetime, timedelta, timezone

import pytest
from botocore.exceptions import ClientError

from web import cron, scalingo
from web.db import get_db
from web.helpers import format_future_date

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

S3_DOWN = ClientError({"Error": {"Code": "ServiceUnavailable", "Message": "x"}}, "ListObjectsV2")


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/cron/{slug}/run"),
        ("post", "/api/cron/{slug}/toggle"),
        ("get", "/api/cron/{slug}/script"),
        ("get", "/api/cron/{slug}/logs"),
    ],
)
@pytest.mark.parametrize(
    "bad_slug",
    [
        "foo..bar",
        "UPPER",
        "with.dot",
        "with$dollar",
        "with%20encoded",
        "a" * 101,
    ],
)
def test_invalid_slug_rejected(client, method, path, bad_slug):
    response = getattr(client, method)(path.format(slug=bad_slug))
    assert response.status_code == 422


def test_valid_slug_reaches_handler(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value=None)
    response = client.get("/api/cron/check-s3-backups/script")
    assert response.status_code == 404
    assert response.json() == {"error": "Task not found"}


def test_view_script_s3_task(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value={"slug": "x", "source": "s3", "cron_path": "x/cron.py"})
    mocker.patch("web.routes.cron.read_cron_script", return_value="print('hi')")
    response = client.get("/api/cron/x/script")
    assert response.status_code == 200
    assert "print('hi')" in response.text


def test_view_script_missing_returns_404_not_500(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value={"slug": "x", "source": "s3", "cron_path": "x/cron.py"})
    mocker.patch("web.routes.cron.read_cron_script", return_value=None)
    response = client.get("/api/cron/x/script")
    assert response.status_code == 404


def test_read_cron_script_local(tmp_path):
    script = tmp_path / "cron.py"
    script.write_text("print('local')")
    assert cron.read_cron_script({"cron_path": str(script)}) == "print('local')"


def test_read_cron_script_s3(mocker):
    mocker.patch("web.cron.s3.interactive.download", return_value=b"print('s3')")
    assert cron.read_cron_script({"source": "s3", "cron_path": "x/cron.py"}) == "print('s3')"


def test_a_manual_run_of_an_unknown_task_returns_404(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value=None)

    response = client.post("/api/cron/ghost/run")

    assert response.status_code == 404
    assert response.json() == {"error": "Task not found"}


def test_a_manual_run_is_delegated_to_a_dedicated_container(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value={"slug": "tdb1", "source": "s3"})
    mocker.patch("web.routes.cron.scalingo.is_configured", return_value=True)
    start = mocker.patch("web.routes.cron.scalingo.start_one_off", return_value="ctr-42")
    execute = mocker.patch("web.cron.run_task_and_publications")

    response = client.post("/api/cron/tdb1/run")

    assert response.status_code == 202
    assert response.json()["container"] == "ctr-42"
    assert start.call_args.args[0] == "python -m web.cron --app tdb1"
    execute.assert_not_called()


def test_a_manual_run_says_so_when_scalingo_is_not_configured(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value={"slug": "tdb1", "source": "s3"})
    mocker.patch("web.routes.cron.scalingo.is_configured", return_value=False)

    response = client.post("/api/cron/tdb1/run")

    assert response.status_code == 503
    assert "ligne de commande" in response.json()["error"]


def test_a_manual_run_reports_a_refused_container(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value={"slug": "tdb1", "source": "s3"})
    mocker.patch("web.routes.cron.scalingo.is_configured", return_value=True)
    mocker.patch("web.routes.cron.scalingo.start_one_off", side_effect=scalingo.ScalingoError("refus"))

    assert client.post("/api/cron/tdb1/run").status_code == 502


def test_cron_page_shows_the_latest_run_of_each_task(client, mocker):
    task = {
        "slug": "nightly",
        "title": "Nightly",
        "tier": "system",
        "enabled": True,
        "schedule": "daily",
        "timeout": 60,
        "batch": "synchros",
    }
    mocker.patch("web.routes.cron.discover_cron_tasks", return_value=[task])
    now = datetime.now(timezone.utc)
    earlier = now - timedelta(hours=1)
    with get_db() as session:
        session.add(
            cron.CronRun(app_slug="nightly", started_at=earlier, status="failure", duration_ms=500, trigger="manual")
        )
        session.add(
            cron.CronRun(app_slug="nightly", started_at=now, status="success", duration_ms=2500, trigger="scheduled")
        )
    response = client.get("/cron")
    assert response.status_code == 200
    assert "(scheduled)" in response.text
    assert "2.5s" in response.text
    assert "(manual)" not in response.text


def test_the_cron_page_shows_a_task_killed_mid_run_as_interrupted(client, mocker):
    task = {
        "slug": "tdb-x",
        "title": "X",
        "tier": "app",
        "enabled": True,
        "schedule": "daily",
        "timeout": 60,
        "batch": "tableaux",
    }
    mocker.patch("web.routes.cron.discover_cron_tasks", return_value=[task])
    with get_db() as session:
        session.add(
            cron.CronRun(
                app_slug="tdb-x",
                started_at=datetime.now(timezone.utc) - timedelta(hours=2),
                status="running",
                trigger="scheduled",
            )
        )

    response = client.get("/cron")

    assert "interrompu" in response.text


def test_the_cron_page_shows_the_last_run_of_each_batch(client, mocker):
    mocker.patch("web.routes.cron.discover_cron_tasks", return_value=[])
    with get_db() as session:
        session.add(
            cron.CronBatchRun(
                batch="tableaux", started_at=datetime.now(timezone.utc) - timedelta(hours=25), status="running"
            )
        )

    response = client.get("/cron")

    assert "Lot <code>tableaux</code>" in response.text
    assert "interrompu" in response.text


def test_the_cron_page_announces_the_next_run_at_the_hour_of_the_task_batch(client, mocker):
    task = {
        "slug": "sync-x",
        "title": "X",
        "tier": "system",
        "enabled": True,
        "schedule": "daily",
        "timeout": 60,
        "batch": "synchros",
    }
    mocker.patch("web.routes.cron.discover_cron_tasks", return_value=[task])

    response = client.get("/cron")

    assert format_future_date(cron.next_cron_run("daily", "synchros")) in response.text


def test_the_cron_page_survives_an_s3_outage(client, mocker):
    mocker.patch("web.routes.cron.discover_cron_tasks", side_effect=S3_DOWN)
    mocker.patch(
        "web.routes.cron.discover_system_tasks",
        return_value=[
            {
                "slug": "sys-task",
                "title": "Sys",
                "tier": "system",
                "enabled": True,
                "schedule": "daily",
                "timeout": 60,
                "batch": "default",
                "cron_path": "/x",
                "path": "/x",
            }
        ],
    )

    response = client.get("/cron")

    assert response.status_code == 200
    assert "sys-task" in response.text
    assert "S3" in response.text


@pytest.mark.parametrize(
    ("method", "path"),
    [("post", "/api/cron/tdb1/run"), ("get", "/api/cron/tdb1/script")],
)
def test_a_route_degrades_instead_of_crashing_when_the_discovery_cannot_reach_s3(client, mocker, method, path):
    # Why: résoudre un slug liste S3. Une secousse rendait un 500 avec traceback là où la page
    # /cron sait déjà se replier — le mode d'échec muet que cette branche referme.
    mocker.patch("web.routes.cron.find_task", side_effect=S3_DOWN)

    response = getattr(client, method)(path)

    assert response.status_code == 503
    assert "S3" in response.json()["error"]
