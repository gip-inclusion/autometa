"""Contrat du point d'entrée commun des crons système."""

import logging

import pytest

from web import cron_task


def test_run_configures_the_product_logging_before_the_task(mocker):
    calls = []
    mocker.patch.object(cron_task, "setup_logging", side_effect=lambda **kw: calls.append("logging"))

    cron_task.run(lambda: calls.append("task"))

    assert calls == ["logging", "task"]


def test_a_task_that_raises_exits_with_a_non_zero_code_and_leaves_a_structured_log(mocker, caplog):
    mocker.patch.object(cron_task, "setup_logging")

    def boom():
        raise RuntimeError("Grist injoignable")

    with caplog.at_level(logging.ERROR, logger="web.cron_task"), pytest.raises(SystemExit) as exit_info:
        cron_task.run(boom)

    assert exit_info.value.code == 1
    assert any(record.exc_info and "Grist injoignable" in record.exc_text for record in caplog.records)


def test_a_task_that_succeeds_does_not_exit(mocker):
    mocker.patch.object(cron_task, "setup_logging")

    assert cron_task.run(lambda: None) is None
