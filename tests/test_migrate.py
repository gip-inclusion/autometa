"""Tests for the deploy migration runner."""

from lib import migrate


def test_main_runs_upgrade_head(mocker):
    run = mocker.patch("lib.migrate.subprocess.run")
    run.return_value.returncode = 0

    assert migrate.main() == 0
    assert [c.args[0] for c in run.call_args_list] == [["alembic", "upgrade", "head"]]


def test_main_reports_failure_to_sentry(mocker):
    run = mocker.patch("lib.migrate.subprocess.run")
    run.return_value.returncode = 1
    init = mocker.patch("lib.migrate.init_sentry")
    capture = mocker.patch("lib.migrate.sentry_sdk.capture_message")

    assert migrate.main() == 1
    init.assert_called_once()
    assert capture.call_args.kwargs.get("level") == "error"


def test_main_success_does_not_report(mocker):
    run = mocker.patch("lib.migrate.subprocess.run")
    run.return_value.returncode = 0
    capture = mocker.patch("lib.migrate.sentry_sdk.capture_message")

    assert migrate.main() == 0
    capture.assert_not_called()
