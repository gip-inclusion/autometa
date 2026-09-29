"""Robustesse du runner cron face aux pannes : S3, exceptions imprévues, sorties tronquées."""

import ast
import importlib.util
import json
import logging
import os
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from botocore.exceptions import ClientError
from sqlalchemy.exc import OperationalError

from web import cron

S3_DOWN = ClientError({"Error": {"Code": "ServiceUnavailable", "Message": "x"}}, "ListObjectsV2")


@pytest.fixture(autouse=True)
def no_run_markers(mocker):
    """Couloir unit : les marqueurs `running` du lot et des tâches ne touchent pas la base."""
    mocker.patch.object(cron, "open_batch_run", return_value=None)
    mocker.patch.object(cron, "open_run", return_value=None)


def make_task(slug, **overrides):
    return {
        "slug": slug,
        "title": slug,
        "tier": "app",
        "source": "s3",
        "path": slug,
        "cron_path": f"{slug}/cron.py",
        "enabled": True,
        "timeout": 5,
        "schedule": "daily",
        "batch": "maintenance",
        **overrides,
    }


def test_a_system_task_without_a_declared_batch_fails_discovery(tmp_path):
    (tmp_path / "sans-batch").mkdir()
    (tmp_path / "sans-batch" / "cron.py").write_text("print('x')")
    (tmp_path / "sans-batch" / "CRON.md").write_text("---\ntitle: Sans batch\n---\n")

    with pytest.raises(ValueError, match="sans-batch"):
        cron.discover_from_dir(tmp_path, "CRON.md", "system")


def test_dashboards_and_publications_land_in_the_dashboard_batch(mocker):
    mocker.patch.object(cron.config, "S3_BUCKET", "bucket")
    session = mocker.MagicMock()
    session.execute.return_value.all.return_value = [("tdb1", "T1", True, 300, "0 6 * * *")]
    mocker.patch.object(cron, "get_db").return_value.__enter__.return_value = session
    mocker.patch.object(cron.s3.interactive, "list_files", return_value=[{"path": "tdb1/cron.py"}])

    assert [task["batch"] for task in cron.discover_from_s3()] == [cron.DASHBOARD_BATCH]


def test_discover_from_s3_fails_loudly_when_the_listing_fails(mocker):
    mocker.patch.object(cron.config, "S3_BUCKET", "bucket")
    session = mocker.MagicMock()
    session.execute.return_value.all.return_value = [("tdb1", "T1", True, 300, "0 6 * * *")]
    mocker.patch.object(cron, "get_db").return_value.__enter__.return_value = session
    mocker.patch.object(cron.s3._client, "get_paginator").return_value.paginate.side_effect = S3_DOWN

    with pytest.raises(ClientError):
        cron.discover_from_s3()


@pytest.mark.parametrize("error", [RuntimeError("bug"), S3_DOWN])
def test_run_all_runs_every_task_and_records_a_failure_when_one_raises(mocker, error):
    mocker.patch.object(cron, "discover_cron_tasks", return_value=[make_task("a"), make_task("b"), make_task("c")])
    mocker.patch.object(cron.sentry_sdk.crons.api, "capture_checkin", return_value="cid")
    mocker.patch.object(cron, "get_app_runs", return_value=[])
    mocker.patch.object(cron, "notify_cron_status_change")
    record_run = mocker.patch.object(cron, "record_run")
    prepare = mocker.patch.object(cron, "prepare_s3_workdir", side_effect=error)

    results = cron.run_all(batch="maintenance")

    assert prepare.call_count == 3
    assert [r["status"] for r in results] == ["failure"] * 3
    assert [c.args[0]["slug"] for c in record_run.call_args_list] == ["a", "b", "c"]


def test_execute_task_reports_a_failure_and_closes_the_sentry_checkin_when_it_raises(mocker):
    checkin = mocker.patch.object(cron.sentry_sdk.crons.api, "capture_checkin", return_value="cid")
    mocker.patch.object(cron, "prepare_s3_workdir", side_effect=RuntimeError("bug"))
    mocker.patch.object(cron, "record_run")

    result = cron.execute_task(make_task("a"), trigger="manual")

    assert result["status"] == "failure"
    assert checkin.call_args.kwargs["status"] == cron.sentry_sdk.crons.consts.MonitorStatus.ERROR
    assert checkin.call_args.kwargs["check_in_id"] == "cid"


