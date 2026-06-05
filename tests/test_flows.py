"""Tests for the Prefect flow helpers (subprocess running, recording, scheduling, backup check)."""

import json

import pytest
from botocore.exceptions import ClientError

from flows import base
from flows import check_s3_backups as backups
from flows.s3_app_crons import _is_due


def test_run_cron_subprocess_success(tmp_path):
    script = tmp_path / "ok.py"
    script.write_text("print('hello world')")
    status, output, duration_ms = base.run_cron_subprocess(str(script), str(tmp_path), 10)
    assert status == "success"
    assert "hello world" in output
    assert duration_ms >= 0


def test_run_cron_subprocess_failure_captures_stderr(tmp_path):
    script = tmp_path / "bad.py"
    script.write_text("import sys; sys.stderr.write('boom'); sys.exit(1)")
    status, output, _ = base.run_cron_subprocess(str(script), str(tmp_path), 10)
    assert status == "failure"
    assert "--- stderr ---" in output
    assert "boom" in output


def test_run_cron_subprocess_timeout(tmp_path):
    script = tmp_path / "slow.py"
    script.write_text("import time; time.sleep(3)")
    status, output, _ = base.run_cron_subprocess(str(script), str(tmp_path), 1)
    assert status == "timeout"
    assert "timed out" in output


def test_run_cron_subprocess_truncates_output(tmp_path):
    script = tmp_path / "big.py"
    script.write_text(f"print('x' * {base.MAX_OUTPUT_SIZE + 1000})")
    status, output, _ = base.run_cron_subprocess(str(script), str(tmp_path), 10)
    assert status == "success"
    assert len(output) <= base.MAX_OUTPUT_SIZE


def test_record_and_notify_scheduled_alerts_on_status(mocker):
    mocker.patch.object(base, "record_run")
    mocker.patch.object(base, "get_app_runs", return_value=[{"status": "success"}])
    notify = mocker.patch.object(base, "notify_cron_status_change")

    result = base.record_and_notify("slug", "failure", "out", base.utcnow(), 12, "scheduled")

    assert result["status"] == "failure"
    assert result["duration_ms"] == 12
    base.record_run.assert_called_once()
    notify.assert_called_once_with("slug", "failure", "success", "out")


def test_record_and_notify_manual_does_not_alert(mocker):
    mocker.patch.object(base, "record_run")
    get = mocker.patch.object(base, "get_app_runs")
    notify = mocker.patch.object(base, "notify_cron_status_change")

    base.record_and_notify("slug", "success", "", base.utcnow(), 5, "manual")

    get.assert_not_called()
    notify.assert_not_called()


def test_run_with_recording_success(mocker):
    mocker.patch.object(base, "record_run")
    mocker.patch.object(base, "get_app_runs", return_value=[])
    notify = mocker.patch.object(base, "notify_cron_status_change")
    ran = []

    result = base.run_with_recording("slug", lambda: ran.append(1))

    assert ran == [1]
    assert result["status"] == "success"
    notify.assert_called_once()


def test_run_with_recording_failure_records_and_reraises(mocker):
    mocker.patch.object(base, "record_run")
    mocker.patch.object(base, "get_app_runs", return_value=[{"status": "success"}])
    mocker.patch.object(base, "notify_cron_status_change")

    def boom():
        raise ValueError("nope")

    with pytest.raises(ValueError, match="nope"):
        base.run_with_recording("slug", boom)

    recorded = base.record_run.call_args.args[0]
    assert recorded["status"] == "failure"
    assert "ValueError" in recorded["output"]


def test_run_with_recording_manual_does_not_alert(mocker):
    mocker.patch.object(base, "record_run")
    notify = mocker.patch.object(base, "notify_cron_status_change")

    base.run_with_recording("slug", lambda: None, trigger="manual")

    notify.assert_not_called()


def test_is_due_daily_always():
    assert _is_due("daily") is True


@pytest.mark.parametrize("weekday,expected", [(0, True), (1, False), (6, False)])
def test_is_due_weekly_only_monday(mocker, weekday, expected):
    fake = mocker.Mock()
    fake.weekday.return_value = weekday
    mocker.patch("flows.s3_app_crons.now_local", return_value=fake)
    assert _is_due("weekly") is expected


def test_check_backup_manifest_skips_when_unconfigured(mocker):
    mocker.patch.object(backups.config, "BACKUP_S3_BUCKET", "")
    make = mocker.patch.object(backups.s3_module, "make_client")
    backups.check_backup_manifest()
    make.assert_not_called()


def _client_returning(mocker, payload: dict):
    client = mocker.Mock()
    body = mocker.Mock()
    body.read.return_value = json.dumps(payload).encode()
    client.get_object.return_value = {"Body": body}
    mocker.patch.object(backups.s3_module, "make_client", return_value=client)
    return client


def test_check_backup_manifest_ok(mocker):
    mocker.patch.object(backups.config, "BACKUP_S3_BUCKET", "bucket")
    _client_returning(mocker, {"ok": True, "objects": 3, "bytes": 99})
    backups.check_backup_manifest()


def test_check_backup_manifest_reports_failure(mocker):
    mocker.patch.object(backups.config, "BACKUP_S3_BUCKET", "bucket")
    _client_returning(mocker, {"ok": False})
    with pytest.raises(RuntimeError, match="reports failure"):
        backups.check_backup_manifest()


def test_check_backup_manifest_missing_raises(mocker):
    mocker.patch.object(backups.config, "BACKUP_S3_BUCKET", "bucket")
    client = mocker.Mock()
    client.get_object.side_effect = ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
    mocker.patch.object(backups.s3_module, "make_client", return_value=client)
    with pytest.raises(RuntimeError, match="manifest missing"):
        backups.check_backup_manifest()
