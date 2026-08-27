"""Le contrôle de la façade aux deux moments où un TDB passe : écriture (skills) et exécution (cron)."""

from contextlib import nullcontext

import pytest

from lib import dashboards
from web import cron

CONFORMING = "from lib.dashboard_api import query_matomo\n\nquery_matomo('inclusion', 'VisitsSummary.get')\n"
OFFENDING = "from lib.query import execute_matomo_query\nfrom web.db import get_db\n"


def dashboard_dir(mocker, tmp_path, files):
    mocker.patch.object(dashboards.config, "INTERACTIVE_DIR", tmp_path)
    if files is None:
        return
    slug_dir = tmp_path / "tdb"
    slug_dir.mkdir()
    for name, body in files.items():
        (slug_dir / name).write_text(body)


@pytest.mark.parametrize(
    ("files", "expectation"),
    [
        ({"cron.py": CONFORMING}, nullcontext()),
        ({}, nullcontext()),
        (None, nullcontext()),
        ({"cron.py": OFFENDING}, pytest.raises(ValueError, match=r"cron\.py importe lib\.query, web\.db")),
        ({"cron.py": "def main(\n"}, pytest.raises(ValueError, match="pas un fichier Python valide")),
    ],
)
def test_check_facade_compliance(mocker, tmp_path, files, expectation):
    dashboard_dir(mocker, tmp_path, files)
    with expectation:
        dashboards.check_facade_compliance("tdb")


def test_template_only_imports_the_facade():
    template = dashboards.config.BASE_DIR / "docs" / "dashboard-template" / "cron.py"
    assert cron.dashboard_api.facade_violations(template.read_text()) == []


def cron_task(slug):
    return {"slug": slug, "cron_path": f"{slug}/cron.py", "source": "s3"}


@pytest.mark.parametrize(
    ("sources", "expected"),
    [
        ({"ok": CONFORMING}, {}),
        ({"ko": OFFENDING}, {"ko": ["lib.query", "web.db"]}),
        ({"ok": CONFORMING, "ko": OFFENDING}, {"ko": ["lib.query", "web.db"]}),
        ({"broken": "def main(\n"}, {}),
        ({"gone": None}, {}),
    ],
)
def test_facade_violations_by_slug(mocker, sources, expected):
    mocker.patch.object(cron, "read_cron_script", side_effect=lambda task: sources[task["slug"]])
    tasks = [cron_task(slug) for slug in sources]
    assert cron.facade_violations_by_slug(tasks) == expected


def test_system_crons_are_not_held_to_the_facade(mocker):
    mocker.patch.object(cron, "read_cron_script", return_value=OFFENDING)
    system_task = {"slug": "refresh-rpe", "cron_path": "cron/refresh-rpe/cron.py", "tier": "system"}
    assert cron.facade_violations_by_slug([system_task]) == {}


def test_scheduling_alerts_but_does_not_block(mocker):
    mocker.patch.object(cron, "read_cron_script", return_value=OFFENDING)
    notify = mocker.patch.object(cron.alerts, "notify_alert_channel")
    execute = mocker.patch.object(cron, "execute_task", return_value={"status": "success", "duration_ms": 1})
    mocker.patch.object(
        cron,
        "discover_cron_tasks",
        return_value=[{**cron_task("ko"), "enabled": True, "schedule": "daily", "timeout": 30}],
    )

    assert len(cron.run_all()) == 1
    execute.assert_called_once()
    message = notify.call_args.args[0]
    assert "lib.dashboard_api" in message
    assert "`ko`" in message


def test_dry_run_does_not_alert(mocker):
    mocker.patch.object(cron, "read_cron_script", return_value=OFFENDING)
    notify = mocker.patch.object(cron.alerts, "notify_alert_channel")
    mocker.patch.object(
        cron,
        "discover_cron_tasks",
        return_value=[{**cron_task("ko"), "enabled": True, "schedule": "daily", "timeout": 30}],
    )

    assert cron.run_all(dry_run=True) == []
    notify.assert_not_called()


def test_conforming_schedule_stays_silent(mocker):
    mocker.patch.object(cron, "read_cron_script", return_value=CONFORMING)
    notify = mocker.patch.object(cron.alerts, "notify_alert_channel")
    mocker.patch.object(cron, "execute_task", return_value={"status": "success", "duration_ms": 1})
    mocker.patch.object(
        cron,
        "discover_cron_tasks",
        return_value=[{**cron_task("ok"), "enabled": True, "schedule": "daily", "timeout": 30}],
    )

    cron.run_all()
    notify.assert_not_called()


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_facade_audit_counts_active_dashboards(mocker):
    mocker.patch.object(cron, "read_cron_script", return_value=OFFENDING)
    mocker.patch.object(cron, "discover_cron_tasks", return_value=[cron_task("ko")])
    assert cron.facade_audit() == [
        f"0 tableaux de bord actifs, 1 importent hors de {cron.dashboard_api.FACADE}.",
        f"  {'ko':30s} lib.query, web.db",
    ]
