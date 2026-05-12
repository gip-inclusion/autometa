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


def test_main_stamps_when_needed(mocker):
    mocker.patch("lib.migrate.needs_stamp", return_value=True)
    run = mocker.patch("lib.migrate.subprocess.run")
    run.return_value.returncode = 0

    assert migrate.main() == 0

    assert run.call_args_list[0].args[0] == ["alembic", "stamp", "head"]
    assert run.call_args_list[1].args[0] == ["alembic", "upgrade", "head"]


def test_main_skips_stamp_when_not_needed(mocker):
    mocker.patch("lib.migrate.needs_stamp", return_value=False)
    run = mocker.patch("lib.migrate.subprocess.run")
    run.return_value.returncode = 0

    assert migrate.main() == 0

    assert len(run.call_args_list) == 1
    assert run.call_args_list[0].args[0] == ["alembic", "upgrade", "head"]
