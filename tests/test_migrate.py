"""Tests for the deploy migration runner."""

from sqlalchemy.exc import OperationalError

from lib import migrate


def unreachable_then_ready(mocker, failures):
    """Moteur qui refuse `failures` connexions avant d'accepter, comme un addon qui démarre."""
    outcomes = [OperationalError("SELECT 1", {}, Exception("connection refused"))] * failures + [mocker.MagicMock()]
    engine = mocker.MagicMock()
    engine.connect.side_effect = outcomes
    mocker.patch("lib.migrate.get_engine", return_value=engine)
    mocker.patch("lib.migrate.time.sleep")
    return engine


def test_wait_for_database_retries_until_the_addon_accepts_connections(mocker):
    engine = unreachable_then_ready(mocker, failures=3)

    assert migrate.wait_for_database() is True
    assert engine.connect.call_count == 4


def test_wait_for_database_gives_up_at_the_deadline(mocker):
    mocker.patch("lib.migrate.get_engine").return_value.connect.side_effect = OperationalError(
        "SELECT 1", {}, Exception("connection refused")
    )
    mocker.patch("lib.migrate.time.sleep")

    assert migrate.wait_for_database(timeout=0) is False


def test_main_aborts_without_running_alembic_when_the_database_never_comes_up(mocker):
    mocker.patch("lib.migrate.wait_for_database", return_value=False)
    run = mocker.patch("lib.migrate.subprocess.run")
    mocker.patch("lib.migrate.init_sentry")
    capture = mocker.patch("lib.migrate.sentry_sdk.capture_message")

    assert migrate.main() == 1
    run.assert_not_called()
    assert capture.call_args.kwargs.get("level") == "error"


def test_main_runs_upgrade_head(mocker):
    mocker.patch("lib.migrate.wait_for_database", return_value=True)
    run = mocker.patch("lib.migrate.subprocess.run")
    run.return_value.returncode = 0

    assert migrate.main() == 0
    assert [c.args[0] for c in run.call_args_list] == [["alembic", "upgrade", "head"]]


def test_main_reports_failure_to_sentry(mocker):
    mocker.patch("lib.migrate.wait_for_database", return_value=True)
    run = mocker.patch("lib.migrate.subprocess.run")
    run.return_value.returncode = 1
    init = mocker.patch("lib.migrate.init_sentry")
    capture = mocker.patch("lib.migrate.sentry_sdk.capture_message")

    assert migrate.main() == 1
    init.assert_called_once()
    assert capture.call_args.kwargs.get("level") == "error"


def test_main_success_does_not_report(mocker):
    mocker.patch("lib.migrate.wait_for_database", return_value=True)
    run = mocker.patch("lib.migrate.subprocess.run")
    run.return_value.returncode = 0
    capture = mocker.patch("lib.migrate.sentry_sdk.capture_message")

    assert migrate.main() == 0
    capture.assert_not_called()
