import json
import re

import httpx
import pytest

from lib import agent_config, agents
from tests.test_agent_delivery import FakeStore
from tests.test_agents import PIPELINE_ID, RUN_ID, Conversation
from web import config

CONFIG = (config.BASE_DIR / "agents" / "veille-boamp.yaml").read_text()
CONSIGNE = (config.BASE_DIR / "agents" / "veille-boamp.md").read_text()
DIGEST = {
    "envois": [
        {
            "destination": "bizdev.marche",
            "titre": "Veille BOAMP du 2026-10-28 au 2026-11-03 : 1 avis",
            "texte": (
                "## Outils numériques\n\n"
                "- Logiciel de suivi des parcours d'insertion des bénéficiaires du RSA : Département fictif (99), "
                "réponse avant le 04/12/2026 : https://www.boamp.fr/pages/avis/?q=idweb:26-000001\n\n"
                "1 158 avis lus, 1 retenu."
            ),
        }
    ]
}


@pytest.fixture
def store(mocker):
    fake = FakeStore()
    mocker.patch("lib.agent_delivery.s3.agents", fake)
    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", {"bizdev.marche": "C0BIZDEV"})
    return fake


@pytest.fixture
def offline(mocker):
    """No network at all: BOAMP, Slack, Notion and the jobs engine would all go through httpx."""
    return mocker.patch("httpx.Client.send", side_effect=AssertionError("appel réseau"))


def test_dod_1_boamp_agent_writes_only_to_the_bizdev_slack_channel_in_shadow():
    doc = agent_config.parse(CONFIG)
    assert agent_config.validate(doc) == []
    assert doc["points_de_contact"] == [{"id": "bizdev.marche", "mode": "ombre"}]
    assert agent_config.destinations()["bizdev.marche"]["canal"] == "slack"


def test_dod_2_job_prompt_reads_only_the_public_boamp_api():
    hosts = {re.match(r"https?://([^/\s]+)", url).group(1) for url in re.findall(r"https?://\S+", CONSIGNE)}
    assert hosts == {"boamp-datadila.opendatasoft.com"}
    for rule in ('nature=\\"APPEL_OFFRE\\"', 'etat=\\"INITIAL\\"', "7 jours", "url_avis", '{"envois": []}'):
        assert rule in CONSIGNE


def test_dod_2_job_prompt_and_digest_carry_no_long_dash():
    assert not re.search("[\u2013\u2014]", CONSIGNE + DIGEST["envois"][0]["texte"])


def test_dod_4_repository_agent_registers_through_the_creation_flow(store, mocker, offline):
    conversation = Conversation(mocker)
    create = mocker.patch("lib.agents.jobs.create_pipeline", return_value={"id": PIPELINE_ID})
    proposal = agents.plan(CONFIG, CONSIGNE)
    create.assert_not_called()
    assert proposal["system_prompt"].startswith(CONSIGNE)
    assert "destination : une de bizdev.marche, aucune autre." in proposal["system_prompt"]
    conversation.user_replies()
    assert agents.apply(proposal["id"])["status"] == "applied"
    create.assert_called_once_with("agent-veille-boamp", proposal["system_prompt"], {"output_format": "json"})


def test_dod_5_boamp_digest_is_recorded_in_shadow_and_written_nowhere(store, mocker, offline):
    conversation = Conversation(mocker)
    mocker.patch("lib.agents.jobs.create_pipeline", return_value={"id": PIPELINE_ID})
    mocker.patch("lib.agents.jobs.get_run", return_value={"pipeline_id": PIPELINE_ID, "status": "completed"})
    mocker.patch("lib.agents.jobs.get_run_output", return_value=json.dumps(DIGEST))
    slack = mocker.patch("lib.agent_delivery.slack.post_message")
    notion = mocker.patch("lib.agent_delivery.notion.create_page")
    proposal = agents.plan(CONFIG, CONSIGNE)
    conversation.user_replies()
    agents.apply(proposal["id"])

    summary = agents.deliver_run("veille-boamp", RUN_ID)

    envoi_id = f"{RUN_ID}-0"
    assert summary == [{"id": envoi_id, "destination": "bizdev.marche", "mode": "ombre", "statut": "ombre"}]
    assert store.json(f"veille-boamp/envois/{envoi_id}.json")["texte"] == DIGEST["envois"][0]["texte"]
    slack.assert_not_called()
    notion.assert_not_called()
    offline.assert_not_called()
    with pytest.raises(AssertionError, match="appel réseau"):
        httpx.get("https://boamp-datadila.opendatasoft.com", timeout=5)
