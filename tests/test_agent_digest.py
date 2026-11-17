from datetime import datetime, timezone

import pytest

from lib import agent_config, agent_delivery
from tests.test_agent_delivery import RUN_ID, TARGETS, Rows, make_agent, open_real_mode, registered
from tests.test_agent_delivery import deliver as deliver_run
from web.db import get_db
from web.db import test_transaction as _test_tx
from web.models import AgentRun

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

DESTINATION = "produit.signal_faible"
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
    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", TARGETS)
    mocker.patch("lib.agent_delivery.config.AGENT_SLACK_BOT_TOKEN", "agent-bot-token")
    with _test_tx():
        yield Rows()


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


def deliver(mocker, agent, deliveries, verdicts):
    return deliver_run(mocker, agent, deliveries, chain=chain(verdicts))


def digest(rows: Rows) -> dict:
    return next(d for d in rows.deliveries() if d["rank"] is None)


def test_dod_7_digest_gathers_kept_productions_by_label_with_their_links(store, post, mocker):
    summary = deliver(mocker, digest_agent(), ENVOIS, VERDICTS)

    assert [e["status"] for e in summary] == ["grouped", "grouped", "discarded", "grouped", "recorded"]
    found = digest(store)
    assert found["title"].startswith("Signaux faibles des mises en production, run du ")
    assert found["title"].endswith(" : retenus 3, écartés 1")
    assert found["text"] == (
        "## outils\n- Logiciel RSA : https://exemple.fr/avis/1\n- Plateforme insertion : https://exemple.fr/avis/2\n\n"
        "## prestations\n- Plateforme insertion : https://exemple.fr/avis/2\n\n"
        "## Autres\n- Divers"
    )
    assert [d["rank"] for d in store.deliveries() if d["digest_id"] == found["id"]] == [0, 1, 3]
    assert store.delivery(2)["status"] == "discarded"
    post.assert_not_called()


def test_dod_7_digest_with_nothing_kept_says_so(store, post, mocker):
    deliver(mocker, digest_agent(), [production("Nettoyage")], VERDICTS)
    found = digest(store)
    assert (found["title"][-22:], found["text"]) == (": retenus 0, écartés 1", "Aucune production retenue.")


def test_dod_7_digest_beyond_its_cap_keeps_the_first_lines_and_counts_the_others(store, post, mocker):
    mocker.patch("lib.agent_delivery.DIGEST_MAX", 90)
    deliveries = [production(f"Avis {n:02d}", f"https://exemple.fr/{n}") for n in range(10)]
    deliver(mocker, digest_agent(), deliveries, {e["title"]: ["outils"] for e in deliveries})

    kept, _, omitted = digest(store)["text"].rpartition("\n\n")
    assert kept == "## outils\n- Avis 00 : https://exemple.fr/0\n- Avis 01 : https://exemple.fr/1"
    assert len(kept) <= 90
    assert omitted == "8 lignes omises au-delà de 90 caractères."


def test_dod_7_autonomous_digest_is_posted_once_and_never_rebuilt_on_redelivery(store, post, mocker):
    open_real_mode(mocker)
    agent = digest_agent("autonomous")
    first = deliver(mocker, agent, ENVOIS, VERDICTS)
    second = deliver(mocker, agent, ENVOIS, VERDICTS)

    assert first[-1] == {
        "id": digest(store)["id"],
        "destination": DESTINATION,
        "mode": "autonomous",
        "status": "sent",
        "calls": 0,
    }
    assert [e["status"] for e in second] == [e["status"] for e in first]
    post.assert_called_once()
    assert "Plateforme insertion" in post.call_args.args[2]


def test_dod_7_digest_waits_for_productions_whose_sub_agents_failed(store, post, mocker):
    agent = digest_agent()
    first = deliver(mocker, agent, ENVOIS, {**VERDICTS, "Divers": "failure"})
    assert first[-1]["status"] == "pending_subagents"
    assert all(d["rank"] is not None for d in store.deliveries())

    second = deliver(mocker, agent, ENVOIS, VERDICTS)
    assert second[-1]["id"] == digest(store)["id"]
    assert digest(store)["text"].endswith("## Autres\n- Divers")


def test_tutorial_gap_2_digest_is_dated_by_its_run_not_by_its_building(store, post, mocker):
    agent = digest_agent()
    registered(agent)
    with get_db() as session:
        session.get(AgentRun, RUN_ID).launched_at = datetime(2026, 11, 9, 8, tzinfo=timezone.utc)
    deliver(mocker, agent, ENVOIS, VERDICTS)
    assert "run du 09/11/2026 :" in digest(store)["title"]


def test_review_2_5_a_sub_agent_failing_every_time_is_set_aside_and_the_digest_goes_on(store, post, mocker):
    """Review 2.5: an identical failure used to hold the digest for ever."""
    agent, failing = digest_agent(), {**VERDICTS, "Divers": "failure"}
    for _ in range(agent_delivery.SUBAGENT_ATTEMPTS_MAX):
        summary = deliver(mocker, agent, ENVOIS, failing)
    assert summary[3]["status"] == "subagent_failed"
    assert digest(store)["title"].endswith(" : retenus 2, écartés 2")


def test_dod_7_digest_in_review_is_written_once_approved(store, post, mocker):
    open_real_mode(mocker)
    deliver(mocker, digest_agent("conversational"), ENVOIS, VERDICTS)
    assert digest(store)["status"] == "pending_review"
    post.assert_not_called()

    assert agent_delivery.approve(digest(store)["id"], "lj@example.org") == "sent"
    post.assert_called_once()


@pytest.mark.parametrize("grouping", [None, "single"])
def test_dod_7_unit_delivery_is_unchanged_without_digest(store, post, mocker, grouping):
    agent = digest_agent(grouping=grouping)
    if grouping is None:
        del agent["destinations"][0]["grouping"]
    summary = deliver(mocker, agent, ENVOIS, VERDICTS)
    assert [e["status"] for e in summary] == ["recorded", "recorded", "discarded", "recorded"]
    assert all(d["digest_id"] is None for d in store.deliveries())


def test_dod_7_an_unknown_grouping_is_refused_and_a_digest_is_shown_at_review():
    assert agent_config.validate(digest_agent(grouping="hebdo")) == [
        "destinations[0].grouping : 'hebdo' inconnu, attendu single ou digest."
    ]
    assert agent_config.describe(digest_agent())[0] == (
        "destination produit.signal_faible en mode background, un digest par run (productions retenues regroupées par étiquette)"
    )
