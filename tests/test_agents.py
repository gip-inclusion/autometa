import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from lib import agents
from skills.agents.scripts import agents as cli
from tests.test_agent_connectors import FakeGitHub
from tests.test_agent_delivery import Rows
from web.database import store as conversations
from web.db import get_db
from web.db import test_transaction as _test_tx
from web.models import Agent, AgentFileVersion

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

SLUG = "signaux-faibles-mep"
PIPELINE_ID = "22222222-2222-2222-2222-222222222222"
RUN_ID = "11111111-1111-1111-1111-111111111111"
CONFIG = f"""
format: pdi.agent/1
slug: {SLUG}
title: Signaux faibles des mises en production
mission: Signaler à l'équipe produit les MEP dont l'effet n'est pas mesurable.
destinations:
  - id: produit.signal_faible
    mode: conversational
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
    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", {"produit.signal_faible": "C0SLACK"})
    mocker.patch("lib.agent_delivery.config.AGENT_SLACK_BOT_TOKEN", "agent-bot-token")
    with _test_tx():
        yield Rows()


@pytest.fixture
def conversation(mocker):
    return Conversation(mocker)


@pytest.fixture
def engine(mocker):
    """The jobs engine, faked: one pipeline creation, one completed run of that pipeline."""
    mocker.patch("lib.agents.jobs.create_pipeline", return_value={"id": PIPELINE_ID})
    mocker.patch("lib.agents.jobs.get_run", return_value={"pipeline_id": PIPELINE_ID, "status": "completed"})
    output = {"deliveries": [{"destination": "produit.signal_faible", "title": "MEP", "text": "Effet nul."}]}
    mocker.patch("lib.agents.jobs.get_run_output", return_value=json.dumps(output))
    return agents.jobs


@pytest.fixture
def post(mocker):
    return mocker.patch("lib.agent_delivery.slack.post_message", return_value=True)


def created_agent(conversation):
    proposal = agents.plan(CONFIG, "Tu es analyste produit.")
    conversation.user_replies()
    return agents.apply(proposal["id"])


def retire(conversation, changeset_id):
    """Retire as the skill does: shown first, then confirmed in a later message."""
    agents.present_retire(changeset_id)
    conversation.user_replies()
    return agents.revert(changeset_id)


def test_dod_1_proposal_shows_the_agent_and_creates_no_job(store, conversation, engine):
    proposal = agents.plan(CONFIG, "Tu es analyste produit.")
    assert proposal["status"] == "planned"
    assert proposal["config"]["destinations"] == [{"id": "produit.signal_faible", "mode": "conversational"}]
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
    assert store.size() == 0


def test_dod_2_slug_of_a_retired_agent_gives_no_proposal(store, conversation, engine):
    retire(conversation, created_agent(conversation)["id"])
    count = store.size()
    with pytest.raises(ValueError, match="déjà pris par un agent retiré"):
        agents.plan(CONFIG, "Tu es analyste produit.")
    assert store.size() == count


def test_dod_3_proposal_outside_a_conversation_is_refused(store, conversation, engine):
    conversation.id = None
    with pytest.raises(ValueError, match="dans une conversation"):
        agents.plan(CONFIG, "Consigne.")
    assert store.size() == 0


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
    assert store.agent(SLUG)["owner_email"] == "lj@example.org"
    assert store.agent(SLUG)["status"] == "active"


def test_dod_4_jobs_engine_failure_leaves_the_proposal_planned(store, conversation, engine):
    engine.create_pipeline.side_effect = httpx.ConnectError("coupé")
    proposal = agents.plan(CONFIG, "Consigne.")
    conversation.user_replies()
    with pytest.raises(httpx.ConnectError):
        agents.apply(proposal["id"])
    assert agents.show(proposal["id"])["status"] == "planned"
    assert store.agent(SLUG) is None


def test_dod_5_second_approval_creates_nothing(store, conversation, engine):
    applied = created_agent(conversation)
    conversation.user_replies()
    with pytest.raises(ValueError, match="est applied, attendu planned"):
        agents.apply(applied["id"])
    engine.create_pipeline.assert_called_once()


def test_dod_6_retired_agent_runs_are_no_longer_delivered(store, conversation, engine, post):
    applied = created_agent(conversation)
    assert retire(conversation, applied["id"])["status"] == "reverted"
    assert store.agent(SLUG)["status"] == "retired"
    with pytest.raises(ValueError, match="aucun agent actif"):
        agents.deliver_run(SLUG, RUN_ID)
    post.assert_not_called()


@pytest.mark.parametrize("applied_first", [False, True])
def test_dod_6_retiring_a_proposal_not_applied_changes_nothing(store, conversation, engine, applied_first):
    proposal = created_agent(conversation) if applied_first else agents.plan(CONFIG, "Consigne.")
    if applied_first:
        retire(conversation, proposal["id"])
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
        {
            "id": store.delivery()["id"],
            "destination": "produit.signal_faible",
            "mode": "conversational",
            "status": "pending_review",
            "calls": 0,
        }
    ]
    post.assert_not_called()


@pytest.mark.parametrize(
    ("run", "output", "message"),
    [
        ({"pipeline_id": "autre", "status": "completed"}, "{}", "n'appartient pas"),
        ({"pipeline_id": PIPELINE_ID, "status": "running"}, "{}", "est launched : pas encore terminé"),
        ({"pipeline_id": PIPELINE_ID, "status": "completed"}, "Voici le résultat", "illisible"),
        ({"pipeline_id": PIPELINE_ID, "status": "completed"}, "[]", "deliveries : attendu une liste"),
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
    delivery_id = str(store.delivery()["id"])
    with pytest.raises(PermissionError, match="envoi jamais proposé"):
        agents.approve_delivery(SLUG, delivery_id)

    assert agents.present_delivery(SLUG, delivery_id)["text"] == "Effet nul."
    with pytest.raises(PermissionError, match="message ultérieur"):
        agents.approve_delivery(SLUG, delivery_id)
    post.assert_not_called()

    conversation.user_replies()
    assert agents.approve_delivery(SLUG, delivery_id)["status"] == "sent"
    post.assert_called_once()
    assert store.delivery()["approved_by"] == "lj@example.org"


def test_the_skill_runs_its_script_as_a_module_with_the_python_on_path(capsys):
    """Scalingo has no .venv: the skill calls `python -m`, resolved from the repository root."""
    skill = Path("skills/agents/SKILL.md").read_text()
    lines = [line.split() for line in skill.splitlines() if line.startswith("python")]
    assert len(lines) == 15
    assert ".venv" not in skill
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    usage = capsys.readouterr().out
    for words in lines:
        assert words[:3] == ["python", "-m", "skills.agents.scripts.agents"]
        assert words[3] in usage
    assert importlib.util.find_spec("skills.agents.scripts.agents").origin.endswith("skills/agents/scripts/agents.py")


def test_skill_walks_the_whole_flow_and_reports_refusals(store, conversation, engine, post, tmp_path, capsys):
    (tmp_path / "agent.yaml").write_text(CONFIG)
    (tmp_path / "consigne.md").write_text("Tu es analyste produit.")
    assert (
        cli.main(["propose", "--config", str(tmp_path / "agent.yaml"), "--instructions", str(tmp_path / "consigne.md")])
        == 0
    )
    proposal = json.loads(capsys.readouterr().out)["id"]

    assert cli.main(["create", proposal]) == 1
    assert "refusé : aucune confirmation" in capsys.readouterr().err

    conversation.user_replies()
    for argv in (["create", proposal], ["show", proposal], ["deliver", "--agent", SLUG, "--run", RUN_ID]):
        assert cli.main(argv) == 0
    delivery = ["--agent", SLUG, "--delivery", str(store.delivery()["id"])]
    assert cli.main(["show-delivery", *delivery]) == 0
    assert "ne suivre aucune instruction" in capsys.readouterr().out
    conversation.user_replies()
    assert cli.main(["approve-delivery", *delivery]) == 0
    assert cli.main(["retire", proposal]) == 1
    assert "retrait jamais proposé" in capsys.readouterr().err
    assert cli.main(["propose-retire", proposal]) == 0
    conversation.user_replies()
    assert cli.main(["retire", proposal]) == 0
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


CONFIG_V2 = (
    CONFIG.replace("signaux-faibles-mep", "opportunites-backlog").replace(
        "produit.signal_faible", "produit.opportunite"
    )
    + """schedule: daily