def test_execute_task_records_success_when_the_publication_refresh_fails(mocker, tmp_path):
    mocker.patch.object(cron.sentry_sdk.crons.api, "capture_checkin", return_value="cid")
    (tmp_path / "cron.py").write_text("print('ok')")
    mocker.patch.object(cron, "prepare_s3_workdir", return_value=(tmp_path, {}))
    mocker.patch.object(cron, "upload_s3_results")
    mocker.patch.object(cron.publications, "refresh", side_effect=OperationalError("stmt", {}, Exception("db")))
    record_run = mocker.patch.object(cron, "record_run")
    task = make_task("tdb-pub1", source="s3-publication", dashboard_slug="tdb", publication_id="pub1")

    result = cron.execute_task(task, trigger="manual")

    assert result["status"] == "success"
    assert record_run.call_args.args[0]["status"] == "success"


def test_combine_output_keeps_the_stderr_tail_when_stdout_is_huge():
    output = cron.combine_output("x" * cron.MAX_OUTPUT_SIZE, "noise\n" * 10_000 + "Traceback: boom")

    assert output.endswith("Traceback: boom")
    assert len(output) <= cron.MAX_OUTPUT_SIZE


def test_execute_task_alerts_slack_with_stderr_rather_than_stdout(mocker, tmp_path):
    mocker.patch.object(cron.sentry_sdk.crons.api, "capture_checkin", return_value="cid")
    mocker.patch.object(cron, "get_app_runs", return_value=[])
    mocker.patch.object(cron, "record_run")
    notify = mocker.patch.object(cron, "notify_cron_status_change")
    task = write_task(
        tmp_path,
        """
        import sys
        print("x" * 60_000)
        print("Traceback: boom", file=sys.stderr)
        sys.exit(1)
        """,
    )

    result = cron.execute_task(task)

    assert "Traceback: boom" in result["output"]
    assert notify.call_args.args[3] == "Traceback: boom"


def test_cron_alert_snippet_shows_the_end_of_a_long_error(mocker):
    notify = mocker.patch.object(cron.alerts, "notify_alert_channel")

    cron.notify_cron_status_change("my-app", "failure", "success", "frame\n" * 500 + "ValueError: boom")

    assert "ValueError: boom" in notify.call_args.args[0]


def write_task(tmp_path, body, **overrides):
    script = tmp_path / "cron.py"
    script.write_text(textwrap.dedent(body))
    return make_task("sys", source=None, tier="system", path=str(tmp_path), cron_path=str(script), **overrides)


def run_task_offline(mocker, task, **kwargs):
    mocker.patch.object(cron.sentry_sdk.crons.api, "capture_checkin", return_value="cid")
    mocker.patch.object(cron, "record_run")
    return cron.execute_task(task, trigger="manual", **kwargs)


def test_execute_task_logs_each_line_of_the_task_output(mocker, tmp_path, caplog):
    task = write_task(
        tmp_path,
        """
        import sys
        print("ligne stdout")
        print("ligne stderr", file=sys.stderr)
        """,
    )

    with caplog.at_level(logging.INFO, logger="web.cron"):
        result = run_task_offline(mocker, task)

    logged = {r.getMessage(): getattr(r, "cron.task.stream", None) for r in caplog.records}
    assert logged.get("ligne stdout") == "stdout"
    assert logged.get("ligne stderr") == "stderr"
    assert result["status"] == "success"


def test_execute_task_logs_progress_before_a_timeout_kills_the_task(mocker, tmp_path, caplog):
    task = write_task(
        tmp_path,
        """
        import sys, time
        print("avant le blocage", flush=True)
        time.sleep(30)
        """,
        timeout=1,
    )

    with caplog.at_level(logging.INFO, logger="web.cron"):
        result = run_task_offline(mocker, task)

    assert result["status"] == "timeout"
    assert result["duration_ms"] < 10_000
    assert "avant le blocage" in [r.getMessage() for r in caplog.records]


def test_execute_task_still_stores_both_streams_in_the_run(mocker, tmp_path):
    task = write_task(
        tmp_path,
        """
        import sys
        print("sortie normale")
        print("erreur fatale", file=sys.stderr)
        sys.exit(1)
        """,
    )

    result = run_task_offline(mocker, task)

    assert result["status"] == "failure"
    assert "sortie normale" in result["output"]
    assert "erreur fatale" in result["output"]


def env_for_subprocess():
    # Why: transmission de l'environnement complet au sous-processus, pas une lecture de configuration.
    return dict(os.environ)  # noqa: TID251


def repo_system_tasks():
    return cron.discover_from_dir(cron.config.CRON_DIR, "CRON.md", "system")


def scheduled_batch(command: str) -> str:
    """Le lot d'une ligne de cron.json : la valeur qui suit --batch, jamais le dernier mot brut
    — un --budget en fin de ligne le déplacerait silencieusement."""
    tokens = command.split()
    return tokens[tokens.index("--batch") + 1] if "--batch" in tokens else tokens[-1]


