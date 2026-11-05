import pytest

from lib import agent_config, agent_delivery
from tests.test_agent_delivery import RUN_ID, SLUG, TARGETS, FakeStore, make_agent, open_real_mode

DESTINATION = "produit.signal_faible"
DIGEST_ID = f"{RUN_ID}-digest-{DESTINATION}"
LABELS = {
    "type": "classificateur",
    "modele": "clef:27b",
    "etiquettes": [
        {"nom": "outils", "question": "La production porte-t-elle sur un outil numérique ?"},
        {"nom": "prestations", "question": "La production porte-t-elle sur une prestation ?"},
    ],
    "seuil": 0.5,
}


@pytest.fixture
def store(mocker):
    fake = FakeStore()
    mocker.patch("lib.agent_delivery.s3.agents", fake)
    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", TARGETS)
    mocker.patch("lib.agent_delivery.config.AGENT_SLACK_BOT_TOKEN", "agent-bot-token")
    return fake


@pytest.fixture
def post(mocker):
    return mocker.patch("lib.agent_delivery.slack.post_message", return_value=True)


def digest_agent(mode="ombre", regroupement="digest"):
    agent = make_agent((DESTINATION, mode))
    agent["points_de_contact"][0]["regroupement"] = regroupement
    return {**agent, "outils_modeles": [LABELS]}


def production(titre, lien=None):
    texte = f"Détails de {titre}." + (f"\n{lien}" if lien else "")
    return {"destination": DESTINATION, "titre": titre, "texte": texte}


def chain(verdicts):
    """Sub-agents faked by title: a list of labels, « ecarte » below the filter, « echec » for a failing link."""

    def run(envoi):
        verdict = verdicts[envoi["titre"]]
        if verdict == "echec":
            return {"envoi": envoi, "etapes": [], "appels": 1, "echec": "sous-agent 1 en échec"}
        if verdict == "ecarte":
            return {"envoi": envoi, "etapes": [{"retenu": False}], "appels": 1, "echec": None}
        return {
            "envoi": {**envoi, "etiquettes": verdict},
            "etapes": [{"etiquettes": verdict}],
            "appels": 1,
            "echec": None,
        }

    return run


VERDICTS = {
    "Logiciel RSA": ["outils"],
    "Plateforme insertion": ["outils", "prestations"],
    "Nettoyage": "ecarte",
    "Divers": [],
}
ENVOIS = [
    production("Logiciel RSA", "https://exemple.fr/avis/1"),
    production("Plateforme insertion", "https://exemple.fr/avis/2"),
    production("Nettoyage", "https://exemple.fr/avis/3"),
    production("Divers"),
]


def test_dod_7_digest_gathers_kept_productions_by_label_with_their_links(store, post):
    summary = agent_delivery.deliver(digest_agent(), RUN_ID, ENVOIS, chain(VERDICTS))

    assert [(e["id"], e["statut"]) for e in summary] == [
        (f"{RUN_ID}-0", "regroupe"),
        (f"{RUN_ID}-1", "regroupe"),
        (f"{RUN_ID}-2", "ecarte"),
        (f"{RUN_ID}-3", "regroupe"),
        (DIGEST_ID, "ombre"),
    ]
    digest = store.json(f"{SLUG}/envois/{DIGEST_ID}.json")
    assert digest["titre"].startswith("Signaux faibles des mises en production, run du ")
    assert digest["titre"].endswith(" : retenus 3, écartés 1")
    assert digest["texte"] == (
        "## outils\n- Logiciel RSA : https://exemple.fr/avis/1\n- Plateforme insertion : https://exemple.fr/avis/2\n\n"
        "## prestations\n- Plateforme insertion : https://exemple.fr/avis/2\n\n"
        "## Autres\n- Divers"
    )
    assert digest["productions"] == [f"{RUN_ID}-0", f"{RUN_ID}-1", f"{RUN_ID}-3"]
    assert store.json(f"{SLUG}/envois/{RUN_ID}-0.json")["digest"] == DIGEST_ID
    assert store.json(f"{SLUG}/envois/{RUN_ID}-2.json")["statut"] == "ecarte"
    post.assert_not_called()


