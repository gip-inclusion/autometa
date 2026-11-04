import json

import httpx
import pytest

from lib import agents
from skills.agents.scripts import agents as cli
from tests.test_agent_delivery import FakeStore
from web.database import store as conversations

SLUG = "signaux-faibles-mep"
PIPELINE_ID = "22222222-2222-2222-2222-222222222222"
RUN_ID = "11111111-1111-1111-1111-111111111111"
CONFIG = f"""
format: pdi.agent/1
slug: {SLUG}
titre: Signaux faibles des mises en production
mission: Signaler à l'équipe produit les MEP dont l'effet n'est pas mesurable.
points_de_contact:
  - id: produit.signal_faible
    mode: relecture
"""


class Conversation:
    """The conversation the agent CLI runs in: its id and the id of the latest user message."""

    def __init__(self, mocker):
        self.id, self.last_message = "conv-1", 7
        mocker.patch("lib.agents.config.agent_conversation_id", lambda: self.id)
        mocker.patch("lib.agents.config.agent_user_email", return_value="lj@example.org")
        mocker.patch("lib.agents.last_user_message_id", lambda conversation_id: self.last_message)

    def user_replies(self):
        self.last_message += 2


@pytest.fixture
def store(mocker):
    fake = FakeStore()
    mocker.patch("lib.agent_delivery.s3.agents", fake)
    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", {"produit.signal_faible": "C0SLACK"})
    mocker.patch("lib.agent_delivery.config.AGENT_SLACK_BOT_TOKEN", "agent-bot-token")
    return fake


@pytest.fixture
def conversation(mocker):
    return Conversation(mocker)


@pytest.fixture
def engine(mocker):
    """The jobs engine, faked: one pipeline creation, one completed run of that pipeline."""
    mocker.patch("lib.agents.jobs.create_pipeline", return_value={"id": PIPELINE_ID})
    mocker.patch("lib.agents.jobs.get_run", return_value={"pipeline_id": PIPELINE_ID, "status": "completed"})
    output = {"envois": [{"destination": "produit.signal_faible", "titre": "MEP", "texte": "Effet nul."}]}
    mocker.patch("lib.agents.jobs.get_run_output", return_value=json.dumps(output))
    return agents.jobs


@pytest.fixture
def post(mocker):
    return mocker.patch("lib.agent_delivery.slack.post_message", return_value=True)


def created_agent(conversation):
    proposal = agents.plan(CONFIG, "Tu es analyste produit.")
    conversation.user_replies()
    return agents.apply(proposal["id"])


def test_dod_1_proposal_shows_the_agent_and_creates_no_job(store, conversation, engine):
    proposal = agents.plan(CONFIG, "Tu es analyste produit.")
    assert proposal["status"] == "planned"
    assert proposal["config"]["points_de_contact"] == [{"id": "produit.signal_faible", "mode": "relecture"}]
    assert proposal["system_prompt"].startswith("Tu es analyste produit.")
    assert proposal["shown"] == {"conversation_id": "conv-1", "after_message_id": 7}
    engine.create_pipeline.assert_not_called()
    assert agents.show(proposal["id"]) == proposal


@pytest.mark.parametrize(
    ("config_yaml", "prompt", "message"),
    [
        (CONFIG.replace("produit.signal_faible", "#general"), "Consigne.", "n'est pas une destination"),
        (CONFIG + "webhook: x\n", "Consigne.", "webhook : champ inconnu"),
        (CONFIG, "  ", "consigne du job vide"),
    ],
)
def test_dod_2_refused_configuration_gives_no_proposal(store, conversation, engine, config_yaml, prompt, message):
    with pytest.raises(ValueError, match=message):
        agents.plan(config_yaml, prompt)
    assert store.files == {}


def test_dod_2_slug_already_taken_gives_no_proposal(store, conversation, engine):
    created_agent(conversation)
    count = len(store.files)
    with pytest.raises(ValueError, match="déjà pris"):
        agents.plan(CONFIG, "Tu es analyste produit.")
    assert len(store.files) == count