def test_sync_webinaires_is_a_runner_task_so_its_runs_are_recorded():
    assert "sync-webinaires" in {task["slug"] for task in repo_system_tasks()}


def test_no_scalingo_job_schedules_a_task_the_runner_already_owns():
    # Why: le test suppose la convention de cron.json — chaque job passe --batch, jamais le slug
    # nu d'une tâche déjà possédée par le runner.
    jobs = json.loads((Path(cron.config.BASE_DIR) / "cron.json").read_text())["jobs"]
    owned = {task["slug"] for task in repo_system_tasks()}

    assert [job["command"] for job in jobs if scheduled_batch(job["command"]) in owned] == []


PROBE_RUNNER = """
    import os, sys

    from web.cron import run_task_process

    returncode, stdout, _ = run_task_process(
        [sys.executable, sys.argv[1]], sys.argv[2], dict(os.environ), int(sys.argv[3]), "probe"
    )
    print(f"RESULT {returncode} {stdout.strip()}")
    """


def probe_run_task_process(tmp_path, body, timeout):
    """run_task_process joué dans un interpréteur jetable : un gel de la fonction comme un gel de la
    sortie de l'interpréteur se voient alors comme un dépassement de délai, pas comme un test suspendu."""
    (tmp_path / "cron.py").write_text(textwrap.dedent(body))
    (tmp_path / "runner.py").write_text(textwrap.dedent(PROBE_RUNNER))
    return subprocess.run(
        [sys.executable, str(tmp_path / "runner.py"), str(tmp_path / "cron.py"), str(tmp_path), str(timeout)],
        capture_output=True,
        text=True,
        timeout=25,
        check=False,
        env={**env_for_subprocess(), "PYTHONPATH": str(cron.config.BASE_DIR)},
    )


@pytest.mark.parametrize(
    ("body", "timeout", "expected"),
    [
        (
            """
            import subprocess
            subprocess.Popen(['sleep', '40'])
            print('go', flush=True)
            """,
            30,
            "RESULT 0 go",
        ),
        (
            """
            import subprocess, sys, time
            subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(40)'], start_new_session=True)
            print('go', flush=True)
            time.sleep(40)
            """,
            1,
            "RESULT None",
        ),
    ],
    ids=["succes_avec_processus_de_fond", "timeout_avec_descendant_echappe"],
)
def test_run_task_process_never_holds_the_container(tmp_path, body, timeout, expected):
    # Why: deux gels distincts se referment ici. Une tâche qui réussit bien avant son timeout mais
    # laisse un processus d'arrière-plan tenant les tuyaux bloquait `run_task_process` sans fin ; et
    # des threads de drainage non daemon retenaient la sortie de l'interpréteur même après son retour.
    completed = probe_run_task_process(tmp_path, body, timeout)

    assert expected in completed.stdout, completed.stderr


def test_a_task_never_receives_the_scalingo_token(mocker, monkeypatch, tmp_path):
    # Why: le jeton Scalingo autorise `POST /v1/apps/<app>/run`, donc l'exécution de commandes
    # arbitraires sur la production. Les cron.py de tableaux de bord sont écrits par l'agent et
    # stockés sur S3 : aucun diff ne les relit, ils ne doivent jamais le voir passer.
    monkeypatch.setenv("SCALINGO_API_TOKEN", "tk-secret")
    monkeypatch.setenv("CRON_TEMOIN", "transmis")
    task = write_task(
        tmp_path,
        """
        import os
        print(os.environ.get("SCALINGO_API_TOKEN", "absent"))
        print(os.environ.get("CRON_TEMOIN", "perdu"))
        """,
    )

    result = run_task_offline(mocker, task)

    assert "absent" in result["output"]
    assert "tk-secret" not in result["output"]
    assert "transmis" in result["output"]


def test_a_successful_task_takes_its_background_processes_down_with_it(tmp_path):
    # Why: voulu — un processus de fond survivant tiendrait les tuyaux, et le conteneur avec eux.
    # Une tâche n'a rien à laisser tourner après son retour, succès compris.
    pid_file = tmp_path / "child.pid"
    (tmp_path / "cron.py").write_text(
        textwrap.dedent(
            f"""
            import subprocess
            child = subprocess.Popen(['sleep', '40'])
            open({str(pid_file)!r}, 'w').write(str(child.pid))
            """
        )
    )

    returncode, _, _ = cron.run_task_process(
        [sys.executable, str(tmp_path / "cron.py")], str(tmp_path), env_for_subprocess(), 30, "sys"
    )

    assert returncode == 0
    assert not process_alive(int(pid_file.read_text()))


def process_alive(pid):
    for _ in range(50):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        time.sleep(0.1)
    return True


