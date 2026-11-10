import pytest
import yaml

from lib import agent_config
from lib.agent_connectors import cron as cron_connector

SLUG = "signaux-faibles-mep"


def make_agent(**overrides):
    return {
        "format": "pdi.agent/1",
        "slug": SLUG,
        "title": "Signaux faibles des mises en production",
        "mission": "Signaler à l'équipe produit les MEP dont l'effet n'est pas mesurable.",
        "destinations": [{"id": "produit.signal_faible", "mode": "shadow"}],
        **overrides,
    }


def test_dod_1_destinations_are_a_closed_list_without_real_identifiers():
    destinations = agent_config.known_destinations()
    assert {d["channel"] for d in destinations.values()} == {"slack", "notion"}
    assert all(set(d) == {"id", "channel", "autonomous_allowed"} for d in destinations.values())


def test_dod_2_valid_configuration_is_accepted():
    assert agent_config.validate(make_agent()) == []


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"destinations": [{"id": "produit.signal_faibl", "mode": "shadow"}]}, "'produit.signal_faible'"),
        ({"destinations": [{"id": "#general", "mode": "shadow"}]}, "n'est pas une destination"),
        ({"destinations": [{"id": "produit.signal_faible", "mode": "direct"}]}, "modes permis"),
        ({"destinations": [{"id": "produit.signal_faible", "mode": "live"}]}, "autonomous_allowed"),
        ({"destinations": [{"id": "produit.signal_faible", "mode": "shadow", "channel": "C0123"}]}, "id et mode"),
        ({"destinations": []}, "de 1 à 6"),
        ({"webhook": "https://hooks.slack.com/x"}, "webhook : champ inconnu"),
        ({"titr": "x"}, "Vouliez-vous dire 'title'"),
        ({"mission": "Écrire chaque semaine à @louije les MEP sans effet mesuré."}, "'@louije'"),
        ({"mission": "Poster dans #produit les MEP sans effet mesuré cette semaine."}, "'#produit'"),
        ({"mission": "Voir https://example.org pour les MEP sans effet mesuré."}, "'https://'"),
        ({"mission": "trop court"}, "de 20 à 400"),
        ({"title": 12}, "title : attendu un texte"),
        ({"slug": "Signaux"}, "slug :"),
        ({"format": "pdi.agent/2"}, "format : doit valoir"),
    ],
)
def test_dod_2_invalid_configuration_is_refused_naming_field_and_fix(overrides, expected):
    errors = agent_config.validate(make_agent(**overrides))
    assert any(expected in e for e in errors), errors


def test_dod_2_missing_fields_and_non_mapping_are_refused():
    assert agent_config.validate(["format"]) == ["(racine) : la configuration doit être un objet YAML (clé: valeur)."]
    doc = make_agent()
    del doc["mission"]
    assert agent_config.validate(doc) == ["mission : champ obligatoire absent."]


def test_dod_2_duplicate_destination_is_refused():
    contacts = [{"id": "produit.signal_faible", "mode": "shadow"}, {"id": "produit.signal_faible", "mode": "review"}]
    assert agent_config.validate(make_agent(destinations=contacts)) == [
        "destinations : 'produit.signal_faible' apparaît plusieurs fois."
    ]


def test_dod_6_real_mode_is_accepted_for_an_agent_named_in_autonomous_allowed(mocker):
    destinations = agent_config.known_destinations()
    destinations["produit.signal_faible"]["autonomous_allowed"] = [SLUG]
    mocker.patch("lib.agent_config.known_destinations", return_value=destinations)
    contacts = [{"id": "produit.signal_faible", "mode": "live"}]
    assert agent_config.validate(make_agent(destinations=contacts)) == []


def test_dod_2_parse_refuses_duplicate_keys_that_yaml_would_overwrite():
    assert agent_config.parse("slug: a-b-c\ntitle: Veille\n") == {"slug": "a-b-c", "title": "Veille"}
    with pytest.raises(yaml.YAMLError, match="clé en double : slug"):
        agent_config.parse("slug: a-b-c\nslug: d-e-f\n")


