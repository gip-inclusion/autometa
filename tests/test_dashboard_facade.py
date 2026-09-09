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
    return {"slug": slug, "cron_path": f"{slug}/cron.py", "source": "s3", "batch": cron.DEFAULT_BATCH}


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
    system_task = {
        "slug": "refresh-rpe",
        "cron_path": "cron/refresh-rpe/cron.py",
        "tier": "system",
        "batch": cron.DEFAULT_BATCH,
    }
    assert cron.facade_violations_by_slug([system_task]) == {}


def test_scheduling_does_not_scan_s3_nor_alert(mocker):
    """L'audit tombait avant tout filtrage batch : deux passes par jour, un pavé Slack par passe."""
    read = mocker.patch.object(cron, "read_cron_script", return_value=OFFENDING)
    notify = mocker.patch.object(cron.alerts, "notify_alert_channel")
    execute = mocker.patch.object(cron, "execute_task", return_value={"status": "success", "duration_ms": 1})
    mocker.patch.object(
        cron,
        "discover_cron_tasks",
        return_value=[{**cron_task("ko"), "enabled": True, "schedule": "daily", "timeout": 30}],
    )

    assert len(cron.run_all()) == 1
    execute.assert_called_once()
    notify.assert_not_called()
    read.assert_not_called()


def test_an_executed_task_logs_what_it_imports_outside_the_facade(mocker, tmp_path, caplog):
    """Le cron.py est déjà sur disque au moment de l'exécution : le signaler ne coûte aucun appel S3."""
    script = tmp_path / "cron.py"
    script.write_text(OFFENDING)

    with caplog.at_level("WARNING"):
        cron.log_facade_violations("ko", script)

    assert "lib.query, web.db" in caplog.text


@pytest.mark.parametrize("body", [CONFORMING, "def main(\n"])
def test_an_executed_task_stays_silent_when_it_has_nothing_to_say(mocker, tmp_path, caplog, body):
    script = tmp_path / "cron.py"
    script.write_text(body)

    with caplog.at_level("WARNING"):
        cron.log_facade_violations("ok", script)

    assert caplog.text == ""


def audit(mocker, sources, connus):
    mocker.patch.object(cron, "read_cron_script", side_effect=lambda task: sources[task["slug"]])
    mocker.patch.object(cron, "discover_cron_tasks", return_value=[cron_task(slug) for slug in sources])
    mocker.patch.object(cron, "last_reported_slugs", return_value=connus)
    return mocker.patch.object(cron.alerts, "notify_alert_channel"), mocker.patch.object(cron, "record_reported_slugs")


@pytest.mark.parametrize(
    ("sources", "connus", "alerte", "enregistre"),
    [
        ({"ko": OFFENDING}, None, True, True),
        ({"ko": OFFENDING}, [], True, True),
        # Why: un canal où le même message revient chaque jour cesse d'être lu — les échecs s'y noient.
        ({"ko": OFFENDING}, ["ko"], False, False),
        ({"ko": OFFENDING, "ko2": OFFENDING}, ["ko"], True, True),
        ({"ok": CONFORMING}, ["ko"], True, True),
        ({"ok": CONFORMING}, [], False, False),
        # Premier passage d'un parc conforme : rien à dire, mais l'état de référence se pose.
        ({"ok": CONFORMING}, None, False, True),
    ],
)
def test_the_audit_alerts_only_when_the_list_changes(mocker, sources, connus, alerte, enregistre):
    notify, record = audit(mocker, sources, connus)

    cron.report_facade_violations(cron.discover_cron_tasks(), notify=True)

    assert notify.called == alerte
    assert record.called == enregistre
    if enregistre:
        record.assert_called_once_with(sorted(slug for slug, body in sources.items() if body is OFFENDING))


def test_the_audit_records_nothing_when_it_does_not_notify(mocker):
    notify, record = audit(mocker, {"ko": OFFENDING}, [])

    cron.report_facade_violations(cron.discover_cron_tasks(), notify=False)

    notify.assert_not_called()
    record.assert_not_called()


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_facade_audit_counts_active_dashboards(mocker):
    mocker.patch.object(cron, "read_cron_script", return_value=OFFENDING)
    mocker.patch.object(cron, "discover_cron_tasks", return_value=[cron_task("ko")])
    assert cron.facade_audit() == [
        f"0 tableaux de bord actifs, 1 importent hors de {cron.dashboard_api.FACADE}.",
        f"  {'ko':30s} lib.query, web.db",
    ]


