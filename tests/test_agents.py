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


def test_dod_2_slug_of_a_retired_agent_gives_no_proposal(store, conversation, engine):
    agents.revert(created_agent(conversation)["id"])
    count = len(store.files)
    with pytest.raises(ValueError, match="déjà pris par un agent retiré"):
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
        {
            "id": f"{RUN_ID}-0",
            "destination": "produit.signal_faible",
            "mode": "relecture",
            "statut": "a_relire",
            "appels": 0,
        }
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


CONFIG_V2 = (
    CONFIG.replace("signaux-faibles-mep", "opportunites-backlog").replace(
        "produit.signal_faible", "produit.opportunite"
    )
    + """cadence: quotidienne
outils_modeles:
  - type: classificateur
    modele: "clef:27b"
    question: La production décrit-elle une opportunité produit nouvelle ?
    seuil: 0.7
  - type: resume
    modele: glm-5.2
    longueur_max: 400
preparations:
  - type: cron
    tache: sync-tags
  - type: cron
    tache: sync-connectors
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
    mocker.patch("lib.agents.notion.query_database", return_value=[{"properties": {}}])
    mocker.patch("lib.agents.notion.extract_page_properties", return_value={"Nom": "Export CSV"})
    mocker.patch("lib.agents.s3.job_inputs.get_url", return_value="https://s3/services.sqlite")
    mocker.patch("lib.agents.s3.job_inputs.exists", return_value=True)
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
    envois = [{"destination": "produit.opportunite", "titre": t, "texte": f"{t}, détails."} for t in titles]
    engine.get_run_output.return_value = json.dumps({"envois": envois})


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
    assert not any(d["cible_configuree"] for d in listed["destinations"])
    assert listed["sous_agents"]["classificateur"] == ["clef:27b"]
    assert set(listed["sous_agents"]) == {"classificateur", "extraction", "resume"}
    assert listed["preparations"]["types"] == {"notion": "base", "s3": "jeu", "cron": "tache"}
    assert "sync-tags" in listed["preparations"]["taches_cron"]
    assert "run-agents" not in listed["preparations"]["taches_cron"]
    assert listed["cadences"] == ["quotidienne", "hebdomadaire", "mensuelle"]
    assert listed["sous_agents_configures"] is False


def test_dod_9_proposal_without_any_target_shows_classifier_preparations_and_cadence(
    store, conversation, engine, mocker
):
    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", {})
    proposal = agents.plan(CONFIG_V2, "Tu lis le backlog produit.")
    assert proposal["nature"] == "creation"
    assert proposal["config"]["cadence"] == "quotidienne"
    assert proposal["config"]["outils_modeles"][0]["seuil"] == 0.7
    assert "dans cet ordre : cron sync-tags, cron sync-connectors." in proposal["system_prompt"]
    engine.create_pipeline.assert_not_called()


def test_dod_10_productions_under_the_threshold_are_kept_but_not_delivered(store, conversation, engine, mocker, post):
    created_v2(conversation, mocker)
    runs_output(engine, "Export CSV", "Bruit")
    ollama_says(mocker, 0.91, 0.2)
    summary = agents.deliver_run(SLUG_V2, RUN_ID)
    assert [s["statut"] for s in summary] == ["a_relire", "ecarte"]
    assert [s["appels"] for s in summary] == [2, 1]
    assert store.json(f"{SLUG_V2}/envois/{RUN_ID}-0.json")["texte"] == "Résumé."
    kept = store.json(f"{SLUG_V2}/envois/{RUN_ID}-1.json")
    assert kept["sous_agents"] == [
        {"type": "classificateur", "modele": "clef:27b", "probabilite": 0.2, "seuil": 0.7, "retenu": False}
    ]
    assert kept["texte"] == "Bruit, détails."
    assert store.json(f"{SLUG_V2}/runs/{RUN_ID}.json")["appels_sous_agents"] == 3
    with pytest.raises(ValueError, match="est ecarte"):
        agents.agent_delivery.approve(SLUG_V2, f"{RUN_ID}-1", "lj@example.org")


def test_dod_10_a_failing_sub_agent_delivers_nothing_of_that_production_and_is_retried(
    store, conversation, engine, mocker, caplog
):
    created_v2(conversation, mocker)
    runs_output(engine, "Export CSV")
    mocker.patch("lib.agent_subagents.config.OLLAMA_API_KEY", "")
    with caplog.at_level("INFO"):
        summary = agents.deliver_run(SLUG_V2, RUN_ID)
    assert [s["statut"] for s in summary] == ["echec_sous_agent"]
    record = store.json(f"{SLUG_V2}/envois/{RUN_ID}-0.json")
    assert "sous-agent 1 (classificateur clef:27b) en échec : OLLAMA_API_KEY absent" in record["erreur"]
    assert "Export CSV" not in caplog.text
    with pytest.raises(ValueError, match="est echec_sous_agent"):
        agents.agent_delivery.approve(SLUG_V2, f"{RUN_ID}-0", "lj@example.org")

    ollama_says(mocker, 0.9)
    assert [s["statut"] for s in agents.deliver_run(SLUG_V2, RUN_ID)] == ["a_relire"]
    assert store.json(f"{SLUG_V2}/envois/{RUN_ID}-0.json")["texte"] == "Résumé."
    assert store.json(f"{SLUG_V2}/runs/{RUN_ID}.json")["appels_sous_agents"] == 3


def test_dod_11_preparations_feed_the_run_in_order_from_their_three_types(
    store, conversation, engine, mocker, preparations
):
    steps = f"  - type: notion\n    base: {NOTION_DB}\n  - type: s3\n    jeu: services.sqlite\n"
    created_v2(conversation, mocker, CONFIG_V2.replace("  - type: cron\n    tache: sync-connectors\n", steps))
    assert agents.execute(SLUG_V2)["preparations"] == ["cron sync-tags", f"notion {NOTION_DB}", "s3 services.sqlite"]
    _, columns, rows = preparations.call_args.args
    assert columns == ["ordre", "type", "source", "contenu"]
    assert rows == [
        [1, "cron", "sync-tags", "vocabulaire : 42 tags"],
        [2, "notion", NOTION_DB, '[{"Nom": "Export CSV"}]'],
        [3, "s3", "services.sqlite", "https://s3/services.sqlite"],
    ]
    agents.jobs.trigger_run.assert_called_once_with(
        PIPELINE_ID, input_uri="https://s3/entree.jsonl", idempotency_key=None
    )
    assert store.json(f"{SLUG_V2}/agent.json")["runs_a_livrer"] == [NEW_RUN]


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
    created_v2(conversation, mocker, CONFIG_V2 + "  - type: s3\n    jeu: absent.csv\n")
    mocker.patch("lib.agents.s3.job_inputs.exists", return_value=False)
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

    assert store.json(f"{SLUG_V2}/envois/{NEW_RUN}-0.json")["statut"] == "a_relire"
    assert store.json(f"{SLUG_V2}/agent.json")["runs_a_livrer"] == ["44444444-4444-4444-4444-444444444444"]
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

    with pytest.raises(RuntimeError, match=f"agents en échec : {SLUG_V2}"):
        agents.tick()

    assert store.json(f"{SLUG_V2}/envois/{NEW_RUN}-0.json")["statut"] == "echec_sous_agent"
    pending = store.json(f"{SLUG_V2}/agent.json")["runs_a_livrer"]
    assert pending == [NEW_RUN, "44444444-4444-4444-4444-444444444444"]
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
    assert store.json(f"{SLUG}/agent.json")["runs_a_livrer"] == [NEW_RUN]

    agents.revert(applied["id"])
    agents.tick()
    assert agents.jobs.trigger_run.call_count == 1


def test_dod_12_one_failing_agent_does_not_stop_the_others(store, conversation, engine, mocker, preparations):
    created_v2(conversation, mocker)
    agents.execute(SLUG_V2)
    engine.get_run.side_effect = httpx.ConnectError("coupé")
    with pytest.raises(RuntimeError, match=f"agents en échec : {SLUG_V2}"):
        agents.tick()


def test_dod_13_a_run_now_needs_a_later_message_and_the_confirmation_is_spent(
    store, conversation, engine, mocker, preparations
):
    created_v2(conversation, mocker)
    with pytest.raises(PermissionError, match="lancement jamais proposé"):
        agents.launch(SLUG_V2)
    assert agents.present_launch(SLUG_V2)["preparations"][0] == {"type": "cron", "tache": "sync-tags"}
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
    weekly = agents.plan(CONFIG_V2.replace("quotidienne", "hebdomadaire"), "Tu lis le backlog produit.")
    assert weekly["nature"] == "modification"
    assert store.json(f"{SLUG_V2}/agent.json")["config"]["cadence"] == "quotidienne"
    with pytest.raises(PermissionError, match="message ultérieur"):
        agents.apply(weekly["id"])

    conversation.user_replies()
    agents.apply(weekly["id"])
    agent = store.json(f"{SLUG_V2}/agent.json")
    assert (agent["config"]["cadence"], agent["version"], agent["pipeline_id"]) == ("hebdomadaire", 2, PIPELINE_ID)
    engine.create_pipeline.assert_not_called()

    agents.revert(weekly["id"])
    assert store.json(f"{SLUG_V2}/agent.json")["config"]["cadence"] == "quotidienne"


def test_dod_13_a_changed_prompt_is_a_new_pipeline_and_a_stale_proposal_is_refused(store, conversation, engine, mocker):
    creation = created_v2(conversation, mocker)
    first = agents.plan(CONFIG_V2, "Tu lis le backlog produit et les retours.")
    stale = agents.plan(CONFIG_V2.replace("quotidienne", "mensuelle"), "Tu lis le backlog produit.")
    engine.create_pipeline.return_value = {"id": "55555555-5555-5555-5555-555555555555"}
    conversation.user_replies()
    agents.apply(first["id"])
    assert engine.create_pipeline.call_args.args[0] == f"agent-{SLUG_V2}-v2"
    assert store.json(f"{SLUG_V2}/agent.json")["pipeline_id"] == "55555555-5555-5555-5555-555555555555"
    with pytest.raises(ValueError, match="a changé depuis cette proposition"):
        agents.apply(stale["id"])
    with pytest.raises(ValueError, match="n'est plus la dernière appliquée"):
        agents.revert(creation["id"])


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
    (tmp_path / "agent.yaml").write_text(CONFIG_V2.replace("mode: relecture", "mode: ombre"))
    (tmp_path / "consigne.md").write_text("Tu lis le backlog produit.")
    assert cli.main(["destinations"]) == 0
    capsys.readouterr()
    assert (
        cli.main(["proposer", "--config", str(tmp_path / "agent.yaml"), "--consigne", str(tmp_path / "consigne.md")])
        == 0
    )
    proposal = json.loads(capsys.readouterr().out)
    assert cli.main(["creer", proposal["id"]]) == 1
    engine.create_pipeline.assert_not_called()

    user_says("oui")
    assert cli.main(["creer", proposal["id"]]) == 0
    assert cli.main(["proposer-lancement", "--agent", SLUG_V2]) == 0
    assert cli.main(["lancer", "--agent", SLUG_V2]) == 1
    user_says("oui, lance-le")
    assert cli.main(["lancer", "--agent", SLUG_V2]) == 0
    capsys.readouterr()

    rows = publish.call_args.args[2]
    assert [(r[1], r[2]) for r in rows] == [("cron", "sync-tags"), ("cron", "sync-connectors")]
    assert "vocabulaire : 42 tags" in rows[0][3]
    assert "connecteurs : notion, tally" in rows[1][3]
    agents.jobs.trigger_run.assert_called_once_with(
        PIPELINE_ID, input_uri="https://s3/entree.jsonl", idempotency_key=None
    )

    assert cli.main(["livrer", "--agent", SLUG_V2, "--run", RUN_ID]) == 0
    assert [e["statut"] for e in json.loads(capsys.readouterr().out)] == ["ombre", "ecarte"]
    post.assert_not_called()
    assert [c.args[0].rsplit("/", 2)[-2:] for c in ollama.call_args_list] == [
        ["v1", "systemone"],
        ["api", "chat"],
        ["v1", "systemone"],
    ]
    delivered = store.json(f"{SLUG_V2}/envois/{RUN_ID}-0.json")
    assert delivered["texte"] == "Une demande d'export CSV."
    assert [e["type"] for e in delivered["sous_agents"]] == ["classificateur", "resume"]
    assert store.json(f"{SLUG_V2}/runs/{RUN_ID}.json")["appels_sous_agents"] == 3