@pytest.mark.parametrize(
    ("targets", "missing", "unknown"),
    [
        ({"produit.signal_faible": "C1", "bizdev.marche": "C2", "produit.opportunite": "db"}, [], []),
        ({"produit.signal_faible": "C1", "bizdev.marche": ""}, ["bizdev.marche", "produit.opportunite"], []),
        (
            {"produit.signal_faible": "C1", "bizdev.marche": "C2", "produit.opportunite": "db", "produit.signal": "C3"},
            [],
            ["produit.signal"],
        ),
    ],
)
def test_dod_11_target_gaps_list_destinations_without_target_and_unknown_targets(mocker, targets, missing, unknown):
    mocker.patch("lib.agent_config.config.AGENT_DESTINATION_TARGETS", targets)
    assert agent_config.target_gaps() == (missing, unknown)


def test_dod_11_gaps_are_warnings_naming_destinations_never_identifiers(mocker, caplog):
    mocker.patch("lib.agent_config.config.AGENT_DESTINATION_TARGETS", {"bizdev.marche": "C2", "x.y": "C9SECRET"})
    agent_config.warn_target_gaps()
    assert [r.levelname for r in caplog.records] == ["WARNING", "WARNING"]
    assert "produit.opportunite, produit.signal_faible" in caplog.text
    assert "inconnues : x.y" in caplog.text
    assert "C9SECRET" not in caplog.text


def test_dod_11_no_warning_when_aligned(mocker, caplog):
    targets = {d: "id" for d in agent_config.known_destinations()}
    mocker.patch("lib.agent_config.config.AGENT_DESTINATION_TARGETS", targets)
    agent_config.warn_target_gaps()
    assert caplog.records == []


OUTIL = {
    "type": "classifier",
    "model": "clef:27b",
    "question": "Est-ce une opportunité pour le produit ?",
    "threshold": 0.7,
}
EXTRACTION = {"type": "extraction", "model": "glm-5.2", "schema": {"produit": "string", "demandes": "integer"}}
RESUME = {"type": "summary", "model": "gemma4:31b", "max_length": 600}