@pytest.mark.parametrize(
    ("batch", "schedule", "timeout", "crontab", "max_runtime"),
    [
        ("synchros", "daily", 300, "0 2 * * *", 6),
        ("maintenance", "daily", 300, "0 6 * * *", 6),
        ("maintenance", "weekly", 600, "0 6 * * 1", 11),
    ],
)
def test_a_task_checks_in_at_the_hour_its_batch_starts(batch, schedule, timeout, crontab, max_runtime):
    # Why: déduire l'heure de la cadence faisait attendre à Sentry un check-in à 06:00 pour des
    # tâches lancées à 02:00 — un missed check-in par jour et par tâche.
    config = cron.sentry_monitor_config({"schedule": schedule, "timeout": timeout, "batch": batch})

    assert config["schedule"]["value"] == crontab
    assert config["max_runtime"] == max_runtime


def test_every_batch_starts_at_the_hour_cron_json_says():
    # Why: BATCH_START n'est vrai que tant qu'il recopie cron.json — sinon Sentry attend le
    # check-in à une heure où plus rien ne tourne.
    jobs = json.loads((Path(cron.config.BASE_DIR) / "cron.json").read_text())["jobs"]
    scheduled = {
        scheduled_batch(job["command"]): (int(job["command"].split()[1]), int(job["command"].split()[0]))
        for job in jobs
    }

    assert cron.BATCH_START == scheduled


def test_a_task_checks_in_at_the_minute_its_batch_starts(monkeypatch):
    monkeypatch.setitem(cron.BATCH_START, "synchros", (2, 30))

    assert (
        cron.sentry_monitor_config({"schedule": "daily", "timeout": 300, "batch": "synchros"})["schedule"]["value"]
        == "30 2 * * *"
    )
    assert cron.batch_monitor_config("synchros", [], None)["schedule"]["value"] == "30 2 * * *"


UTC = timezone.utc


@pytest.mark.parametrize(
    ("schedule", "batch", "now", "expected"),
    [
        ("daily", "synchros", datetime(2026, 9, 29, 2, 5, tzinfo=UTC), True),
        ("weekly", "tableaux", datetime(2026, 9, 28, 6, 5, tzinfo=UTC), True),
        ("weekly", "tableaux", datetime(2026, 9, 29, 6, 5, tzinfo=UTC), False),
        # Why: dimanche 23:30 UTC, c'est déjà lundi à Paris — le lot de dimanche ne doit rien y voir.
        ("weekly", "synchros", datetime(2026, 9, 27, 23, 30, tzinfo=UTC), False),
        # Why: un lot parti lundi et qui déborde après minuit reste le lot du lundi.
        ("weekly", "tableaux", datetime(2026, 9, 29, 0, 30, tzinfo=UTC), True),
        ("monthly", "tableaux", datetime(2026, 10, 1, 6, 10, tzinfo=UTC), True),
        ("monthly", "tableaux", datetime(2026, 10, 2, 0, 30, tzinfo=UTC), True),
        ("monthly", "synchros", datetime(2026, 9, 30, 23, 0, tzinfo=UTC), False),
    ],
)
def test_a_task_is_due_on_the_utc_day_its_batch_started(mocker, schedule, batch, now, expected):
    mocker.patch.object(cron, "utcnow", return_value=now)

    assert cron.is_due(schedule, batch) is expected


@pytest.mark.parametrize(
    ("schedule", "batch", "now", "expected"),
    [
        ("daily", "synchros", datetime(2026, 9, 28, 1, 0, tzinfo=UTC), datetime(2026, 9, 28, 2, 0, tzinfo=UTC)),
        ("daily", "synchros", datetime(2026, 9, 28, 2, 0, tzinfo=UTC), datetime(2026, 9, 29, 2, 0, tzinfo=UTC)),
        ("daily", "tableaux", datetime(2026, 9, 28, 3, 0, tzinfo=UTC), datetime(2026, 9, 28, 6, 0, tzinfo=UTC)),
        ("weekly", "synchros", datetime(2026, 9, 28, 3, 0, tzinfo=UTC), datetime(2026, 10, 5, 2, 0, tzinfo=UTC)),
        ("monthly", "synchros", datetime(2026, 12, 15, 3, 0, tzinfo=UTC), datetime(2027, 1, 1, 2, 0, tzinfo=UTC)),
    ],
)
def test_the_next_run_starts_at_the_utc_hour_of_the_task_batch(schedule, batch, now, expected):
    assert cron.next_cron_run(schedule, batch, now=now) == expected