@pytest.mark.parametrize("slug", ["../../etc", "tdb/../../secrets", "..", "TDB Majuscules", ""])
def test_check_facade_compliance_refuses_a_slug_that_escapes_the_dashboards_directory(slug):
    """Un appelant ne valide pas le slug : la défense appartient à la fonction qui construit le chemin."""
    with pytest.raises(ValueError, match="[Ss]lug"):
        dashboards.check_facade_compliance(slug)


def test_check_facade_compliance_accepts_a_well_formed_slug(mocker, tmp_path):
    mocker.patch.object(dashboards.config, "INTERACTIVE_DIR", tmp_path)
    (tmp_path / "mon-tdb").mkdir()

    assert dashboards.check_facade_compliance("mon-tdb") is None


@pytest.mark.parametrize(
    ("files", "attendu"),
    [
        ({"cron.py": CONFORMING}, []),
        ({"cron.py": OFFENDING}, ["cron.py importe lib.query, web.db"]),
        (None, []),
    ],
)
def test_facade_problems_enonce_sans_lever(mocker, tmp_path, files, attendu):
    """La liste des problèmes est une donnée : c'est l'appelant qui décide d'en faire un refus."""
    dashboard_dir(mocker, tmp_path, files)

    assert dashboards.facade_problems("tdb") == attendu


def test_facade_problems_refuse_un_slug_qui_sort_du_repertoire():
    with pytest.raises(ValueError, match="[Ss]lug"):
        dashboards.facade_problems("../../etc")


def test_mettre_a_jour_les_metadonnees_dun_tdb_herite_ne_juge_pas_son_code(mocker, tmp_path):
    """`lib.dashboard_api` naît avec cette PR : tout TDB antérieur viole la façade par construction."""
    dashboard_dir(mocker, tmp_path, {"cron.py": OFFENDING})
    refuse = mocker.patch.object(dashboards, "check_facade_compliance")
    mocker.patch.object(dashboards, "get_db", side_effect=dashboards.DashboardNotFound("tdb"))

    with pytest.raises(dashboards.DashboardNotFound):
        dashboards.update_dashboard(slug="tdb", updater_email="a@b.c", title="Nouveau titre")

    refuse.assert_not_called()


def test_le_cron_daudit_est_decouvert_et_quotidien():
    """Sorti de `run_all()`, l'audit n'existe que si le runner le découvre comme tâche système."""
    tasks = cron.discover_from_dir(cron.config.CRON_DIR, "CRON.md", "system")
    audit_task = next(task for task in tasks if task["slug"] == "facade-audit")

    assert cron.cadence(audit_task["schedule"]) == "daily"
    assert audit_task["enabled"]


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_letat_precedent_survit_dun_passage_a_lautre(mocker):
    """Sans persistance, l'audit ne peut pas savoir que la liste n'a pas bougé — il crie chaque jour."""
    mocker.patch.object(cron, "read_cron_script", return_value=OFFENDING)
    mocker.patch.object(cron, "discover_cron_tasks", return_value=[cron_task("ko")])
    notify = mocker.patch.object(cron.alerts, "notify_alert_channel")

    cron.report_facade_violations(cron.discover_cron_tasks(), notify=True)
    assert cron.last_reported_slugs() == ["ko"]
    assert notify.call_count == 1

    cron.report_facade_violations(cron.discover_cron_tasks(), notify=True)
    assert notify.call_count == 1


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_un_parc_redevenu_conforme_le_dit_une_fois(mocker):
    mocker.patch.object(cron, "read_cron_script", return_value=CONFORMING)
    mocker.patch.object(cron, "discover_cron_tasks", return_value=[cron_task("ok")])
    notify = mocker.patch.object(cron.alerts, "notify_alert_channel")
    cron.record_reported_slugs(["ko"])

    cron.report_facade_violations(cron.discover_cron_tasks(), notify=True)
    assert "Plus aucun tableau de bord" in notify.call_args.args[0]
    assert cron.last_reported_slugs() == []

    cron.report_facade_violations(cron.discover_cron_tasks(), notify=True)
    assert notify.call_count == 1