def test_dod_10_sub_agents_typed_preparations_and_cadence_are_accepted():
    steps = [
        {"type": "notion", "base": "0" * 32},
        {"type": "cron", "task": "sync-tags"},
        {"type": "s3", "dataset": "a.jsonl"},
    ]
    doc = make_agent(schedule="weekly", subagents=[OUTIL, EXTRACTION, RESUME], preparations=steps)
    assert agent_config.validate(doc) == []


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"subagents": [{**OUTIL, "type": "traduction"}]}, "subagents[0].type : attendu un type"),
        ({"subagents": [{**OUTIL, "model": "nimble"}]}, "'nimble' n'est pas permis pour classifier"),
        ({"subagents": [{**OUTIL, "model": "glm-5.2"}]}, "modèles permis : clef:27b"),
        ({"subagents": [{**RESUME, "model": "clef:27b"}]}, "'clef:27b' n'est pas permis pour summary"),
        ({"subagents": [{**RESUME, "model": "glm-5"}]}, "Vouliez-vous dire 'glm-5.2'"),
        ({"subagents": [{**OUTIL, "threshold": 1}]}, "subagents[0].threshold : attendu une probabilité"),
        ({"subagents": [{**OUTIL, "threshold": True}]}, "subagents[0].threshold"),
        ({"subagents": [{**OUTIL, "question": "Oui ?"}]}, "subagents[0].question : attendu un texte"),
        ({"subagents": [{**OUTIL, "question": "Faut-il prévenir @louije de ceci ?"}]}, "'@louije'"),
        ({"subagents": [{"type": "classifier"}]}, "exactement les champs type, model, question, threshold"),
        ({"subagents": [{**RESUME, "threshold": 0.5}]}, "exactement les champs type, model, max_length"),
        ({"subagents": [{**EXTRACTION, "schema": []}]}, "subagents[0].schema : attendu de 1 à 10"),
        ({"subagents": [{**EXTRACTION, "schema": {}}]}, "subagents[0].schema : attendu de 1 à 10"),
        ({"subagents": [{**EXTRACTION, "schema": {f"c{i}": "string" for i in range(11)}}]}, "de 1 à 10"),
        ({"subagents": [{**EXTRACTION, "schema": {"Produit": "string"}}]}, "schema.Produit : name en minuscules"),
        ({"subagents": [{**EXTRACTION, "schema": {"produit": "date"}}]}, "type parmi string, number"),
        ({"subagents": [{**EXTRACTION, "schema": {"p": {"type": "string"}}}]}, "schema.p : name"),
        ({"subagents": [{**RESUME, "max_length": 20}]}, "max_length : attendu un nombre de caractères"),
        ({"subagents": [{**RESUME, "max_length": 100000}]}, "de 100 à 3000"),
        ({"subagents": [{**RESUME, "max_length": "600"}]}, "max_length"),
        ({"subagents": [{**RESUME, "max_length": True}]}, "max_length"),
        ({"subagents": [OUTIL, OUTIL]}, "apparaît plusieurs fois"),
        ({"subagents": [OUTIL, EXTRACTION, RESUME, RESUME, EXTRACTION, OUTIL]}, "attendu une liste de 5"),
        ({"subagents": "classifier"}, "subagents : attendu une liste"),
        ({"subagents": ["classifier"]}, "subagents[0].type : attendu un type"),
        (
            {"preparations": [{"type": "sql", "requete": "select 1"}]},
            "attendu un type parmi notion, github, url, s3, cron",
        ),
        ({"preparations": ["sync-tags"]}, "preparations[0] : attendu un type parmi"),
        ({"preparations": [{"type": "cron", "task": "sync-tag"}]}, "Vouliez-vous dire 'sync-tags'"),
        ({"preparations": [{"type": "cron", "task": "run-agents"}]}, "'run-agents' n'est pas une tâche de cron/"),
        ({"preparations": [{"type": "cron", "task": "../web"}]}, "n'est pas une tâche de cron/"),
        ({"preparations": [{"type": "notion", "base": "https://notion.so/x"}]}, "preparations[0].base"),
        ({"preparations": [{"type": "s3", "dataset": "../secrets.json"}]}, "preparations[0].dataset"),
        (
            {"preparations": [{"type": "s3", "dataset": "a.csv", "url": "x"}]},
            "champs inconnus pour s3 : url ; champs : dataset",
        ),
        ({"preparations": [{"type": "cron", "task": "sync-tags"}] * 2}, "'cron sync-tags' apparaît plusieurs fois"),
        ({"preparations": [{"type": "cron", "task": "sync-tags"}] * 6}, "preparations : attendu une liste de 5"),
        ({"preparations": "sync-tags"}, "preparations : attendu une liste"),
        ({"schedule": "toutes les heures"}, "attendu weekdays: [monday, thursday] ou l'un de daily, weekly"),
    ],
)
def test_dod_10_unknown_sub_agent_preparation_type_or_cadence_is_refused(overrides, expected):
    errors = agent_config.validate(make_agent(**overrides))
    assert any(expected in e for e in errors), errors


def test_dod_11_cron_preparations_are_the_tasks_of_cron_except_the_generic_agents_cron():
    tasks = cron_connector.tasks()
    assert "sync-tags" in tasks
    assert cron_connector.GENERIC_CRON not in tasks
    assert (agent_config.config.CRON_DIR / cron_connector.GENERIC_CRON / "cron.py").is_file()


def test_dod_10_each_sub_agent_type_has_its_own_ollama_cloud_models():
    assert agent_config.models() == {
        "classifier": ["clef:27b"],
        "extraction": ["glm-5.2", "gemma4:31b"],
        "summary": ["glm-5.2", "gemma4:31b"],
    }
    assert set(agent_config.models()) == set(agent_config.SUBAGENT_FIELDS)


