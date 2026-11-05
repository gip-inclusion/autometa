import pytest
import yaml

from lib import agent_config

SLUG = "signaux-faibles-mep"


def make_agent(**overrides):
    return {
        "format": "pdi.agent/1",
        "slug": SLUG,
        "titre": "Signaux faibles des mises en production",
        "mission": "Signaler à l'équipe produit les MEP dont l'effet n'est pas mesurable.",
        "points_de_contact": [{"id": "produit.signal_faible", "mode": "ombre"}],
        **overrides,
    }


def test_dod_1_destinations_are_a_closed_list_without_real_identifiers():
    destinations = agent_config.destinations()
    assert {d["canal"] for d in destinations.values()} == {"slack", "notion"}
    assert all(set(d) == {"id", "canal", "reel_autorise"} for d in destinations.values())


def test_dod_2_valid_configuration_is_accepted():
    assert agent_config.validate(make_agent()) == []


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"points_de_contact": [{"id": "produit.signal_faibl", "mode": "ombre"}]}, "'produit.signal_faible'"),
        ({"points_de_contact": [{"id": "#general", "mode": "ombre"}]}, "n'est pas une destination"),
        ({"points_de_contact": [{"id": "produit.signal_faible", "mode": "direct"}]}, "modes permis"),
        ({"points_de_contact": [{"id": "produit.signal_faible", "mode": "reel"}]}, "reel_autorise"),
        ({"points_de_contact": [{"id": "produit.signal_faible", "mode": "ombre", "canal": "C0123"}]}, "id et mode"),
        ({"points_de_contact": []}, "de 1 à 6"),
        ({"webhook": "https://hooks.slack.com/x"}, "webhook : champ inconnu"),
        ({"titr": "x"}, "Vouliez-vous dire 'titre'"),
        ({"mission": "Écrire chaque semaine à @louije les MEP sans effet mesuré."}, "'@louije'"),
        ({"mission": "Poster dans #produit les MEP sans effet mesuré cette semaine."}, "'#produit'"),
        ({"mission": "Voir https://example.org pour les MEP sans effet mesuré."}, "'https://'"),
        ({"mission": "trop court"}, "de 20 à 400"),
        ({"titre": 12}, "titre : attendu un texte"),
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
    contacts = [{"id": "produit.signal_faible", "mode": "ombre"}, {"id": "produit.signal_faible", "mode": "relecture"}]
    assert agent_config.validate(make_agent(points_de_contact=contacts)) == [
        "points_de_contact : 'produit.signal_faible' apparaît plusieurs fois."
    ]


def test_dod_6_real_mode_is_accepted_for_an_agent_named_in_reel_autorise(mocker):
    destinations = agent_config.destinations()
    destinations["produit.signal_faible"]["reel_autorise"] = [SLUG]
    mocker.patch("lib.agent_config.destinations", return_value=destinations)
    contacts = [{"id": "produit.signal_faible", "mode": "reel"}]
    assert agent_config.validate(make_agent(points_de_contact=contacts)) == []


def test_dod_2_parse_refuses_duplicate_keys_that_yaml_would_overwrite():
    assert agent_config.parse("slug: a-b-c\ntitre: Veille\n") == {"slug": "a-b-c", "titre": "Veille"}
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
    targets = {d: "id" for d in agent_config.destinations()}
    mocker.patch("lib.agent_config.config.AGENT_DESTINATION_TARGETS", targets)
    agent_config.warn_target_gaps()
    assert caplog.records == []


OUTIL = {
    "type": "classificateur",
    "modele": "clef:27b",
    "question": "Est-ce une opportunité pour le produit ?",
    "seuil": 0.7,
}
EXTRACTION = {"type": "extraction", "modele": "glm-5.2", "schema": {"produit": "texte", "demandes": "entier"}}
RESUME = {"type": "resume", "modele": "gemma4:31b", "longueur_max": 600}