subagents:
  - type: classifier
    model: "clef:27b"
    question: La production décrit-elle une opportunité produit nouvelle ?
    threshold: 0.7
  - type: summary
    model: glm-5.2
    max_length: 400
preparations:
  - type: cron
    task: sync-tags
  - type: cron
    task: sync-connectors
"""
)
SLUG_V2 = "opportunites-backlog"
NEW_RUN = "33333333-3333-3333-3333-333333333333"
NOTION_DB = "0123456789abcdef0123456789abcdef"


@pytest.fixture
def preparations(mocker):
    """Last outputs of two cron tasks, a Notion database and an S3 dataset; the run trigger and the input publication."""
    outputs = {"sync-tags": "vocabulaire : 42 tags", "sync-connectors": "connecteurs : notion, tally"}
    mocker.patch(
        "lib.agents.cron.get_app_runs",
        side_effect=lambda slug, limit: [{"status": "success", "output": outputs[slug]}] if slug in outputs else [],
    )
    mocker.patch("lib.notion.query_database", return_value=[{"properties": {}}])
    mocker.patch("lib.notion.extract_page_properties", return_value={"Nom": "Export CSV"})
    mocker.patch("lib.notion.NOTION_TOKEN", "notion-token")
    mocker.patch("web.s3.job_inputs.get_url", return_value="https://s3/services.sqlite")
    mocker.patch("web.s3.job_inputs.exists", return_value=True)
    publish = mocker.patch("lib.agents.job_inputs.publish_dataset", return_value={"url": "https://s3/entree.jsonl"})
    mocker.patch("lib.agents.jobs.trigger_run", return_value={"id": NEW_RUN})
    return publish


def created_v2(conversation, mocker, config_yaml=CONFIG_V2):
    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", {})
    proposal = agents.plan(config_yaml, "Tu lis le backlog produit.")
    conversation.user_replies()
    return agents.apply(proposal["id"])


def ollama_says(mocker, *probabilities, summary="Résumé."):
    """Ollama Cloud mocked: clef answers the probabilities in turn, the chat models the summary."""
    answers = iter(probabilities)

    def reply(path, payload):
        if path == "v1/systemone":
            return {"answers": {"retenir": {"type": "noul", "noul": next(answers)}}}
        return {"message": {"role": "assistant", "content": summary}}

    return mocker.patch("lib.agent_subagents.ollama", side_effect=reply)


def runs_output(engine, *titles):
    deliveries = [{"destination": "produit.opportunite", "title": t, "text": f"{t}, détails."} for t in titles]
    engine.get_run_output.return_value = json.dumps({"deliveries": deliveries})


def test_dod_9_guide_lists_what_an_agent_may_use_even_when_no_destination_has_a_target(store, mocker, capsys):
    mocker.patch("lib.agents.config.AGENT_DESTINATION_TARGETS", {})
    mocker.patch("lib.agents.config.OLLAMA_API_KEY", "")
    assert cli.main(["destinations"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert {d["id"] for d in listed["destinations"]} == {
        "produit.signal_faible",
        "bizdev.marche",
        "produit.opportunite",
    }
    assert not any(d["target_configured"] for d in listed["destinations"])
    assert listed["subagents"]["classifier"] == ["clef:27b"]
    assert set(listed["subagents"]) == {"classifier", "extraction", "summary"}
    assert list(listed["preparations"]) == ["notion", "github", "url", "s3", "cron"]
    assert {"base", "page", "filter", "cap"} <= set(listed["preparations"]["notion"]["fields"])
    assert {"repos", "organization", "repo_cap"} <= set(listed["preparations"]["github"]["fields"])
    assert "sync-tags" in listed["cron_tasks"]
    assert "run-agents" not in listed["cron_tasks"]
    assert listed["schedules"]["weekdays"][0] == "monday"
    assert listed["schedules"]["shortcuts"] == ["daily", "weekly", "monthly"]
    assert listed["files"] == {"at_most": 5, "max_size": 100000}
    assert listed["subagents_configured"] is False


def test_dod_9_proposal_without_any_target_shows_classifier_preparations_and_cadence(
    store, conversation, engine, mocker
):
    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", {})
    proposal = agents.plan(CONFIG_V2, "Tu lis le backlog produit.")
    assert proposal["kind"] == "create"
    assert proposal["config"]["schedule"] == "daily"
    assert proposal["config"]["subagents"][0]["threshold"] == 0.7
    assert "dans cet ordre : cron sync-tags, cron sync-connectors." in proposal["system_prompt"]
    engine.create_pipeline.assert_not_called()


def test_dod_10_productions_under_the_threshold_are_kept_but_not_delivered(store, conversation, engine, mocker, post):
    created_v2(conversation, mocker)
    runs_output(engine, "Export CSV", "Bruit")
    ollama_says(mocker, 0.91, 0.2)
    summary = agents.deliver_run(SLUG_V2, RUN_ID)
    assert [s["status"] for s in summary] == ["pending_review", "discarded"]
    assert [s["calls"] for s in summary] == [2, 1]
    assert store.delivery(0)["text"] == "Résumé."
    kept = store.delivery(1)
    assert kept["subagent_steps"] == [
        {"type": "classifier", "model": "clef:27b", "probability": 0.2, "threshold": 0.7, "kept": False}
    ]
    assert kept["text"] == "Bruit, détails."
    assert store.run().subagent_calls == 3
    with pytest.raises(ValueError, match="est discarded"):
        agents.agent_delivery.approve(store.delivery(1)["id"], "lj@example.org")


def test_dod_10_a_failing_sub_agent_delivers_nothing_of_that_production_and_is_retried(
    store, conversation, engine, mocker, caplog
):
    created_v2(conversation, mocker)
    runs_output(engine, "Export CSV")
    mocker.patch("lib.agent_subagents.config.OLLAMA_API_KEY", "")
    with caplog.at_level("INFO"):
        summary = agents.deliver_run(SLUG_V2, RUN_ID)
    assert [s["status"] for s in summary] == ["pending_subagents"]
    record = store.delivery(0)
    assert "sous-agent 1 (classifier clef:27b) en échec : OLLAMA_API_KEY absent" in record["error"]
    assert "Export CSV" not in caplog.text
    with pytest.raises(ValueError, match="est pending_subagents"):
        agents.agent_delivery.approve(store.delivery(0)["id"], "lj@example.org")

    ollama_says(mocker, 0.9)
    assert [s["status"] for s in agents.deliver_run(SLUG_V2, RUN_ID)] == ["pending_review"]
    assert store.delivery(0)["text"] == "Résumé."
    assert store.run().subagent_calls == 3


def test_dod_11_preparations_feed_the_run_in_order_from_their_three_types(
    store, conversation, engine, mocker, preparations
):
    steps = f"  - type: notion\n    base: {NOTION_DB}\n  - type: s3\n    dataset: services.sqlite\n"
    created_v2(conversation, mocker, CONFIG_V2.replace("  - type: cron\n    task: sync-connectors\n", steps))
    assert agents.execute(SLUG_V2)["preparations"] == [
        "cron sync-tags",
        f"notion base {NOTION_DB}",
        "s3 services.sqlite",
    ]
    _, columns, rows = preparations.call_args.args
    assert columns == ["order", "type", "source", "content"]
    assert rows == [
        [1, "cron", "sync-tags", "vocabulaire : 42 tags"],
        [
            2,
            "notion",
            f"base {NOTION_DB}",
            "1 lignes.\n\n| Nom | derniere_modification |\n|---|---|\n| Export CSV |  |",
        ],
        [3, "s3", "services.sqlite", "https://s3/services.sqlite"],
    ]
    agents.jobs.trigger_run.assert_called_once_with(
        PIPELINE_ID, input_uri="https://s3/entree.jsonl", idempotency_key=None
    )
    assert store.launched() == [NEW_RUN]


def test_dod_11_agent_without_preparations_runs_without_input(store, conversation, engine, mocker, preparations):
    created_agent(conversation)
    agents.execute(SLUG)
    agents.jobs.trigger_run.assert_called_once_with(PIPELINE_ID, input_uri=None, idempotency_key=None)
    preparations.assert_not_called()


@pytest.mark.parametrize(
    ("break_it", "message"),
    [
        (lambda m: m.patch("lib.agents.cron.get_app_runs", return_value=[]), "cron sync-tags : pas de dernière sortie"),
        (
            lambda m: m.patch("lib.agents.cron.get_app_runs", return_value=[{"status": "failure", "output": "x"}]),
            "pas de dernière sortie réussie",
        ),
    ],
)
def test_dod_11_a_preparation_without_content_launches_no_run(
    store, conversation, engine, mocker, preparations, break_it, message
):
    created_v2(conversation, mocker)
    break_it(mocker)
    with pytest.raises(ValueError, match=message):
        agents.execute(SLUG_V2)
    agents.jobs.trigger_run.assert_not_called()


def test_dod_11_missing_s3_dataset_launches_no_run(store, conversation, engine, mocker, preparations):
    created_v2(conversation, mocker, CONFIG_V2 + "  - type: s3\n    dataset: absent.csv\n")
    mocker.patch("web.s3.job_inputs.exists", return_value=False)
    with pytest.raises(ValueError, match="s3 absent.csv : jeu introuvable"):
        agents.execute(SLUG_V2)
    agents.jobs.trigger_run.assert_not_called()


def test_dod_12_generic_cron_delivers_finished_runs_then_launches_due_agents(
    store, conversation, engine, mocker, post, preparations
):
    created_v2(conversation, mocker)
    agents.execute(SLUG_V2)
    ollama_says(mocker, 0.9)
    mocker.patch("lib.agents.cron.is_due", return_value=True)
    runs_output(engine, "Export")
    agents.jobs.trigger_run.return_value = {"id": "44444444-4444-4444-4444-444444444444"}

    agents.tick()

    assert store.delivery(0, NEW_RUN)["status"] == "pending_review"
    assert store.launched() == ["44444444-4444-4444-4444-444444444444"]
    assert agents.jobs.trigger_run.call_args.kwargs["idempotency_key"].startswith(f"agent-{SLUG_V2}-")


def test_dod_12_a_run_whose_sub_agent_failed_stays_pending_and_the_cron_reports_it(
    store, conversation, engine, mocker, post, preparations
):
    created_v2(conversation, mocker)
    agents.execute(SLUG_V2)
    mocker.patch("lib.agent_subagents.config.OLLAMA_API_KEY", "")
    mocker.patch("lib.agents.cron.is_due", return_value=True)
    runs_output(engine, "Export")
    agents.jobs.trigger_run.return_value = {"id": "44444444-4444-4444-4444-444444444444"}

    with pytest.raises(RuntimeError, match="sous-agent en échec"):
        agents.tick()

    assert store.delivery(0, NEW_RUN)["status"] == "pending_subagents"
    assert store.launched() == ["44444444-4444-4444-4444-444444444444"]
    post.assert_not_called()


def test_dod_12_generic_cron_skips_running_runs_retired_and_on_demand_agents(
    store, conversation, engine, mocker, preparations
):
    applied = created_agent(conversation)
    mocker.patch("lib.agents.cron.is_due", return_value=True)
    agents.execute(SLUG)
    engine.get_run.return_value = {"pipeline_id": PIPELINE_ID, "status": "running"}
    agents.tick()
    assert agents.jobs.trigger_run.call_count == 1
    assert store.launched() == [NEW_RUN]

    retire(conversation, applied["id"])
    agents.tick()
    assert agents.jobs.trigger_run.call_count == 1


def test_dod_12_one_failing_agent_does_not_stop_the_others(store, conversation, engine, mocker, preparations):
    created_v2(conversation, mocker)
    agents.execute(SLUG_V2)
    engine.get_run.side_effect = httpx.ConnectError("coupé")
    mocker.patch("lib.agents.cron.is_due", return_value=True)
    with pytest.raises(RuntimeError, match="collecte en échec : coupé"):
        agents.tick()
    assert agents.jobs.trigger_run.call_count == 2


def test_dod_13_a_run_now_needs_a_later_message_and_the_confirmation_is_spent(
    store, conversation, engine, mocker, preparations
):
    created_v2(conversation, mocker)
    with pytest.raises(PermissionError, match="lancement jamais proposé"):
        agents.launch(SLUG_V2)
    assert agents.present_launch(SLUG_V2)["preparations"][0] == {"type": "cron", "task": "sync-tags"}
    with pytest.raises(PermissionError, match="message ultérieur"):
        agents.launch(SLUG_V2)
    agents.jobs.trigger_run.assert_not_called()

    conversation.user_replies()
    assert agents.launch(SLUG_V2)["run_id"] == NEW_RUN
    with pytest.raises(PermissionError, match="lancement jamais proposé"):
        agents.launch(SLUG_V2)
    agents.jobs.trigger_run.assert_called_once()


def test_dod_13_changing_an_agent_is_a_confirmed_proposal_and_reverts_to_what_it_replaced(
    store, conversation, engine, mocker
):
    created_v2(conversation, mocker)
    engine.create_pipeline.reset_mock()
    weekly = agents.plan(CONFIG_V2.replace("daily", "weekly"), "Tu lis le backlog produit.")
    assert weekly["kind"] == "update"
    assert store.agent(SLUG_V2)["config"]["schedule"] == "daily"
    with pytest.raises(PermissionError, match="message ultérieur"):
        agents.apply(weekly["id"])

    conversation.user_replies()
    agents.apply(weekly["id"])
    agent = store.agent(SLUG_V2)
    assert (agent["config"]["schedule"], agent["version"], agent["pipeline_id"]) == ("weekly", 2, PIPELINE_ID)
    engine.create_pipeline.assert_not_called()

    retire(conversation, weekly["id"])
    assert store.agent(SLUG_V2)["config"]["schedule"] == "daily"


def test_dod_13_a_changed_prompt_is_a_new_pipeline_and_a_stale_proposal_is_refused(store, conversation, engine, mocker):
    create = created_v2(conversation, mocker)
    first = agents.plan(CONFIG_V2, "Tu lis le backlog produit et les retours.")
    stale = agents.plan(CONFIG_V2.replace("daily", "monthly"), "Tu lis le backlog produit.")
    engine.create_pipeline.return_value = {"id": "55555555-5555-5555-5555-555555555555"}
    conversation.user_replies()
    agents.apply(first["id"])
    assert engine.create_pipeline.call_args.args[0] == f"agent-{SLUG_V2}-v2"
    assert store.agent(SLUG_V2)["pipeline_id"] == "55555555-5555-5555-5555-555555555555"
    with pytest.raises(ValueError, match="a changé depuis cette proposition"):
        agents.apply(stale["id"])
    with pytest.raises(ValueError, match="n'est plus la dernière appliquée"):
        agents.revert(create["id"])


def test_review_2_3_a_stale_creation_proposal_neither_overwrites_nor_retires_the_agent(store, conversation, engine):
    """Review 2.3: propose A, propose B, create B, then create A used to overwrite B, and retire A to retire it all."""
    first = agents.plan(CONFIG, "Consigne A.")
    second = agents.plan(CONFIG, "Consigne B.")
    conversation.user_replies()
    agents.apply(second["id"])
    with pytest.raises(ValueError, match="existe depuis cette proposition"):
        agents.apply(first["id"])
    with pytest.raises(ValueError, match="est planned, attendu applied"):
        agents.present_retire(first["id"])
    assert store.agent(SLUG)["system_prompt"].startswith("Consigne B.")
    assert store.agent(SLUG)["status"] == "active"


def test_review_3_retiring_needs_its_own_confirmation_and_the_owner_is_recorded(store, conversation, engine):
    applied = created_agent(conversation)
    assert store.agent(SLUG)["owner_email"] == "lj@example.org"
    with pytest.raises(PermissionError, match="retrait jamais proposé"):
        agents.revert(applied["id"])
    assert agents.present_retire(applied["id"])["effect"] == "retire l'agent"
    with pytest.raises(PermissionError, match="message ultérieur"):
        agents.revert(applied["id"])
    assert store.agent(SLUG)["status"] == "active"
    conversation.user_replies()
    agents.revert(applied["id"])
    assert store.agent(SLUG)["status"] == "retired"


CONFIG_FILES = (
    CONFIG_V2
    .replace("schedule: daily", "schedule:\n  weekdays: [monday, thursday]")
    .replace("    question: La production décrit-elle une opportunité produit nouvelle ?\n", "")
    .replace(
        "    threshold: 0.7\n",
        "    labels:\n      - name: rapide\n        question: Est-ce faisable en moins d'une semaine ?\n    threshold: 0.7\n",
    )
    + "files: [notes.md, suivi.md]\n"
)


def labelled(mocker, *probabilities):
    """Ollama Cloud mocked for a labeller with one label rapide, then the summary."""
    answers = iter(probabilities)

    def reply(path, payload):
        if path == "v1/systemone":
            return {"answers": {"rapide": {"type": "noul", "noul": next(answers)}}}
        return {"message": {"role": "assistant", "content": "Résumé."}}

    return mocker.patch("lib.agent_subagents.ollama", side_effect=reply)


@pytest.mark.parametrize(
    ("day", "due"),
    [
        ("2026-11-02T07:00:00", True),
        ("2026-11-05T07:00:00", True),
        ("2026-11-04T07:00:00", False),
        ("2026-11-06T05:00:00", True),
    ],
)
def test_dod_18_a_cadence_by_days_of_the_week_launches_on_those_days_only(mocker, day, due):
    """Days of the batch start: a Friday before 06:00 still belongs to Thursday's batch."""
    mocker.patch("lib.agents.cron.utcnow", return_value=datetime.fromisoformat(day).replace(tzinfo=timezone.utc))
    assert agents.due({"weekdays": ["monday", "thursday"]}) is due


