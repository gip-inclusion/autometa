"""Tests for the alembic auto-stamp helper."""

import pytest

from lib import migrate


@pytest.mark.parametrize(
    ("tables", "expected"),
    [
        (set(), False),
        ({"alembic_version"}, False),
        ({"alembic_version", "conversations"}, False),
        ({"conversations", "messages"}, True),
        ({"conversations"}, True),
    ],
)
def test_needs_stamp(mocker, tables, expected):
    inspector = mocker.MagicMock()
    inspector.get_table_names.return_value = list(tables)
    mocker.patch("lib.migrate.inspect", return_value=inspector)
    mocker.patch("lib.migrate.create_engine")

    assert migrate.needs_stamp("postgresql://fake/db") is expected


@pytest.mark.parametrize(
    ("needs", "expected_calls"),
    [
        (True, [["alembic", "stamp", "head"], ["alembic", "upgrade", "head"]]),
        (False, [["alembic", "upgrade", "head"]]),
    ],
)
def test_main(mocker, needs, expected_calls):
    mocker.patch("lib.migrate.needs_stamp", return_value=needs)
    run = mocker.patch("lib.migrate.subprocess.run")
    run.return_value.returncode = 0

    assert migrate.main() == 0
    assert [c.args[0] for c in run.call_args_list] == expected_calls


def test_main_reports_failure_to_sentry(mocker):
    mocker.patch("lib.migrate.needs_stamp", return_value=False)
    run = mocker.patch("lib.migrate.subprocess.run")
    run.return_value.returncode = 1
    init = mocker.patch("lib.migrate.init_sentry")
    capture = mocker.patch("lib.migrate.sentry_sdk.capture_message")

    assert migrate.main() == 1
    init.assert_called_once()
    assert capture.call_args.kwargs.get("level") == "error"


def test_main_success_does_not_report(mocker):
    mocker.patch("lib.migrate.needs_stamp", return_value=False)
    run = mocker.patch("lib.migrate.subprocess.run")
    run.return_value.returncode = 0
    capture = mocker.patch("lib.migrate.sentry_sdk.capture_message")

    assert migrate.main() == 0
    capture.assert_not_called()
