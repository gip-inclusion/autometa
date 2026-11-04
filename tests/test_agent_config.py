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