def test_a_task_emitting_non_utf8_bytes_does_not_derail_the_run(mocker, tmp_path):
    task = write_task(
        tmp_path,
        """
        import sys
        sys.stdout.buffer.write(b"octets \\xff\\xfe bruts\\n")
        sys.stdout.flush()
        """,
    )

    result = run_task_offline(mocker, task)

    assert result["status"] == "success"
    assert "bruts" in result["output"]


@pytest.mark.parametrize(
    "error", [ClientError({"Error": {"Code": "X", "Message": "m" * 80_000}}, "Op"), RuntimeError("m" * 80_000)]
)
def test_an_enormous_exception_message_is_truncated_before_reaching_the_database(mocker, error):
    mocker.patch.object(cron, "discover_cron_tasks", return_value=[make_task("a")])
    mocker.patch.object(cron.sentry_sdk.crons.api, "capture_checkin", return_value="cid")
    mocker.patch.object(cron, "get_app_runs", return_value=[])
    mocker.patch.object(cron, "notify_cron_status_change")
    mocker.patch.object(cron, "prepare_s3_workdir", side_effect=error)
    record_run = mocker.patch.object(cron, "record_run")

    cron.run_all(batch="maintenance")

    assert len(record_run.call_args.args[0]["output"]) <= cron.MAX_OUTPUT_SIZE


def test_the_run_keeps_the_end_of_both_streams(mocker, tmp_path):
    task = write_task(
        tmp_path,
        """
        import sys
        for i in range(5_000):
            print(f"bavardage numero {i:05d}")
        print("DERNIERE LIGNE STDOUT")
        for i in range(2_000):
            print(f"bruit numero {i:05d}", file=sys.stderr)
        print("DERNIERE LIGNE STDERR", file=sys.stderr)
        """,
    )

    result = run_task_offline(mocker, task)

    assert "DERNIERE LIGNE STDOUT" in result["output"]
    assert "DERNIERE LIGNE STDERR" in result["output"]


def test_combine_output_never_exceeds_the_budget_whatever_the_budget(mocker):
    mocker.patch.object(cron, "MAX_OUTPUT_SIZE", 20)

    assert len(cron.combine_output("s" * 500, "e" * 500)) <= 20


def test_a_task_that_floods_its_output_does_not_flood_the_logs(mocker, tmp_path, caplog):
    mocker.patch.object(cron, "MAX_LOGGED_LINES", 50)
    task = write_task(
        tmp_path,
        """
        for i in range(400):
            print(f"ligne {i}")
        """,
    )

    with caplog.at_level(logging.INFO, logger="web.cron"):
        run_task_offline(mocker, task)

    streamed = [r for r in caplog.records if getattr(r, "cron.task.stream", None) == "stdout"]
    assert len(streamed) <= 51
    assert any("350" in r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)


def test_a_manual_run_that_raises_still_records_a_failed_run(mocker):
    mocker.patch.object(cron, "find_task", return_value=make_task("a"))
    mocker.patch.object(cron, "execute_task", side_effect=RuntimeError("bug"))
    record_run = mocker.patch.object(cron, "record_run")

    result = cron.run_cron_task("a", trigger="manual")

    assert result["status"] == "failure"
    assert record_run.call_args.args[0]["slug"] == "a"


def test_a_manual_run_records_a_failure_when_the_discovery_cannot_reach_s3(mocker):
    # Why: la découverte liste S3 ; hors de tout try, une secousse faisait exploser le conteneur
    # avec une traceback et aucune ligne en base — l'utilisateur n'aurait jamais rien vu revenir.
    mocker.patch.object(cron, "find_task", side_effect=S3_DOWN)
    record_run = mocker.patch.object(cron, "record_run")

    result = cron.run_cron_task("tdb1", trigger="manual")

    assert result["status"] == "failure"
    assert record_run.call_args.args[0]["slug"] == "tdb1"


def test_a_manual_run_of_a_dashboard_still_records_a_failure_when_s3_is_down(mocker):
    mocker.patch.object(cron, "find_task", side_effect=S3_DOWN)
    list_pubs = mocker.patch.object(cron, "list_publications")
    record_run = mocker.patch.object(cron, "record_run")

    results = cron.run_task_and_publications("tdb1")

    assert [result["status"] for result in results] == ["failure"]
    assert list_pubs.called is False
    assert record_run.called


def test_a_manual_run_of_a_dashboard_also_refreshes_its_eligible_publications(mocker):
    mocker.patch.object(cron, "find_task", return_value=make_task("tdb1"))
    mocker.patch.object(
        cron,
        "list_publications",
        return_value=[
            {"publication_id": "pub1", "snapshot_has_cron": True, "refresh_paused_at": None},
            {"publication_id": "pub2", "snapshot_has_cron": False, "refresh_paused_at": None},
            {"publication_id": "pub3", "snapshot_has_cron": True, "refresh_paused_at": "2026-01-01"},
        ],
    )
    run = mocker.patch.object(cron, "run_cron_task", return_value={"slug": "x", "status": "success", "duration_ms": 1})

    results = cron.run_task_and_publications("tdb1")

    assert [call.args[0] for call in run.call_args_list] == ["tdb1", "tdb1-pub1"]
    assert len(results) == 2