def test_dod_3_proposal_outside_a_conversation_is_refused(store, conversation, engine):
    conversation.id = None
    with pytest.raises(ValueError, match="dans une conversation"):
        agents.plan(CONFIG, "Consigne.")
    assert store.files == {}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda c: None, "message ultérieur"),
        (lambda c: (c.user_replies(), setattr(c, "id", "conv-2")), "de la conversation"),
        (lambda c: (c.user_replies(), setattr(c, "id", None)), "de la conversation"),
    ],
)
def test_dod_3_creation_without_a_later_message_of_the_same_conversation_creates_nothing(
    store, conversation, engine, change, message
):
    proposal = agents.plan(CONFIG, "Tu es analyste produit.")
    change(conversation)
    with pytest.raises(PermissionError, match=message):
        agents.apply(proposal["id"])
    engine.create_pipeline.assert_not_called()
    assert agents.show(proposal["id"])["status"] == "planned"


def test_dod_4_approval_creates_the_agent_job_with_its_output_contract(store, conversation, engine):
    applied = created_agent(conversation)
    name, prompt, overrides = engine.create_pipeline.call_args.args
    assert name == f"agent-{SLUG}"
    assert prompt.startswith("Tu es analyste produit.")
    assert "destination : une de produit.signal_faible, aucune autre." in prompt
    assert overrides == {"output_format": "json"}
    assert applied["status"] == "applied"
    assert store.json(f"{SLUG}/agent.json")["approved_by"] == "lj@example.org"
    assert store.json(f"{SLUG}/agent.json")["status"] == "actif"


def test_dod_4_jobs_engine_failure_leaves_the_proposal_planned(store, conversation, engine):
    engine.create_pipeline.side_effect = httpx.ConnectError("coupé")
    proposal = agents.plan(CONFIG, "Consigne.")
    conversation.user_replies()
    with pytest.raises(httpx.ConnectError):
        agents.apply(proposal["id"])
    assert agents.show(proposal["id"])["status"] == "planned"
    assert f"{SLUG}/agent.json" not in store.files


def test_dod_5_second_approval_creates_nothing(store, conversation, engine):
    applied = created_agent(conversation)
    conversation.user_replies()
    with pytest.raises(ValueError, match="est applied, attendu planned"):
        agents.apply(applied["id"])
    engine.create_pipeline.assert_called_once()


def test_dod_6_retired_agent_runs_are_no_longer_delivered(store, conversation, engine, post):
    applied = created_agent(conversation)
    assert agents.revert(applied["id"])["status"] == "reverted"
    assert store.json(f"{SLUG}/agent.json")["status"] == "retire"
    with pytest.raises(ValueError, match="aucun agent actif"):
        agents.deliver_run(SLUG, RUN_ID)
    post.assert_not_called()


@pytest.mark.parametrize("applied_first", [False, True])
def test_dod_6_retiring_a_proposal_not_applied_changes_nothing(store, conversation, engine, applied_first):
    proposal = created_agent(conversation) if applied_first else agents.plan(CONFIG, "Consigne.")
    if applied_first:
        agents.revert(proposal["id"])
    expected = "reverted" if applied_first else "planned"
    with pytest.raises(ValueError, match=f"est {expected}, attendu applied"):
        agents.revert(proposal["id"])


@pytest.mark.parametrize("changeset_id", ["2026-11-04-120000-inconnu", "../../x"])
def test_dod_6_unknown_proposal_is_refused(store, changeset_id):
    with pytest.raises(ValueError, match="introuvable"):
        agents.show(changeset_id)


def test_dod_7_completed_run_of_the_agent_job_is_delivered(store, conversation, engine, post):
    created_agent(conversation)
    assert agents.deliver_run(SLUG, RUN_ID) == [
        {"id": f"{RUN_ID}-0", "destination": "produit.signal_faible", "mode": "relecture", "statut": "a_relire"}
    ]
    post.assert_not_called()


