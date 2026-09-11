"""Le cron suggest-tags résume ses lots sur Slack et signale une panne comme telle."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "suggest_tags_cron", Path(__file__).resolve().parent.parent / "cron" / "suggest-tags" / "cron.py"
)
cron = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cron)


def outcome(processed=0, failed=0, deferred=0, error=None):
    result = {"processed": processed, "failed": failed, "deferred": deferred}
    return result | {"error": error} if error else result


@pytest.mark.parametrize(
    ("results", "expected_start"),
    [
        ([outcome(processed=3), outcome(), outcome(processed=1, failed=1)], "Rattrapage"),
        ([outcome(failed=4), outcome(), outcome()], ":warning: Rattrapage"),
        ([outcome(error="vocabulaire vide")], ":warning: Rattrapage des suggestions de tags — vocabulaire vide"),
    ],
    ids=["healthy", "total-failure", "refused"],
)
def test_a_batch_where_everything_failed_is_flagged_like_an_outage(mocker, results, expected_start):
    mocker.patch.object(cron, "run", side_effect=results)
    notify = mocker.patch.object(cron, "notify_alert_channel")

    cron.main()

    assert notify.call_args.args[0].startswith(expected_start)


def test_a_quiet_run_stays_silent(mocker):
    mocker.patch.object(cron, "run", return_value=outcome())
    notify = mocker.patch.object(cron, "notify_alert_channel")

    cron.main()

    notify.assert_not_called()
