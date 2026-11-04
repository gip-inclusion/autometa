"""Agents: jobs created only after a confirmation in a later message, retired on demand, their runs delivered."""

import json
import logging
import re
import uuid
from datetime import datetime
from functools import partial
from typing import Optional

import httpx
from sqlalchemy import func, select

from lib import agent_classifier, agent_config, agent_delivery, job_inputs, jobs
from lib.agent_delivery import read_json, write_json
from web import config, cron, s3, scalingo
from web.db import get_db
from web.models import Message

logger = logging.getLogger(__name__)

__all__ = [
    "plan",
    "apply",
    "revert",
    "show",
    "catalogue",
    "launch",
    "execute",
    "deliver_run",
    "present_envoi",
    "approve_envoi",
    "tick",
]

OUTPUT_CONTRACT = """

## Contrat de sortie

Ta réponse est un unique objet JSON, sans aucun texte autour :
{{"envois": [{{"destination": "...", "titre": "...", "texte": "...", "cle": "..."}}]}}

- destination : une de {destinations}, aucune autre.
- titre : une ligne. texte : en markdown.
- cle (facultative, Notion seulement) : minuscules, chiffres et tirets ; un envoi qui reprend la cle
  d'une page déjà écrite met cette page à jour.
- Rien à signaler : {{"envois": []}}.
"""

INPUT_CONTRACT = """
## Entrée

Avant chacun de tes runs, Autometa fait tourner tes préparations, dans cet ordre : {preparations}.
Leurs sorties sont le fichier d'entrée du run (input_uri) : un JSON lines, une ligne par préparation,
champs ordre, preparation, statut, sortie. Ne lance aucune préparation ni aucun cron toi-même.
"""


def last_user_message_id(conversation_id: str) -> int:
    with get_db() as session:
        found = session.scalar(
            select(func.max(Message.id)).where(
                Message.conversation_id == conversation_id, func.coalesce(Message.type, Message.role) == "user"
            )
        )
    return found or 0


def mark() -> dict:
    """Where and after which user message a proposal was shown; only a later message may confirm it."""
    conversation_id = config.agent_conversation_id()
    if not conversation_id:
        raise ValueError("une proposition se présente et se confirme dans une conversation")
    return {"conversation_id": conversation_id, "after_message_id": last_user_message_id(conversation_id)}


def require_confirmation(shown: dict) -> str:
    """The approving user's email, once a later message of the same conversation exists; refused otherwise."""
    conversation_id = config.agent_conversation_id()
    if conversation_id != shown["conversation_id"]:
        raise PermissionError("la confirmation doit venir de la conversation où la proposition a été présentée")
    if last_user_message_id(conversation_id) <= shown["after_message_id"]:
        raise PermissionError("aucune confirmation : attendre un message ultérieur de l'utilisateur")
    return config.agent_user_email() or "inconnu"


def agent_path(slug: str) -> str:
    return f"{slug}/agent.json"


