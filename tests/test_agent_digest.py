import pytest

from lib import agent_config, agent_delivery
from tests.test_agent_delivery import RUN_ID, SLUG, TARGETS, FakeStore, make_agent, open_real_mode

DESTINATION = "produit.signal_faible"
DIGEST_ID = f"{RUN_ID}-digest-{DESTINATION}"
LABELS = {
    "type": "classifier",
    "model": "clef:27b",
    "labels": [
        {"name": "outils", "question": "La production porte-t-elle sur un outil numérique ?"},
        {"name": "prestations", "question": "La production porte-t-elle sur une prestation ?"},
    ],
    "threshold": 0.5,
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


def digest_agent(mode="background", grouping="digest"):
    agent = make_agent((DESTINATION, mode))
    agent["destinations"][0]["grouping"] = grouping
    return {**agent, "subagents": [LABELS]}


def production(title, lien=None):
    text = f"Détails de {title}." + (f"\n{lien}" if lien else "")
    return {"destination": DESTINATION, "title": title, "text": text}


def chain(verdicts):
    """Sub-agents faked by title: a list of labels, « ecarte » below the filter, « echec » for a failing link."""

    def run(delivery):
        verdict = verdicts[delivery["title"]]
        if verdict == "failure":
            return {"delivery": delivery, "steps": [], "calls": 1, "failure": "sous-agent 1 en échec"}
        if verdict == "discarded":
            return {"delivery": delivery, "steps": [{"kept": False}], "calls": 1, "failure": None}
        return {
            "delivery": {**delivery, "labels": verdict},
            "steps": [{"labels": verdict}],
            "calls": 1,
            "failure": None,
        }

    return run


VERDICTS = {
    "Logiciel RSA": ["outils"],
    "Plateforme insertion": ["outils", "prestations"],
    "Nettoyage": "discarded",
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

    assert [(e["id"], e["status"]) for e in summary] == [
        (f"{RUN_ID}-0", "grouped"),
        (f"{RUN_ID}-1", "grouped"),
        (f"{RUN_ID}-2", "discarded"),
        (f"{RUN_ID}-3", "grouped"),
        (DIGEST_ID, "recorded"),
    ]
    digest = store.json(f"{SLUG}/envois/{DIGEST_ID}.json")
    assert digest["title"].startswith("Signaux faibles des mises en production, run du ")
    assert digest["title"].endswith(" : retenus 3, écartés 1")
    assert digest["text"] == (
        "## outils\n- Logiciel RSA : https://exemple.fr/avis/1\n- Plateforme insertion : https://exemple.fr/avis/2\n\n"
        "## prestations\n- Plateforme insertion : https://exemple.fr/avis/2\n\n"
        "## Autres\n- Divers"
    )
    assert digest["productions"] == [f"{RUN_ID}-0", f"{RUN_ID}-1", f"{RUN_ID}-3"]
    assert store.json(f"{SLUG}/envois/{RUN_ID}-0.json")["digest"] == DIGEST_ID
    assert store.json(f"{SLUG}/envois/{RUN_ID}-2.json")["status"] == "discarded"
    post.assert_not_called()


def test_dod_7_digest_with_nothing_kept_says_so(store, post):
    agent_delivery.deliver(digest_agent(), RUN_ID, [production("Nettoyage")], chain(VERDICTS))
    digest = store.json(f"{SLUG}/envois/{DIGEST_ID}.json")
    assert (digest["title"][-22:], digest["text"]) == (": retenus 0, écartés 1", "Aucune production retenue.")


def test_dod_7_digest_beyond_its_cap_keeps_the_first_lines_and_counts_the_others(store, post, mocker):
    mocker.patch("lib.agent_delivery.DIGEST_MAX", 90)
    deliveries = [production(f"Avis {n:02d}", f"https://exemple.fr/{n}") for n in range(10)]
    agent_delivery.deliver(digest_agent(), RUN_ID, deliveries, chain({e["title"]: ["outils"] for e in deliveries}))

    text = store.json(f"{SLUG}/envois/{DIGEST_ID}.json")["text"]
    kept, _, omitted = text.rpartition("\n\n")
    assert kept == "## outils\n- Avis 00 : https://exemple.fr/0\n- Avis 01 : https://exemple.fr/1"
    assert len(kept) <= 90
    assert omitted == "8 lignes omises au-delà de 90 caractères."


def test_dod_7_real_digest_is_posted_once_and_never_rebuilt_on_redelivery(store, post, mocker):
    open_real_mode(mocker)
    agent = digest_agent("autonomous")
    first = agent_delivery.deliver(agent, RUN_ID, ENVOIS, chain(VERDICTS))
    second = agent_delivery.deliver(agent, RUN_ID, ENVOIS, chain(VERDICTS))

    assert first[-1] == {
        "id": DIGEST_ID,
        "destination": DESTINATION,
        "mode": "autonomous",
        "status": "sent",
        "calls": 0,
    }
    assert [e["status"] for e in second] == [e["status"] for e in first]
    post.assert_called_once()
    assert "Plateforme insertion" in post.call_args.args[2]


def test_dod_7_digest_waits_for_productions_whose_sub_agents_failed(store, post):
    agent = digest_agent()
    failing = {**VERDICTS, "Divers": "failure"}
    first = agent_delivery.deliver(agent, RUN_ID, ENVOIS, chain(failing))
    assert [e["id"] for e in first][-1] == f"{RUN_ID}-3"
    assert f"{SLUG}/envois/{DIGEST_ID}.json" not in store.files

    second = agent_delivery.deliver(agent, RUN_ID, ENVOIS, chain(VERDICTS))
    assert second[-1]["id"] == DIGEST_ID
    assert store.json(f"{SLUG}/envois/{DIGEST_ID}.json")["text"].endswith("## Autres\n- Divers")


def test_dod_7_digest_in_review_is_written_once_approved(store, post, mocker):
    open_real_mode(mocker)
    agent_delivery.deliver(digest_agent("conversational"), RUN_ID, ENVOIS, chain(VERDICTS))
    assert agent_delivery.show(SLUG, DIGEST_ID)["status"] == "pending_review"
    post.assert_not_called()

    assert agent_delivery.approve(SLUG, DIGEST_ID, "lj@example.org")["status"] == "sent"
    post.assert_called_once()


@pytest.mark.parametrize("grouping", [None, "single"])
def test_dod_7_unit_delivery_is_unchanged_without_digest(store, post, grouping):
    agent = digest_agent(grouping=grouping)
    if grouping is None:
        del agent["destinations"][0]["grouping"]
    summary = agent_delivery.deliver(agent, RUN_ID, ENVOIS, chain(VERDICTS))
    assert [e["status"] for e in summary] == ["recorded", "recorded", "discarded", "recorded"]
    assert all("digest" not in store.json(f"{SLUG}/envois/{e['id']}.json") for e in summary)


def test_dod_7_an_unknown_grouping_is_refused_and_a_digest_is_shown_at_review():
    assert agent_config.validate(digest_agent(grouping="hebdo")) == [
        "destinations[0].grouping : 'hebdo' inconnu, attendu single ou digest."
    ]
    assert agent_config.describe(digest_agent())[0] == (
        "destination produit.signal_faible en mode background, un digest par run (productions retenues regroupées par étiquette)"
    )