def test_dod_7_digest_with_nothing_kept_says_so(store, post):
    agent_delivery.deliver(digest_agent(), RUN_ID, [production("Nettoyage")], chain(VERDICTS))
    digest = store.json(f"{SLUG}/envois/{DIGEST_ID}.json")
    assert (digest["titre"][-22:], digest["texte"]) == (": retenus 0, écartés 1", "Aucune production retenue.")


def test_dod_7_digest_beyond_its_cap_keeps_the_first_lines_and_counts_the_others(store, post, mocker):
    mocker.patch("lib.agent_delivery.DIGEST_MAX", 90)
    envois = [production(f"Avis {n:02d}", f"https://exemple.fr/{n}") for n in range(10)]
    agent_delivery.deliver(digest_agent(), RUN_ID, envois, chain({e["titre"]: ["outils"] for e in envois}))

    texte = store.json(f"{SLUG}/envois/{DIGEST_ID}.json")["texte"]
    kept, _, omitted = texte.rpartition("\n\n")
    assert kept == "## outils\n- Avis 00 : https://exemple.fr/0\n- Avis 01 : https://exemple.fr/1"
    assert len(kept) <= 90
    assert omitted == "8 lignes omises au-delà de 90 caractères."


def test_dod_7_real_digest_is_posted_once_and_never_rebuilt_on_redelivery(store, post, mocker):
    open_real_mode(mocker)
    agent = digest_agent("reel")
    first = agent_delivery.deliver(agent, RUN_ID, ENVOIS, chain(VERDICTS))
    second = agent_delivery.deliver(agent, RUN_ID, ENVOIS, chain(VERDICTS))

    assert first[-1] == {"id": DIGEST_ID, "destination": DESTINATION, "mode": "reel", "statut": "envoyee", "appels": 0}
    assert [e["statut"] for e in second] == [e["statut"] for e in first]
    post.assert_called_once()
    assert "Plateforme insertion" in post.call_args.args[2]


def test_dod_7_digest_waits_for_productions_whose_sub_agents_failed(store, post):
    agent = digest_agent()
    failing = {**VERDICTS, "Divers": "echec"}
    first = agent_delivery.deliver(agent, RUN_ID, ENVOIS, chain(failing))
    assert [e["id"] for e in first][-1] == f"{RUN_ID}-3"
    assert f"{SLUG}/envois/{DIGEST_ID}.json" not in store.files

    second = agent_delivery.deliver(agent, RUN_ID, ENVOIS, chain(VERDICTS))
    assert second[-1]["id"] == DIGEST_ID
    assert store.json(f"{SLUG}/envois/{DIGEST_ID}.json")["texte"].endswith("## Autres\n- Divers")


def test_dod_7_digest_in_review_is_written_once_approved(store, post, mocker):
    open_real_mode(mocker)
    agent_delivery.deliver(digest_agent("relecture"), RUN_ID, ENVOIS, chain(VERDICTS))
    assert agent_delivery.show(SLUG, DIGEST_ID)["statut"] == "a_relire"
    post.assert_not_called()

    assert agent_delivery.approve(SLUG, DIGEST_ID, "lj@example.org")["statut"] == "envoyee"
    post.assert_called_once()


@pytest.mark.parametrize("regroupement", [None, "unitaire"])
def test_dod_7_unit_delivery_is_unchanged_without_digest(store, post, regroupement):
    agent = digest_agent(regroupement=regroupement)
    if regroupement is None:
        del agent["points_de_contact"][0]["regroupement"]
    summary = agent_delivery.deliver(agent, RUN_ID, ENVOIS, chain(VERDICTS))
    assert [e["statut"] for e in summary] == ["ombre", "ombre", "ecarte", "ombre"]
    assert all("digest" not in store.json(f"{SLUG}/envois/{e['id']}.json") for e in summary)


def test_dod_7_an_unknown_grouping_is_refused_and_a_digest_is_shown_at_review():
    assert agent_config.validate(digest_agent(regroupement="hebdo")) == [
        "points_de_contact[0].regroupement : 'hebdo' inconnu, attendu unitaire ou digest."
    ]
    assert agent_config.describe(digest_agent())[0] == (
        "destination produit.signal_faible en mode ombre, un digest par run (productions retenues regroupées par étiquette)"
    )