def manifest_path(changeset_id: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-\d{6}-[a-z0-9-]+", changeset_id):
        raise ValueError(f"proposition {changeset_id} introuvable")
    # Why: a character no slug can hold keeps proposals apart from the agents' own folders.
    return f"_creations/{changeset_id}.json"


def plan(config_yaml: str, system_prompt: str) -> dict:
    """Validate an agent and record its creation as a proposal; nothing is created in the jobs engine."""
    doc = agent_config.parse(config_yaml)
    if errors := agent_config.validate(doc):
        raise ValueError("configuration refusée : " + " ; ".join(errors))
    if not system_prompt.strip():
        raise ValueError("consigne du job vide")
    if read_json(agent_path(doc["slug"])) is not None:
        raise ValueError(f"l'identifiant {doc['slug']} est déjà pris par un agent")
    changeset_id = f"{datetime.now().strftime('%Y-%m-%d-%H%M%S')}-{doc['slug']}"
    destinations = ", ".join(c["id"] for c in doc["points_de_contact"])
    manifest = {
        "id": changeset_id,
        "status": "planned",
        "config": doc,
        "system_prompt": system_prompt
        + OUTPUT_CONTRACT.format(destinations=destinations)
        + (INPUT_CONTRACT.format(preparations=", ".join(steps)) if (steps := doc.get("preparations")) else ""),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "shown": mark(),
    }
    write_json(manifest_path(changeset_id), manifest)
    return manifest


def load(changeset_id: str, expected: str) -> dict:
    manifest = show(changeset_id)
    if manifest["status"] != expected:
        raise ValueError(f"proposition {changeset_id} est {manifest['status']}, attendu {expected}")
    return manifest


def apply(changeset_id: str) -> dict:
    """Create the agent's job, only when confirmed in a later message; a second apply creates nothing."""
    manifest = load(changeset_id, "planned")
    approved_by = require_confirmation(manifest["shown"])
    slug = manifest["config"]["slug"]
    pipeline = jobs.create_pipeline(f"agent-{slug}", manifest["system_prompt"], {"output_format": "json"})
    write_json(
        agent_path(slug),
        {
            "config": manifest["config"],
            "pipeline_id": pipeline["id"],
            "status": "actif",
            "changeset_id": changeset_id,
            "approved_by": approved_by,
            "approved_at": datetime.now().isoformat(timespec="seconds"),
        },
    )
    manifest.update(status="applied", pipeline_id=pipeline["id"], approved_by=approved_by)
    write_json(manifest_path(changeset_id), manifest)
    return manifest


def revert(changeset_id: str) -> dict:
    """Retire an applied agent: its runs are no longer delivered. The job stays, the engine cannot delete it."""
    manifest = load(changeset_id, "applied")
    slug = manifest["config"]["slug"]
    write_json(agent_path(slug), {**read_json(agent_path(slug)), "status": "retire"})
    manifest["status"] = "reverted"
    write_json(manifest_path(changeset_id), manifest)
    return manifest


def show(changeset_id: str) -> dict:
    manifest = read_json(manifest_path(changeset_id))
    if manifest is None:
        raise ValueError(f"proposition {changeset_id} introuvable")
    return manifest


def active_agent(slug: str) -> dict:
    agent: Optional[dict] = read_json(agent_path(slug)) if re.fullmatch(r"[a-z][a-z0-9-]{2,40}", slug) else None
    if agent is None or agent["status"] != "actif":
        raise ValueError(f"aucun agent actif {slug}")
    return agent


def catalogue() -> dict:
    """Everything an agent may use, and whether this instance is configured for it; reads no secret."""
    targets = config.AGENT_DESTINATION_TARGETS
    return {
        "destinations": [
            {"id": d["id"], "canal": d["canal"], "cible_configuree": bool(targets.get(d["id"]))}
            for d in agent_config.destinations().values()
        ],
        "modeles": [{"id": m["id"], "type": m["type"]} for m in agent_config.modeles().values()],
        "preparations": [{"id": p["id"], "cron": p["cron"]} for p in agent_config.preparations().values()],
        "cadences": list(agent_config.CADENCES),
        "classificateur_configure": bool(config.OLLAMA_API_KEY),
        "lancement_configure": scalingo.is_configured(),
    }


def launch(slug: str) -> dict:
    """Start the agent's preparations and run in a one-off container, never in the web process."""
    active_agent(slug)
    command = f"python skills/agents/scripts/agents.py executer --agent {slug}"
    if not scalingo.is_configured():
        raise ValueError(f"lancement indisponible ici (Scalingo non configuré) : exécuter `{command}`")
    return {"agent": slug, "conteneur": scalingo.start_one_off(command)}


def execute(slug: str, idempotency_key: Optional[str] = None) -> dict:
    """Run the agent's preparations in order, publish their outputs, then trigger its job's run with them."""
    agent = active_agent(slug)
    steps = agent["config"].get("preparations", [])
    known = agent_config.preparations()
    tasks = cron.discover_by_slug() if steps else {}
    outputs = []
    for i, step in enumerate(steps):
        task = tasks.get(known[step]["cron"])
        if task is None:
            raise ValueError(f"préparation {step} : tâche {known[step]['cron']} introuvable, le run n'est pas lancé")
        result = cron.execute_task(task, trigger="agent")
        if result["status"] != "success":
            raise ValueError(f"préparation {step} en {result['status']} : le run n'est pas lancé")
        outputs.append([i + 1, step, result["status"], result["output"]])
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    columns = ["ordre", "preparation", "statut", "sortie"]
    dataset = job_inputs.publish_dataset(f"agent-{slug}-{stamp}", columns, outputs, fmt="jsonl") if steps else None
    run = jobs.trigger_run(
        agent["pipeline_id"], input_uri=dataset["url"] if dataset else None, idempotency_key=idempotency_key
    )
    write_json(agent_path(slug), {**agent, "runs_a_livrer": [*agent.get("runs_a_livrer", []), run["id"]]})
    return {"agent": slug, "run_id": run["id"], "preparations": [o[1] for o in outputs]}


def deliver_run(slug: str, run_id: str) -> list[dict]:
    """Deliver the output of a completed run of the agent's own job, through its classifiers if it has any."""
    agent = active_agent(slug)
    run = jobs.get_run(run_id)
    if run.get("pipeline_id") != agent["pipeline_id"]:
        raise ValueError(f"le run {run_id} n'appartient pas au job de l'agent {slug}")
    if run.get("status") != "completed":
        raise ValueError(f"le run {run_id} est {run.get('status')}, attendu completed")
    try:
        output = json.loads(jobs.get_run_output(run_id))
    except json.JSONDecodeError as exc:
        raise ValueError(f"sortie du run {run_id} illisible : {exc}") from exc
    if not isinstance(output, dict) or "envois" not in output:
        raise ValueError(f"sortie du run {run_id} sans liste envois")
    outils = agent["config"].get("outils_modeles")
    classify = partial(agent_classifier.classify, outils) if outils else None
    summary = agent_delivery.deliver(agent["config"], str(uuid.UUID(run_id)), output["envois"], classify)
    pending = [r for r in agent.get("runs_a_livrer", []) if r != run_id]
    write_json(agent_path(slug), {**agent, "runs_a_livrer": pending})
    return summary


def tick() -> None:
    """Daily: deliver every active agent's completed runs, then launch the agents whose cadence is due."""
    failed = []
    for slug in s3.agents.list_directories(""):
        agent = None if slug.startswith("_") else read_json(agent_path(slug))
        if agent is None or agent["status"] != "actif":
            continue
        try:
            for run_id in agent.get("runs_a_livrer", []):
                if jobs.get_run(run_id).get("status") == "completed":
                    deliver_run(slug, run_id)
            cadence = agent["config"].get("cadence")
            if cadence and cron.is_due(agent_config.CADENCES[cadence], "maintenance"):
                execute(slug, idempotency_key=f"agent-{slug}-{datetime.now():%Y-%m-%d}")
        except (ValueError, RuntimeError, httpx.HTTPError) as exc:
            logger.warning("agent %s : passage quotidien en échec : %s", slug, exc)
            failed.append(slug)
    if failed:
        raise RuntimeError(f"agents en échec : {', '.join(failed)}")


def present_envoi(slug: str, envoi_id: str) -> dict:
    """A production awaiting review, marked as shown so that only a later message may approve it."""
    active_agent(slug)
    record = agent_delivery.show(slug, envoi_id)
    record["shown"] = mark()
    write_json(f"{slug}/envois/{envoi_id}.json", record)
    return record


def approve_envoi(slug: str, envoi_id: str) -> dict:
    active_agent(slug)
    record = agent_delivery.show(slug, envoi_id)
    if "shown" not in record:
        raise PermissionError("envoi jamais présenté : le montrer d'abord, puis attendre la confirmation")
    return agent_delivery.approve(slug, envoi_id, require_confirmation(record["shown"]))
