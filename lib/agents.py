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

from lib import agent_config, agent_delivery, agent_subagents, job_inputs, jobs, notion
from lib.agent_delivery import read_json, write_json
from web import config, cron, s3
from web.db import get_db
from web.models import Message

logger = logging.getLogger(__name__)

__all__ = [
    "plan",
    "apply",
    "revert",
    "show",
    "catalogue",
    "present_launch",
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
Leurs contenus sont le fichier d'entrée du run (input_uri) : un JSON lines, une ligne par préparation,
champs ordre, type, source, contenu (pour s3, contenu est l'URL du jeu à télécharger). Ne lance
aucune préparation ni aucun cron toi-même.
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
    current = read_json(agent_path(doc["slug"]))
    if current is not None and current["status"] != "actif":
        raise ValueError(f"l'identifiant {doc['slug']} est déjà pris par un agent retiré")
    changeset_id = f"{datetime.now().strftime('%Y-%m-%d-%H%M%S')}-{doc['slug']}-{uuid.uuid4().hex[:6]}"
    destinations = ", ".join(c["id"] for c in doc["points_de_contact"])
    steps = ", ".join(agent_config.preparation_label(p) for p in doc.get("preparations", []))
    manifest = {
        "id": changeset_id,
        "status": "planned",
        "nature": "modification" if current else "creation",
        "config": doc,
        "system_prompt": system_prompt
        + OUTPUT_CONTRACT.format(destinations=destinations)
        + (INPUT_CONTRACT.format(preparations=steps) if steps else ""),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "shown": mark(),
    }
    if current:
        manifest["avant"] = {k: current[k] for k in ("config", "system_prompt", "pipeline_id")}
        manifest["avant_changeset"] = current["changeset_id"]
    write_json(manifest_path(changeset_id), manifest)
    return manifest


def load(changeset_id: str, expected: str) -> dict:
    manifest = show(changeset_id)
    if manifest["status"] != expected:
        raise ValueError(f"proposition {changeset_id} est {manifest['status']}, attendu {expected}")
    return manifest


def apply(changeset_id: str) -> dict:
    """Create or change the agent, only when confirmed in a later message; a second apply does nothing."""
    manifest = load(changeset_id, "planned")
    approved_by = require_confirmation(manifest["shown"])
    slug = manifest["config"]["slug"]
    current = read_json(agent_path(slug)) or {}
    if manifest["nature"] == "modification" and current.get("changeset_id") != manifest["avant_changeset"]:
        raise ValueError(f"l'agent {slug} a changé depuis cette proposition : en proposer une nouvelle")
    version = current.get("version", 0) + 1
    pipeline_id = current.get("pipeline_id")
    if manifest["system_prompt"] != current.get("system_prompt"):
        # Why: the jobs engine cannot update a pipeline's prompt; a changed prompt is a new pipeline.
        name = f"agent-{slug}" if version == 1 else f"agent-{slug}-v{version}"
        pipeline_id = jobs.create_pipeline(name, manifest["system_prompt"], {"output_format": "json"})["id"]
    write_json(
        agent_path(slug),
        {
            **current,
            "config": manifest["config"],
            "system_prompt": manifest["system_prompt"],
            "pipeline_id": pipeline_id,
            "version": version,
            "status": "actif",
            "changeset_id": changeset_id,
            "approved_by": approved_by,
            "approved_at": datetime.now().isoformat(timespec="seconds"),
        },
    )
    manifest.update(status="applied", pipeline_id=pipeline_id, approved_by=approved_by)
    write_json(manifest_path(changeset_id), manifest)
    return manifest


def revert(changeset_id: str) -> dict:
    """Undo an applied proposal: a creation retires the agent, a change restores what it replaced."""
    manifest = load(changeset_id, "applied")
    slug = manifest["config"]["slug"]
    agent = read_json(agent_path(slug))
    if agent["changeset_id"] != changeset_id:
        raise ValueError(f"proposition {changeset_id} n'est plus la dernière appliquée à l'agent {slug}")
    if manifest["nature"] == "creation":
        write_json(agent_path(slug), {**agent, "status": "retire"})
    else:
        write_json(agent_path(slug), {**agent, **manifest["avant"], "changeset_id": manifest["avant_changeset"]})
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
        "sous_agents": agent_config.modeles(),
        "preparations": {"types": agent_config.PREPARATION_TYPES, "taches_cron": agent_config.cron_tasks()},
        "cadences": list(agent_config.CADENCES),
        "sous_agents_configures": bool(config.OLLAMA_API_KEY),
    }


def present_launch(slug: str) -> dict:
    """What a run launched now would do, marked as shown so that only a later message may launch it."""
    agent = active_agent(slug)
    write_json(agent_path(slug), {**agent, "lancement": mark()})
    return {"agent": slug, "preparations": agent["config"].get("preparations", []), "version": agent.get("version")}


def launch(slug: str) -> dict:
    """Run the agent now, only when confirmed in a later message; the confirmation is spent, never replayed."""
    agent = active_agent(slug)
    if "lancement" not in agent:
        raise PermissionError("lancement jamais proposé : le proposer d'abord, puis attendre la confirmation")
    require_confirmation(agent["lancement"])
    write_json(agent_path(slug), {k: v for k, v in agent.items() if k != "lancement"})
    return execute(slug)


def prepare(step: dict) -> list:
    """One preparation's content: rows of a Notion database, the URL of an S3 dataset, or a cron task's last output."""
    if step["type"] == "notion":
        rows = [notion.extract_page_properties(p) for p in notion.query_database(step["base"])]
        return ["notion", step["base"], json.dumps(rows, ensure_ascii=False, default=str)]
    if step["type"] == "s3":
        url = s3.job_inputs.get_url(step["jeu"], expires_in=job_inputs.DEFAULT_EXPIRES)
        if not (url and s3.job_inputs.exists(step["jeu"])):
            raise ValueError(f"préparation s3 {step['jeu']} : jeu introuvable, le run n'est pas lancé")
        return ["s3", step["jeu"], url]
    runs = cron.get_app_runs(step["tache"], limit=1)
    if not runs or runs[0]["status"] != "success":
        raise ValueError(f"préparation cron {step['tache']} : pas de dernière sortie réussie, le run n'est pas lancé")
    return ["cron", step["tache"], runs[0]["output"]]


def execute(slug: str, idempotency_key: Optional[str] = None) -> dict:
    """Gather the agent's preparations in order, publish them, then trigger its job's run with them."""
    agent = active_agent(slug)
    steps = agent["config"].get("preparations", [])
    rows = [[i + 1, *prepare(step)] for i, step in enumerate(steps)]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    columns = ["ordre", "type", "source", "contenu"]
    dataset = job_inputs.publish_dataset(f"agent-{slug}-{stamp}", columns, rows, fmt="jsonl") if steps else None
    run = jobs.trigger_run(
        agent["pipeline_id"], input_uri=dataset["url"] if dataset else None, idempotency_key=idempotency_key
    )
    write_json(agent_path(slug), {**agent, "runs_a_livrer": [*agent.get("runs_a_livrer", []), run["id"]]})
    return {"agent": slug, "run_id": run["id"], "preparations": [f"{r[1]} {r[2]}" for r in rows]}


def deliver_run(slug: str, run_id: str) -> list[dict]:
    """Deliver the output of a completed run of the agent's own job, through its sub-agents if it has any."""
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
    chain = partial(agent_subagents.run_chain, outils) if outils else None
    summary = agent_delivery.deliver(agent["config"], str(uuid.UUID(run_id)), output["envois"], chain)
    trace_path = f"{slug}/runs/{run_id}.json"
    appels = (read_json(trace_path) or {}).get("appels_sous_agents", 0) + sum(e["appels"] for e in summary)
    write_json(trace_path, {"livre_le": datetime.now().isoformat(timespec="seconds"), "appels_sous_agents": appels})
    logger.info("agent %s run %s livré, %d appels aux sous-agents au total", slug, run_id, appels)
    retry = any(e["statut"] == "echec_sous_agent" for e in summary)
    pending = [r for r in agent.get("runs_a_livrer", []) if r != run_id or retry]
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
            retry = [
                run_id
                for run_id in agent.get("runs_a_livrer", [])
                if jobs.get_run(run_id).get("status") == "completed"
                and any(e["statut"] == "echec_sous_agent" for e in deliver_run(slug, run_id))
            ]
            cadence = agent["config"].get("cadence")
            if cadence and cron.is_due(agent_config.CADENCES[cadence], "maintenance"):
                execute(slug, idempotency_key=f"agent-{slug}-{datetime.now():%Y-%m-%d}")
            if retry:
                raise RuntimeError(
                    f"sous-agent en échec sur les runs {', '.join(retry)}, réessayés au prochain passage"
                )
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