@pytest.mark.parametrize(("schedule", "due"), [("daily", True), ("weekly", False)])
def test_dod_18_the_former_cadences_still_work(mocker, schedule, due):
    mocker.patch("lib.agents.cron.utcnow", return_value=datetime(2026, 11, 4, 7, tzinfo=timezone.utc))
    assert agents.due(schedule) is due


def test_dod_16_the_run_receives_its_files_and_the_github_cursor_moves_on(
    store, conversation, engine, mocker, preparations
):
    created_v2(conversation, mocker, CONFIG_FILES)
    write_file(SLUG_V2, "notes.md", "Définitions v1")
    prepare = mocker.patch(
        "lib.agents.agent_connectors.prepare",
        side_effect=[{"source": "a", "content": "A", "next_cursor": 4}, {"source": "b", "content": "B"}],
    )
    result = agents.execute(SLUG_V2)
    assert [c.args[1] for c in prepare.call_args_list] == [0, 0]
    rows = preparations.call_args.args[2]
    assert rows[2:] == [[3, "file", "notes.md", "Définitions v1"], [4, "file", "suivi.md", ""]]
    assert result["preparations"][2:] == ["file notes.md", "file suivi.md"]
    assert store.agent(SLUG_V2)["cursors"] == {"0": 4}
    prepare.side_effect = [{"source": "a", "content": "A", "next_cursor": 1}, {"source": "b", "content": "B"}]
    agents.execute(SLUG_V2)
    assert prepare.call_args_list[2].args[1] == 4