def test_dod_10_sub_agents_typed_preparations_and_cadence_are_accepted():
    steps = [
        {"type": "notion", "base": "0" * 32},
        {"type": "cron", "tache": "sync-tags"},
        {"type": "s3", "jeu": "a.jsonl"},
    ]
    doc = make_agent(cadence="hebdomadaire", outils_modeles=[OUTIL, EXTRACTION, RESUME], preparations=steps)
    assert agent_config.validate(doc) == []


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"outils_modeles": [{**OUTIL, "type": "traduction"}]}, "outils_modeles[0].type : attendu un type"),
        ({"outils_modeles": [{**OUTIL, "modele": "nimble"}]}, "'nimble' n'est pas permis pour classificateur"),
        ({"outils_modeles": [{**OUTIL, "modele": "glm-5.2"}]}, "modèles permis : clef:27b"),
        ({"outils_modeles": [{**RESUME, "modele": "clef:27b"}]}, "'clef:27b' n'est pas permis pour resume"),
        ({"outils_modeles": [{**RESUME, "modele": "glm-5"}]}, "Vouliez-vous dire 'glm-5.2'"),
        ({"outils_modeles": [{**OUTIL, "seuil": 1}]}, "outils_modeles[0].seuil : attendu une probabilité"),
        ({"outils_modeles": [{**OUTIL, "seuil": True}]}, "outils_modeles[0].seuil"),
        ({"outils_modeles": [{**OUTIL, "question": "Oui ?"}]}, "outils_modeles[0].question : attendu un texte"),
        ({"outils_modeles": [{**OUTIL, "question": "Faut-il prévenir @louije de ceci ?"}]}, "'@louije'"),
        ({"outils_modeles": [{"type": "classificateur"}]}, "exactement les champs type, modele, question, seuil"),
        ({"outils_modeles": [{**RESUME, "seuil": 0.5}]}, "exactement les champs type, modele, longueur_max"),
        ({"outils_modeles": [{**EXTRACTION, "schema": []}]}, "outils_modeles[0].schema : attendu de 1 à 10"),
        ({"outils_modeles": [{**EXTRACTION, "schema": {}}]}, "outils_modeles[0].schema : attendu de 1 à 10"),
        ({"outils_modeles": [{**EXTRACTION, "schema": {f"c{i}": "texte" for i in range(11)}}]}, "de 1 à 10"),
        ({"outils_modeles": [{**EXTRACTION, "schema": {"Produit": "texte"}}]}, "schema.Produit : nom en minuscules"),
        ({"outils_modeles": [{**EXTRACTION, "schema": {"produit": "date"}}]}, "type parmi texte, nombre"),
        ({"outils_modeles": [{**EXTRACTION, "schema": {"p": {"type": "string"}}}]}, "schema.p : nom"),
        ({"outils_modeles": [{**RESUME, "longueur_max": 20}]}, "longueur_max : attendu un nombre de caractères"),
        ({"outils_modeles": [{**RESUME, "longueur_max": 100000}]}, "de 100 à 3000"),
        ({"outils_modeles": [{**RESUME, "longueur_max": "600"}]}, "longueur_max"),
        ({"outils_modeles": [{**RESUME, "longueur_max": True}]}, "longueur_max"),
        ({"outils_modeles": [OUTIL, OUTIL]}, "apparaît plusieurs fois"),
        ({"outils_modeles": [OUTIL, EXTRACTION, RESUME, OUTIL]}, "outils_modeles : attendu une liste de 3"),
        ({"outils_modeles": "classificateur"}, "outils_modeles : attendu une liste"),
        ({"outils_modeles": ["classificateur"]}, "outils_modeles[0].type : attendu un type"),
        ({"preparations": [{"type": "sql", "requete": "select 1"}]}, "attendu un type parmi notion (avec base)"),
        ({"preparations": ["sync-tags"]}, "preparations[0] : attendu un type parmi"),
        ({"preparations": [{"type": "cron", "tache": "sync-tag"}]}, "Vouliez-vous dire 'sync-tags'"),
        ({"preparations": [{"type": "cron", "tache": "run-agents"}]}, "'run-agents' n'est pas une tâche de cron/"),
        ({"preparations": [{"type": "cron", "tache": "../web"}]}, "n'est pas une tâche de cron/"),
        ({"preparations": [{"type": "notion", "base": "https://notion.so/x"}]}, "preparations[0].base"),
        ({"preparations": [{"type": "s3", "jeu": "../secrets.json"}]}, "preparations[0].jeu"),
        ({"preparations": [{"type": "s3", "jeu": "a.csv", "url": "x"}]}, "exactement les champs type et jeu"),
        ({"preparations": [{"type": "cron", "tache": "sync-tags"}] * 2}, "'cron sync-tags' apparaît plusieurs fois"),
        ({"preparations": [{"type": "cron", "tache": "sync-tags"}] * 4}, "preparations : attendu une liste de 3"),
        ({"preparations": "sync-tags"}, "preparations : attendu une liste"),
        ({"cadence": "toutes les heures"}, "cadences permises : quotidienne, hebdomadaire, mensuelle"),
    ],
)
def test_dod_10_unknown_sub_agent_preparation_type_or_cadence_is_refused(overrides, expected):
    errors = agent_config.validate(make_agent(**overrides))
    assert any(expected in e for e in errors), errors


def test_dod_11_cron_preparations_are_the_tasks_of_cron_except_the_generic_agents_cron():
    tasks = agent_config.cron_tasks()
    assert "sync-tags" in tasks
    assert agent_config.GENERIC_CRON not in tasks
    assert (agent_config.config.CRON_DIR / agent_config.GENERIC_CRON / "cron.py").is_file()


def test_dod_10_each_sub_agent_type_has_its_own_ollama_cloud_models():
    assert agent_config.modeles() == {
        "classificateur": ["clef:27b"],
        "extraction": ["glm-5.2", "gemma4:31b"],
        "resume": ["glm-5.2", "gemma4:31b"],
    }
    assert set(agent_config.modeles()) == set(agent_config.SUBAGENT_FIELDS)