def test_a_system_task_does_not_look_up_publications(mocker):
    mocker.patch.object(cron, "find_task", return_value=make_task("sys", source=None))
    list_pubs = mocker.patch.object(cron, "list_publications")
    mocker.patch.object(cron, "run_cron_task", return_value={"slug": "sys", "status": "success", "duration_ms": 1})

    results = cron.run_task_and_publications("sys")

    assert list_pubs.called is False
    assert len(results) == 1


def test_a_publication_composite_does_not_recurse_into_its_own_publications(mocker):
    mocker.patch.object(
        cron, "find_task", return_value=make_task("tdb1-pub1", source="s3-publication", dashboard_slug="tdb1")
    )
    list_pubs = mocker.patch.object(cron, "list_publications")
    mocker.patch.object(
        cron, "run_cron_task", return_value={"slug": "tdb1-pub1", "status": "success", "duration_ms": 1}
    )

    results = cron.run_task_and_publications("tdb1-pub1")

    assert list_pubs.called is False
    assert len(results) == 1


def test_an_unknown_slug_still_returns_one_failing_result(mocker):
    mocker.patch.object(cron, "find_task", return_value=None)
    run = mocker.patch.object(
        cron, "run_cron_task", return_value={"slug": "ghost", "status": "failure", "duration_ms": 0}
    )

    results = cron.run_task_and_publications("ghost")

    assert results == [{"slug": "ghost", "status": "failure", "duration_ms": 0}]
    run.assert_called_once_with("ghost", "manual")


def test_system_tasks_still_run_when_the_database_is_unreachable(mocker, tmp_path):
    # Why: en production S3_BUCKET est renseigné, donc discover_from_s3 ouvre la base et lève. Un
    # test qui vide S3_BUCKET n'exerce que les court-circuits et promet une résilience absente.
    (tmp_path / "sys-task").mkdir()
    (tmp_path / "sys-task" / "cron.py").write_text("print('hello')")
    (tmp_path / "sys-task" / "CRON.md").write_text("---\nbatch: maintenance\n---\n")
    mocker.patch.object(cron.config, "CRON_DIR", tmp_path)
    mocker.patch.object(cron.config, "S3_BUCKET", "bucket")
    mocker.patch.object(cron, "get_db", side_effect=OperationalError("stmt", {}, Exception("db down")))
    mocker.patch.object(cron.alerts, "notify_alert_channel")
    execute = mocker.patch.object(
        cron, "execute_task", return_value={"slug": "sys-task", "status": "success", "duration_ms": 1, "output": ""}
    )

    results = cron.run_all(batch="maintenance")

    assert len(results) == 1
    assert execute.call_args.args[0]["slug"] == "sys-task"


def test_a_workdir_that_survives_its_removal_is_reported(mocker, tmp_path, caplog):
    mocker.patch.object(cron.shutil, "rmtree")

    with caplog.at_level(logging.WARNING, logger="web.cron"):
        cron.remove_workdir(tmp_path)

    assert caplog.records


def test_an_s3_outage_still_runs_the_system_tasks_without_alerting(mocker):
    mocker.patch.object(cron, "discover_cron_tasks", side_effect=S3_DOWN)
    mocker.patch.object(cron, "discover_system_tasks", return_value=[make_task("sys", source=None, tier="system")])
    execute = mocker.patch.object(
        cron, "execute_task", return_value={"slug": "sys", "status": "success", "duration_ms": 1}
    )
    notify = mocker.patch.object(cron.alerts, "notify_alert_channel")

    results = cron.run_all(batch="maintenance")

    assert [r["slug"] for r in results] == ["sys"]
    assert execute.call_count == 1
    notify.assert_not_called()


def test_an_s3_outage_alerts_once_from_the_dashboard_batch_which_runs_nothing(mocker):
    # Why: les quatre conteneurs découvrent en même temps ; seul le lot des tableaux de bord perd
    # tout, c'est donc lui seul qui parle — et il ne prétend pas faire tourner des tâches système.
    mocker.patch.object(cron, "discover_cron_tasks", side_effect=S3_DOWN)
    mocker.patch.object(cron, "discover_system_tasks", return_value=[make_task("sys", source=None, tier="system")])
    execute = mocker.patch.object(cron, "execute_task")
    notify = mocker.patch.object(cron.alerts, "notify_alert_channel")

    cron.run_all(batch=cron.DASHBOARD_BATCH)

    execute.assert_not_called()
    notify.assert_called_once()
    assert f"`{cron.DASHBOARD_BATCH}`" in notify.call_args.args[0]
    assert "système" not in notify.call_args.args[0]