def write_file(slug, name, content):
    with get_db() as session:
        agent_id = session.scalar(select(Agent.id).where(Agent.slug == slug))
        agents.agent_files.write_version(session, agent_id, name, content, "run r")


def files_output(engine, deliveries, files=None):
    engine.get_run_output.return_value = json.dumps({"deliveries": deliveries, **({"files": files} if files else {})})


def test_dod_16_a_run_rewrites_a_file_and_files_labelled_productions_in_another(
    store, conversation, engine, mocker, post
):
    created_v2(conversation, mocker, CONFIG_FILES)
    deliveries = [
        {"destination": "file:suivi.md", "title": "Export CSV", "text": "Trois demandes.", "key": "export-csv"},
        {"destination": "file:suivi.md", "title": "Carte", "text": "Une demande."},
        {"destination": "produit.opportunite", "title": "Synthèse", "text": "Deux sujets."},
    ]
    files_output(engine, deliveries, [{"name": "notes.md", "content": "# Définitions\n- rapide : moins d'une semaine"}])
    labelled(mocker, 0.9, 0.2, 0.8)
    summary = agents.deliver_run(SLUG_V2, RUN_ID)
    assert [s["status"] for s in summary] == ["filed", "filed", "pending_review"]
    post.assert_not_called()
    suivi = agents.read_file(SLUG_V2, "suivi.md")
    assert suivi["version"] == 1
    assert suivi["content"] == (
        f"<!-- entree: export-csv -->\n## Export CSV\n\nRésumé.\n\n<!-- entree: {RUN_ID}-1 -->\n## Carte\n\nRésumé.\n\n"
    )
    assert store.delivery(0)["labels"] == ["rapide"]
    assert store.delivery(1)["file_version"] == 1
    assert agents.read_file(SLUG_V2, "notes.md")["content"].startswith("# Définitions")
    assert [s["status"] for s in agents.deliver_run(SLUG_V2, RUN_ID)] == ["filed", "filed", "pending_review"]
    assert len(agents.file_history(SLUG_V2, "suivi.md")) == 1
    assert len(agents.file_history(SLUG_V2, "notes.md")) == 1