@pytest.mark.parametrize(
    ("run", "output", "message"),
    [
        ({"pipeline_id": "autre", "status": "completed"}, "{}", "n'appartient pas"),
        ({"pipeline_id": PIPELINE_ID, "status": "running"}, "{}", "est running, attendu completed"),
        ({"pipeline_id": PIPELINE_ID, "status": "completed"}, "Voici le résultat", "illisible"),
        ({"pipeline_id": PIPELINE_ID, "status": "completed"}, "[]", "sans liste envois"),
    ],
)
def test_dod_7_other_runs_and_unreadable_outputs_are_refused(store, conversation, engine, post, run, output, message):
    created_agent(conversation)
    engine.get_run.return_value = run
    engine.get_run_output.return_value = output
    with pytest.raises(ValueError, match=message):
        agents.deliver_run(SLUG, RUN_ID)
    post.assert_not_called()


def test_dod_7_unknown_agent_is_refused(store):
    with pytest.raises(ValueError, match="aucun agent actif"):
        agents.deliver_run("../x", RUN_ID)


def test_dod_8_review_is_written_only_when_approved_in_a_later_message(store, conversation, engine, post):
    created_agent(conversation)
    agents.deliver_run(SLUG, RUN_ID)
    envoi_id = f"{RUN_ID}-0"
    with pytest.raises(PermissionError, match="jamais présenté"):
        agents.approve_envoi(SLUG, envoi_id)

    assert agents.present_envoi(SLUG, envoi_id)["texte"] == "Effet nul."
    with pytest.raises(PermissionError, match="message ultérieur"):
        agents.approve_envoi(SLUG, envoi_id)
    post.assert_not_called()

    conversation.user_replies()
    assert agents.approve_envoi(SLUG, envoi_id)["statut"] == "envoyee"
    post.assert_called_once()
    assert store.json(f"{SLUG}/envois/{envoi_id}.json")["approuve_par"] == "lj@example.org"


def test_skill_walks_the_whole_flow_and_reports_refusals(store, conversation, engine, post, tmp_path, capsys):
    (tmp_path / "agent.yaml").write_text(CONFIG)
    (tmp_path / "consigne.md").write_text("Tu es analyste produit.")
    assert (
        cli.main(["proposer", "--config", str(tmp_path / "agent.yaml"), "--consigne", str(tmp_path / "consigne.md")])
        == 0
    )
    proposal = json.loads(capsys.readouterr().out)["id"]

    assert cli.main(["creer", proposal]) == 1
    assert "refusé : aucune confirmation" in capsys.readouterr().err

    conversation.user_replies()
    for argv in (["creer", proposal], ["voir", proposal], ["livrer", "--agent", SLUG, "--run", RUN_ID]):
        assert cli.main(argv) == 0
    envoi = ["--agent", SLUG, "--envoi", f"{RUN_ID}-0"]
    assert cli.main(["montrer-envoi", *envoi]) == 0
    conversation.user_replies()
    assert cli.main(["approuver-envoi", *envoi]) == 0
    assert cli.main(["retirer", proposal]) == 0
    post.assert_called_once()


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_dod_3_last_user_message_ignores_assistant_messages_and_other_conversations(app):
    conv, other = conversations.create_conversation(), conversations.create_conversation()
    assert agents.last_user_message_id(conv.id) == 0
    asked = conversations.add_message(conv.id, "user", "Crée l'agent")
    conversations.add_message(conv.id, "assistant", "Je crée cet agent ?")
    conversations.add_message(other.id, "user", "oui")
    assert agents.last_user_message_id(conv.id) == asked.id
    confirmed = conversations.add_message(conv.id, "user", "oui")
    assert agents.last_user_message_id(conv.id) == confirmed.id