def test_a_batch_over_its_budget_stops_launching_and_says_which_tasks_it_dropped(mocker):
    tasks = [make_task("a", source=None), make_task("b", source=None), make_task("c", source=None)]
    mocker.patch.object(cron, "discover_cron_tasks", return_value=tasks)
    mocker.patch.object(cron, "is_due", return_value=True)
    # Why: un compte d'appels exact rendrait ce test coupleé au nombre de lignes de run_all qui
    # lisent l'horloge. On exprime plutôt le scénario : le budget n'est dépassé qu'une fois que la
    # première tâche a effectivement tourné, quel que soit le nombre d'appels à monotonic() avant.
    budget_consumed = False

    def fake_monotonic():
        return 99 if budget_consumed else 0

    def fake_execute_task(task, trigger, batch_run_id):
        nonlocal budget_consumed
        budget_consumed = True
        return {"slug": "a", "status": "success", "duration_ms": 1, "output": ""}

    mocker.patch.object(cron.time, "monotonic", side_effect=fake_monotonic)
    execute = mocker.patch.object(cron, "execute_task", side_effect=fake_execute_task)
    record_run = mocker.patch.object(cron, "record_run")
    notify = mocker.patch.object(cron.alerts, "notify_alert_channel")

    cron.run_all(batch="maintenance", budget=10)

    assert execute.call_count == 1
    assert [call.args[0]["slug"] for call in record_run.call_args_list] == ["b", "c"]
    assert {call.args[0]["status"] for call in record_run.call_args_list} == {"skipped"}
    notify.assert_called_once()


def test_next_cron_run_counts_in_utc_like_the_scalingo_schedule(mocker):
    mocker.patch.object(cron, "utcnow", return_value=datetime(2026, 7, 1, 5, 0, tzinfo=timezone.utc))
    assert cron.next_cron_run("daily", cron.DASHBOARD_BATCH) == datetime(2026, 7, 1, 6, 0, tzinfo=timezone.utc)


def test_a_batch_closes_its_sentry_check_in_only_once_it_reaches_the_end(mocker):
    mocker.patch.object(cron, "discover_cron_tasks", return_value=[make_task("a", source=None)])
    mocker.patch.object(cron, "is_due", return_value=True)
    checkin = mocker.patch.object(cron.sentry_sdk.crons.api, "capture_checkin", return_value="cid")

    def mid_batch(task, trigger, batch_run_id):
        assert [call.kwargs["status"] for call in checkin.call_args_list] == ["in_progress"]
        return {"slug": "a", "status": "success", "duration_ms": 1, "output": ""}

    mocker.patch.object(cron, "execute_task", side_effect=mid_batch)

    cron.run_all(batch="maintenance")

    assert checkin.call_args_list[-1].kwargs["monitor_slug"] == "lot-maintenance"
    assert checkin.call_args_list[-1].kwargs["status"] == "ok"
    assert checkin.call_args_list[-1].kwargs["check_in_id"] == "cid"