@pytest.mark.parametrize(
    ("deliveries", "files", "message"),
    [
        ([], [{"name": "secret.md", "content": "x"}], "'secret.md' n'est pas un fichier déclaré"),
        (
            [{"destination": "file:notes.md", "title": "t", "text": "x"}],
            [{"name": "notes.md", "content": "x"}],
            "reçoit aussi",
        ),
    ],
)
def test_dod_16_a_run_writing_an_undeclared_file_writes_nothing(
    store, conversation, engine, mocker, deliveries, files, message
):
    created_v2(conversation, mocker, CONFIG_FILES)
    files_output(engine, deliveries, files)
    with pytest.raises(ValueError, match=message):
        agents.deliver_run(SLUG_V2, RUN_ID)
    assert (store.count(), store.count(AgentFileVersion)) == (0, 0)


def test_dod_16_a_production_to_an_undeclared_file_refuses_the_run(store, conversation, engine, mocker):
    created_v2(conversation, mocker, CONFIG_FILES)
    files_output(engine, [{"destination": "file:autre.md", "title": "t", "text": "x"}])
    with pytest.raises(ValueError, match="ni file:<nom> d'un de ses fichiers"):
        agents.deliver_run(SLUG_V2, RUN_ID)


def test_dod_16_files_are_read_compared_and_reverted_only_after_a_later_yes(
    store, conversation, engine, mocker, capsys
):
    created_v2(conversation, mocker, CONFIG_FILES)
    for text in ("v1\n", "v2\n"):
        write_file(SLUG_V2, "notes.md", text)
    file_args = ["--agent", SLUG_V2, "--name", "notes.md"]
    assert cli.main(["file", *file_args, "--version", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["content"] == "v1\n"
    assert cli.main(["history", *file_args]) == 0
    assert [v["version"] for v in json.loads(capsys.readouterr().out)] == [1, 2]
    assert cli.main(["diff", *file_args, "--old", "1", "--new", "2"]) == 0
    assert "-v1\n+v2" in capsys.readouterr().out
    assert cli.main(["revert", *file_args]) == 1
    assert "retour jamais proposé" in capsys.readouterr().err
    assert cli.main(["propose-revert", *file_args, "--version", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["diff"].endswith("-v2\n+v1\n")
    assert cli.main(["revert", *file_args]) == 1
    assert "aucune confirmation" in capsys.readouterr().err
    conversation.user_replies()
    assert cli.main(["revert", *file_args]) == 0
    assert json.loads(capsys.readouterr().out)["version"] == 3
    assert agents.read_file(SLUG_V2, "notes.md")["content"] == "v1\n"
    assert agents.file_history(SLUG_V2, "notes.md")[-1]["origin"] == "retour à la version 1 par lj@example.org"
    assert cli.main(["revert", *file_args]) == 1
    assert cli.main(["file", "--agent", SLUG_V2, "--name", "autre.md"]) == 1
    assert "n'a pas de fichier autre.md" in capsys.readouterr().err


def test_dod_16_the_proposal_shows_files_labels_and_days_and_the_contract_explains_them(
    store, conversation, engine, mocker
):
    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", {})
    proposal = agents.plan(CONFIG_FILES, "Tu lis le backlog produit.")
    assert proposal["review"] == [
        "destination produit.opportunite en mode conversational",
        "sous-agent 1 : classifier clef:27b, étiquettes rapide au seuil 0.7, sans rien écarter",
        "sous-agent 2 : summary glm-5.2, 400 caractères au plus",
        "préparation 1 : cron sync-tags",
        "préparation 2 : cron sync-connectors",
        "fichier de l'agent : notes.md, versionné, lisible depuis le chat",
        "fichier de l'agent : suivi.md, versionné, lisible depuis le chat",
        "cadence : chaque monday, thursday",
    ]
    prompt = proposal["system_prompt"]
    assert "une de produit.opportunite, file:notes.md, file:suivi.md, aucune autre" in prompt
    assert "Un envoi par élément" in prompt
    assert (
        "Tes fichiers de travail, gardés et versionnés par Autometa, jamais envoyés ailleurs : notes.md, suivi.md."
        in prompt
    )
    assert "cron sync-connectors, file notes.md, file suivi.md." in prompt


def ollama_cloud(*probabilities):
    """Ollama Cloud at the HTTP level: clef answers the probabilities in turn, the chat model a short summary."""
    answers = iter(probabilities)

    def respond(url, **kwargs):
        if url.endswith("/v1/systemone"):
            body = {"answers": {"retenir": {"type": "noul", "noul": next(answers)}}}
        else:
            body = {"message": {"role": "assistant", "content": "Une demande d'export CSV."}}
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    return respond


def throwaway_cron(base, slug, line):
    folder = base / slug
    folder.mkdir()
    (folder / "CRON.md").write_text("---\ntitle: test\nbatch: synchros\ntimeout: 30\n---\n")
    (folder / "cron.py").write_text(f"print({line!r})\n")


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_dod_14_guide_me_to_an_agent_with_a_classifier_a_summary_and_two_crons(
    app, store, engine, post, mocker, monkeypatch, tmp_path, capsys
):
    """Alexis's review-app test: propose, yes, create, launch after a yes, two crons first, classify, summarize, shadow."""
    for slug, line in (("sync-tags", "vocabulaire : 42 tags"), ("sync-connectors", "connecteurs : notion, tally")):
        throwaway_cron(tmp_path, slug, line)
    for task in agents.cron.discover_from_dir(tmp_path, "CRON.md", "system"):
        assert agents.cron.execute_task(task, trigger="scheduled")["status"] == "success"
    mocker.patch("lib.agent_config.config.CRON_DIR", tmp_path)
    publish = mocker.patch("lib.agents.job_inputs.publish_dataset", return_value={"url": "https://s3/entree.jsonl"})
    mocker.patch("lib.agents.jobs.trigger_run", return_value={"id": RUN_ID})
    mocker.patch("lib.agents.config.AGENT_DESTINATION_TARGETS", {})
    mocker.patch("lib.agent_subagents.config.OLLAMA_API_KEY", "ollama-key")
    ollama = mocker.patch("lib.agent_subagents.httpx.post", side_effect=ollama_cloud(0.88, 0.1))
    runs_output(engine, "Export CSV", "Bruit")
    conv = conversations.create_conversation()
    monkeypatch.setenv("AUTOMETA_CONVERSATION_ID", conv.id)
    monkeypatch.setenv("AUTOMETA_USER_EMAIL", "alexis@example.org")

    def user_says(text):
        conversations.add_message(conv.id, "user", text)

    user_says("Guide-moi pour créer un agent équipé d'un sous-agent classificateur et de 2 crons")
    (tmp_path / "agent.yaml").write_text(CONFIG_V2.replace("mode: conversational", "mode: background"))
    (tmp_path / "consigne.md").write_text("Tu lis le backlog produit.")
    assert cli.main(["destinations"]) == 0
    capsys.readouterr()
    assert (
        cli.main(["propose", "--config", str(tmp_path / "agent.yaml"), "--instructions", str(tmp_path / "consigne.md")])
        == 0
    )
    proposal = json.loads(capsys.readouterr().out)
    assert cli.main(["create", proposal["id"]]) == 1
    engine.create_pipeline.assert_not_called()

    user_says("oui")
    assert cli.main(["create", proposal["id"]]) == 0
    assert cli.main(["propose-launch", "--agent", SLUG_V2]) == 0
    assert cli.main(["launch", "--agent", SLUG_V2]) == 1
    user_says("oui, lance-le")
    assert cli.main(["launch", "--agent", SLUG_V2]) == 0
    capsys.readouterr()

    rows = publish.call_args.args[2]
    assert [(r[1], r[2]) for r in rows] == [("cron", "sync-tags"), ("cron", "sync-connectors")]
    assert "vocabulaire : 42 tags" in rows[0][3]
    assert "connecteurs : notion, tally" in rows[1][3]
    agents.jobs.trigger_run.assert_called_once_with(
        PIPELINE_ID, input_uri="https://s3/entree.jsonl", idempotency_key=None
    )

    assert cli.main(["deliver", "--agent", SLUG_V2, "--run", RUN_ID]) == 0
    assert [e["status"] for e in json.loads(capsys.readouterr().out)] == ["recorded", "discarded"]
    post.assert_not_called()
    assert [c.args[0].rsplit("/", 2)[-2:] for c in ollama.call_args_list] == [
        ["v1", "systemone"],
        ["api", "chat"],
        ["v1", "systemone"],
    ]
    delivered = store.delivery(0)
    assert delivered["text"] == "Une demande d'export CSV."
    assert [e["type"] for e in delivered["subagent_steps"]] == ["classifier", "summary"]
    assert store.run().subagent_calls == 3


BACKLOG_DB = "2715f321b60480e1827df1529ea754f1"
OKR_PAGE = "27d5f321b6048070985bc6cb1222230b"
EXAMPLE_CONFIG = f"""
format: pdi.agent/1
slug: tickets-backlog
title: Tickets pour le backlog commun
mission: Proposer des tickets pour le backlog commun à partir du backlog, des réflexions bizdev et du code.
destinations: []
schedule:
  weekdays: [monday, thursday]
preparations:
  - type: notion
    base: {BACKLOG_DB}
    columns: [Nom, Statut]
    group_by: [Statut]
    cap: 2000
  - type: notion
    page: {OKR_PAGE}
    depth: 2
  - type: github
    repos: [gip-inclusion/les-emplois]
    organization: gip-inclusion
    repo_cap: 4500
    cap: 5000
subagents:
  - type: classifier
    model: "clef:27b"
    labels:
      - name: quick-win
        question: Le ticket se réalise-t-il en moins d'une semaine ?
      - name: feature
        question: Le ticket décrit-il une fonctionnalité nouvelle ?
      - name: verticale
        question: Le ticket ouvre-t-il un nouveau public ou un nouveau métier ?
    threshold: 0.6
files: [definitions.md, tickets.md]
"""


def notion_api(backlog_rows):
    """Notion at the API level: the backlog database, the OKR page with one sub-page."""

    def text(t):
        return {"rich_text": [{"plain_text": t}]}

    def request(method, endpoint, payload=None):
        if endpoint == f"databases/{BACKLOG_DB}/query":
            results = [
                {
                    "last_edited_time": f"2026-10-{(i % 28) + 1:02d}T00:00:00Z",
                    "properties": {
                        "Nom": {"type": "title", "title": [{"plain_text": f"Ticket {i}"}]},
                        "Statut": {"type": "status", "status": {"name": "À faire" if i % 3 else "Fait"}},
                    },
                }
                for i in range(backlog_rows)
            ]
            return {"results": results, "has_more": False}
        if endpoint == f"pages/{OKR_PAGE}":
            return {"properties": {"Titre": {"type": "title", "title": [{"plain_text": "OKRs Bizdev"}]}}}
        block = endpoint.split("/")[1]
        children = {
            OKR_PAGE: [
                {"id": "o1", "type": "bulleted_list_item", "bulleted_list_item": text("Ouvrir les employeurs")},
                {"id": "sp", "type": "child_page", "child_page": {"title": "Pistes"}},
            ],
            "sp": [{"id": "o2", "type": "paragraph", "paragraph": text("Export CSV demandé")}],
        }
        return {"results": children[block], "has_more": False}

    return request


def labels_cloud(*verdicts):
    """Ollama Cloud at the HTTP level: clef answers each label's probability, production after production."""
    answers = iter(verdicts)

    def respond(url, **kwargs):
        questions = kwargs["json"]["questions"]
        body = {"answers": {name: {"type": "noul", "noul": p} for name, p in zip(questions, next(answers))}}
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    return respond


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_dod_19_alexis_example_tickets_from_notion_and_github_labelled_by_clef_into_a_file(
    app, store, engine, post, mocker, monkeypatch, capsys, tmp_path
):
    """The example of the PR: Notion base and page, GitHub, clef labels, files, twice a week; nothing coded for it."""
    mocker.patch("lib.notion.NOTION_TOKEN", "notion-token")
    mocker.patch("lib.notion.notion_request", side_effect=notion_api(120))
    github = FakeGitHub(mocker, repos=["dora", "les-emplois", "marche"])
    publish = mocker.patch("lib.agents.job_inputs.publish_dataset", return_value={"url": "https://s3/entree.jsonl"})
    mocker.patch("lib.agents.jobs.trigger_run", return_value={"id": RUN_ID})
    mocker.patch("lib.agent_subagents.config.OLLAMA_API_KEY", "ollama-key")
    ollama = mocker.patch("lib.agent_subagents.httpx.post", side_effect=labels_cloud((0.9, 0.2, 0.1), (0.3, 0.8, 0.7)))
    conv = conversations.create_conversation()
    monkeypatch.setenv("AUTOMETA_CONVERSATION_ID", conv.id)
    monkeypatch.setenv("AUTOMETA_USER_EMAIL", "alexis@example.org")

    def user_says(text):
        conversations.add_message(conv.id, "user", text)

    user_says("Je veux un agent qui identifie des tickets pour le backlog commun, deux fois par semaine")
    assert cli.main(["destinations"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert {"notion", "github"} <= set(listed["preparations"]) and "weekdays" in listed["schedules"]
    (tmp_path / "agent.yaml").write_text(EXAMPLE_CONFIG)
    (tmp_path / "consigne.md").write_text("Tu proposes des tickets ; tu fais évoluer definitions.md.")
    assert (
        cli.main(["propose", "--config", str(tmp_path / "agent.yaml"), "--instructions", str(tmp_path / "consigne.md")])
        == 0
    )
    proposal = json.loads(capsys.readouterr().out)
    assert "cadence : chaque monday, thursday" in proposal["review"]
    assert "étiquettes quick-win, feature, verticale au seuil 0.6, sans rien écarter" in proposal["review"][0]
    assert cli.main(["create", proposal["id"]]) == 1
    user_says("oui")
    assert cli.main(["create", proposal["id"]]) == 0
    assert cli.main(["propose-launch", "--agent", "tickets-backlog"]) == 0
    user_says("lance-le")
    assert cli.main(["launch", "--agent", "tickets-backlog"]) == 0
    capsys.readouterr()

    rows = publish.call_args.args[2]
    assert [(r[1], r[2]) for r in rows] == [
        ("notion", f"base {BACKLOG_DB}"),
        ("notion", f"page {OKR_PAGE}"),
        ("github", "gip-inclusion/les-emplois, gip-inclusion"),
        ("file", "definitions.md"),
        ("file", "tickets.md"),
    ]
    assert rows[0][3].startswith("120 lignes, au-delà du plafond de 2000 caractères")
    assert "## Statut\n- À faire : 80\n- Fait : 40" in rows[0][3]
    assert "Export CSV demandé" in rows[1][3]
    assert rows[2][3].startswith(
        "Dépôts lus ce run : gip-inclusion/les-emplois, gip-inclusion/dora ; le prochain run reprend à gip-inclusion/marche."
    )
    assert "app/views.py:2: pass  # TODO: paginer" in rows[2][3]
    assert all("Authorization" not in str(c) for c in publish.call_args_list)
    assert github.paths[0] == "orgs/gip-inclusion/repos"

    tickets = [
        {
            "destination": "file:tickets.md",
            "title": "Pagination des vues",
            "text": "TODO dans les-emplois.",
            "key": "pagination",
        },
        {"destination": "file:tickets.md", "title": "Export CSV", "text": "Demandé par les bizdev."},
    ]
    definitions = [{"name": "definitions.md", "content": "# Définitions\n- quick-win : moins d'une semaine"}]
    engine.get_run_output.return_value = json.dumps({"deliveries": tickets, "files": definitions})
    assert cli.main(["deliver", "--agent", "tickets-backlog", "--run", RUN_ID]) == 0
    assert [e["status"] for e in json.loads(capsys.readouterr().out)] == ["filed", "filed"]
    assert ollama.call_count == 2
    post.assert_not_called()

    assert cli.main(["file", "--agent", "tickets-backlog", "--name", "tickets.md"]) == 0
    tickets_md = json.loads(capsys.readouterr().out)["content"]
    assert "## Pagination des vues\n\nTODO dans les-emplois.\n\nÉtiquettes : quick-win" in tickets_md
    assert "## Export CSV\n\nDemandé par les bizdev.\n\nÉtiquettes : feature, verticale" in tickets_md
    assert cli.main(["history", "--agent", "tickets-backlog", "--name", "definitions.md"]) == 0
    assert [v["origin"] for v in json.loads(capsys.readouterr().out)] == [f"run {RUN_ID}"]

    mocker.patch("lib.agents.cron.utcnow", return_value=datetime(2026, 11, 5, 7, tzinfo=timezone.utc))
    agents.jobs.get_run.return_value = {"pipeline_id": PIPELINE_ID, "status": "running"}
    agents.tick()
    rows = publish.call_args.args[2]
    assert rows[2][3].startswith("Dépôts lus ce run : gip-inclusion/marche, gip-inclusion/les-emplois")
    assert rows[3][3].startswith("# Définitions")