LABELS = [{"name": "rapide", "question": "Est-ce faisable en moins d'une semaine ?"}]


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"subagents": [{**OUTIL, "labels": LABELS}]}, "question, threshold ou type, model, labels, threshold"),
        (
            {"subagents": [{"type": "classifier", "model": "clef:27b", "labels": [], "threshold": 0.5}]},
            "de 1 à 10",
        ),
        (
            {"subagents": [{"type": "classifier", "model": "clef:27b", "labels": LABELS * 11, "threshold": 0.5}]},
            "de 1 à 10 étiquettes",
        ),
        (
            {"subagents": [{"type": "classifier", "model": "clef:27b", "labels": {"rapide": "x"}, "threshold": 0.5}]},
            "chacune {name, question}",
        ),
        (
            {"subagents": [{"type": "classifier", "model": "clef:27b", "labels": LABELS * 2, "threshold": 0.5}]},
            "noms invalides ou en double : rapide",
        ),
        (
            {
                "subagents": [
                    {
                        "type": "classifier",
                        "model": "clef:27b",
                        "labels": [{"name": "Rapide!", "question": "Est-ce faisable vite ?"}],
                        "threshold": 0.5,
                    }
                ]
            },
            "noms invalides ou en double : Rapide!",
        ),
        (
            {
                "subagents": [
                    {
                        "type": "classifier",
                        "model": "clef:27b",
                        "labels": [{"name": "rapide", "question": "Écrire à @louije si c'est rapide ?"}],
                        "threshold": 0.5,
                    }
                ]
            },
            "subagents[0].labels.rapide : contient '@louije'",
        ),
        ({"schedule": {"weekdays": ["monday", "monday"]}}, "schedule.weekdays : attendu une liste sans doublon"),
        ({"schedule": {"weekdays": ["lundi"]}}, "jours parmi monday, tuesday"),
        ({"schedule": {"weekdays": []}}, "schedule.weekdays"),
        ({"schedule": {"weekdays": ["monday"], "heure": 9}}, "attendu weekdays: [monday, thursday]"),
        ({"files": ["Notes.md"]}, "'Notes.md' invalide"),
        ({"files": ["notes.exe"]}, "'notes.exe' invalide"),
        ({"files": ["../notes.md"]}, "invalide"),
        ({"files": ["a.md"] * 2}, "'a.md' apparaît plusieurs fois"),
        ({"files": [f"f{i}.md" for i in range(6)]}, "5 noms de fichiers au plus"),
        ({"destinations": [], "files": []}, "de 1 à 6"),
    ],
)
def test_dod_17_labels_days_and_files_are_validated_as_data(overrides, expected):
    errors = agent_config.validate(make_agent(**overrides))
    assert any(expected in e for e in errors), errors


def test_dod_17_labels_days_and_files_compose_freely_and_are_described_for_the_review():
    labeller = {"type": "classifier", "model": "clef:27b", "labels": LABELS, "threshold": 0.6}
    doc = make_agent(
        destinations=[],
        files=["notes.md", "suivi.csv"],
        schedule={"weekdays": ["tuesday", "friday"]},
        subagents=[labeller, labeller | {"threshold": 0.8}],
        preparations=[{"type": "github", "organization": "owner", "cap": 50000}],
    )
    assert agent_config.validate(doc) == []
    assert agent_config.describe(doc) == [
        "sous-agent 1 : classifier clef:27b, étiquettes rapide au seuil 0.6, sans rien écarter",
        "sous-agent 2 : classifier clef:27b, étiquettes rapide au seuil 0.8, sans rien écarter",
        "préparation 1 : github owner (cap 50000)",
        "fichier de l'agent : notes.md, versionné, lisible depuis le chat",
        "fichier de l'agent : suivi.csv, versionné, lisible depuis le chat",
        "cadence : chaque tuesday, friday",
    ]
    assert agent_config.describe(make_agent(schedule="weekly"))[-1] == "cadence : weekly"
    assert agent_config.describe(make_agent())[-1] == "cadence : à la demande"