@pytest.mark.parametrize(
    "budget,expected_minutes",
    [
        (None, 1 + (300 + 600) // 60),
        (60, 1 + (60 + 600) // 60),
        (3600, 1 + (300 + 600) // 60),
    ],
)
def test_a_batch_monitor_allows_the_time_the_batch_can_legitimately_take(budget, expected_minutes):
    tasks = [make_task("a", timeout=300), make_task("b", timeout=600), make_task("c", timeout=900, batch="xl")]
    assert cron.batch_monitor_config("maintenance", tasks, budget)["max_runtime"] == expected_minutes


def test_a_batch_without_a_budget_runs_everything(mocker):
    tasks = [make_task("a", source=None), make_task("b", source=None)]
    mocker.patch.object(cron, "discover_cron_tasks", return_value=tasks)
    mocker.patch.object(cron, "is_due", return_value=True)
    execute = mocker.patch.object(
        cron, "execute_task", return_value={"slug": "x", "status": "success", "duration_ms": 1, "output": ""}
    )

    cron.run_all(batch="maintenance")

    assert execute.call_count == 2


def test_the_cron_entry_point_initialises_sentry(monkeypatch, mocker):
    monkeypatch.setattr("sys.argv", ["cron", "--dry-run", "--batch", "maintenance"])
    mocker.patch.object(cron, "setup_logging")
    mocker.patch.object(cron, "run_all", return_value=[])
    init = mocker.patch.object(cron, "init_sentry")

    cron.main()

    init.assert_called_once()


@pytest.mark.parametrize("budget", ["0", "-5"])
def test_the_cron_entry_point_refuses_a_budget_that_is_not_positive(monkeypatch, mocker, capsys, budget):
    monkeypatch.setattr("sys.argv", ["cron", "--batch", "tableaux", "--budget", budget])
    mocker.patch.object(cron, "setup_logging")
    mocker.patch.object(cron, "init_sentry")
    run_all = mocker.patch.object(cron, "run_all")

    with pytest.raises(SystemExit) as exc_info:
        cron.main()

    assert exc_info.value.code != 0
    assert "budget" in capsys.readouterr().err.lower()
    run_all.assert_not_called()


def test_the_cron_entry_point_refuses_to_run_with_no_mode_and_no_batch(monkeypatch, mocker, capsys):
    monkeypatch.setattr("sys.argv", ["cron"])
    mocker.patch.object(cron, "setup_logging")
    mocker.patch.object(cron, "init_sentry")

    with pytest.raises(SystemExit) as exc_info:
        cron.main()

    assert exc_info.value.code != 0
    assert "batch" in capsys.readouterr().err.lower()


@pytest.mark.parametrize(
    ("argv", "mocked"),
    [
        (["cron", "--list"], "discover_cron_tasks"),
        (["cron", "--app", "sys-task"], "run_cron_task"),
        (["cron", "--facade-audit"], "facade_audit"),
    ],
)
def test_a_mode_runs_without_a_batch(monkeypatch, mocker, argv, mocked):
    monkeypatch.setattr("sys.argv", argv)
    mocker.patch.object(cron, "setup_logging")
    mocker.patch.object(cron, "init_sentry")
    mocker.patch.object(cron, "discover_cron_tasks", return_value=[])
    mocker.patch.object(cron, "facade_audit", return_value=[])
    mocker.patch.object(
        cron,
        "run_cron_task",
        return_value={"slug": "sys-task", "status": "success", "duration_ms": 1, "output": ""},
    )

    cron.main()

    assert getattr(cron, mocked).called


@pytest.mark.parametrize(
    "slug", ["sync-sites", "sync-inventory", "sync-webinaires", "sync-connectors", "sync-tags", "refresh-rpe"]
)
def test_every_copy_of_an_external_source_runs_in_the_synchros_batch(slug):
    # Why: le lot suit la nature du travail — les synchros tournent à 02:00, avant les tableaux de
    # bord qu'elles alimentent, et à l'écart de la fenêtre de 06:00.
    tasks = {task["slug"]: task for task in repo_system_tasks()}

    assert tasks[slug]["batch"] == "synchros"


def test_declared_batches_and_scheduled_batches_are_the_same_set():
    # Why: dans un sens, une faute de frappe dans `batch:` donne une tâche découverte, activée, due
    # — et jamais exécutée. Dans l'autre, une faute de frappe dans cron.json démarre chaque jour un
    # conteneur qui ne trouve aucune tâche, imprime « 0 succeeded, 0 failed » et sort en 0. Le lot
    # des tableaux de bord n'est déclaré par aucun CRON.md, seulement par DASHBOARD_BATCH : sans lui
    # ici, sa ligne pourrait disparaître de cron.json sans qu'aucun test ne bronche.
    jobs = json.loads((Path(cron.config.BASE_DIR) / "cron.json").read_text())["jobs"]
    scheduled = {scheduled_batch(job["command"]) for job in jobs if "--batch" in job["command"]}

    declared = {task["batch"] for task in repo_system_tasks()} | {cron.DASHBOARD_BATCH}
    assert declared == scheduled


def test_every_system_task_points_at_a_module_that_exists():
    # Why: le point d'entrée n'est qu'un `from X import main` — une faute dans X ne se voit
    # qu'à 02:00 en production, sur une tâche qui ne laisse qu'un ImportError.
    for task in repo_system_tasks():
        tree = ast.parse(Path(task["cron_path"]).read_text())
        for node in (n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level == 0):
            assert importlib.util.find_spec(node.module) is not None, f"{task['slug']} → {node.module}"


def test_every_system_task_goes_through_the_shared_entry_point():
    # Why: le contrat commun (logs du produit, échec tracé, code retour) ne tient que si aucune
    # tâche ne peut l'oublier — sinon on revient aux quatre formes d'avant.
    for task in repo_system_tasks():
        tree = ast.parse(Path(task["cron_path"]).read_text())
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == "web.cron_task"
            for alias in node.names
        }
        called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}

        assert "run" in imported, task["slug"]
        assert "run" in called, task["slug"]
