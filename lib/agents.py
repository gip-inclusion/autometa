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

from lib import agent_config, agent_connectors, agent_delivery, agent_files, agent_subagents, job_inputs, jobs
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
    "present_delivery",
    "approve_delivery",
    "tick",
    "read_file",
    "file_history",
    "compare_file",
    "present_file_revert",
    "revert_file",
]

OUTPUT_CONTRACT = """

## Contrat de sortie

Ta réponse est un unique objet JSON, sans aucun texte autour :
{{"deliveries": [{{"destination": "...", "title": "...", "text": "...", "key": "..."}}]}}

- destination : une de {destinations}, aucune autre.
- title : une ligne. text : en markdown.
- Un envoi par élément (un ticket, un signal, une opportunité) : les sous-agents d'Autometa jugent
  chaque envoi à part, un envoi qui en regroupe plusieurs serait jugé en bloc.
- key (facultative, Notion ou fichier) : minuscules, chiffres et tirets ; un envoi qui reprend la
  key d'une page ou d'un élément déjà écrit le met à jour.
- Rien à signaler : {{"deliveries": []}}.
"""

FILES_CONTRACT = """
## Tes fichiers

Tes fichiers de travail, gardés et versionnés par Autometa, jamais envoyés ailleurs : {files}.
Leur dernière version est dans ton entrée (type file ; vide avant la première écriture).
- Pour réécrire un fichier en entier, ajoute à ta réponse
  "files": [{{"name": "...", "content": "..."}}] ({size} caractères au plus par fichier).
- Pour y ranger des éléments un par un, un envoi par élément avec "destination": "file:<nom>" ;
  Autometa l'y ajoute après ses sous-agents (étiquettes comprises).
- Un même fichier ne reçoit pas les deux dans un même run.
"""

INPUT_CONTRACT = """
## Entrée

Avant chacun de tes runs, Autometa fait tourner tes préparations, dans cet ordre : {preparations}.
Leurs contenus sont le fichier d'entrée du run (input_uri) : un JSON lines, une ligne par préparation
puis une par fichier, champs order, type, source, content (en Markdown ; pour s3, l'URL du jeu à
télécharger). Ne lance aucune préparation ni aucun cron toi-même.
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


def plan(config_yaml: str, system_prompt: str, initial_files: Optional[dict[str, str]] = None) -> dict:
    """Validate an agent and record its creation as a proposal; nothing is created in the jobs engine."""
    doc = agent_config.parse(config_yaml)
    initial_files = initial_files or {}
    if errors := agent_config.validate(doc) + agent_config.initial_errors(initial_files, doc.get("files", [])):
        raise ValueError("configuration refusée : " + " ; ".join(errors))
    if not system_prompt.strip():
        raise ValueError("consigne du job vide")
    current = read_json(agent_path(doc["slug"]))
    if current is not None and current["status"] != "active":
        raise ValueError(f"l'identifiant {doc['slug']} est déjà pris par un agent retiré")
    changeset_id = f"{datetime.now().strftime('%Y-%m-%d-%H%M%S')}-{doc['slug']}-{uuid.uuid4().hex[:6]}"
    files = doc.get("files", [])
    destinations = ", ".join([*(c["id"] for c in doc["destinations"]), *(f"file:{f}" for f in files)])
    steps = ", ".join([
        *(agent_connectors.label(p) for p in doc.get("preparations", [])),
        *(f"fichier {f}" for f in files),
    ])
    manifest = {
        "id": changeset_id,
        "status": "planned",
        "kind": "update" if current else "create",
        "config": doc,
        "system_prompt": system_prompt
        + OUTPUT_CONTRACT.format(destinations=destinations)
        + (INPUT_CONTRACT.format(preparations=steps) if steps else "")
        + (FILES_CONTRACT.format(files=", ".join(files), size=agent_config.AGENT_FILE_MAX) if files else ""),
        "review": agent_config.describe(doc)
        + [
            f"valeur initiale de {name} : {len(c)} caractères, écrite à la création si le fichier est vide"
            for name, c in initial_files.items()
        ],
        "initial_files": initial_files,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "shown": mark(),
    }
    if current:
        manifest["avant"] = {k: current[k] for k in ("config", "system_prompt", "pipeline_id")}
        manifest["previous_changeset"] = current["changeset_id"]
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
    if manifest["kind"] == "update" and current.get("changeset_id") != manifest["previous_changeset"]:
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
            "status": "active",
            "changeset_id": changeset_id,
            "approved_by": approved_by,
            "approved_at": datetime.now().isoformat(timespec="seconds"),
        },
    )
    for name, content in manifest.get("initial_files", {}).items():
        # Why: a file the agent already wrote is its own work; an initial value never overwrites it.
        if not agent_files.history(slug, name):
            agent_files.write_version(slug, name, content, f"valeur initiale, proposition {changeset_id}")
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
    if manifest["kind"] == "create":
        write_json(agent_path(slug), {**agent, "status": "retired"})
    else:
        write_json(agent_path(slug), {**agent, **manifest["avant"], "changeset_id": manifest["previous_changeset"]})
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
    if agent is None or agent["status"] != "active":
        raise ValueError(f"aucun agent actif {slug}")
    return agent


def catalogue() -> dict:
    """Everything an agent may use, and whether this instance is configured for it; reads no secret."""
    targets = config.AGENT_DESTINATION_TARGETS
    return {
        "destinations": [
            {"id": d["id"], "channel": d["channel"], "target_configured": bool(targets.get(d["id"]))}
            for d in agent_config.known_destinations().values()
        ],
        "subagents": agent_config.models(),
        "preparations": agent_connectors.catalogue(),
        "cron_tasks": agent_connectors.connector("cron").tasks(),
        "schedules": {"weekdays": list(agent_config.WEEKDAYS), "shortcuts": list(agent_config.SCHEDULES)},
        "files": {"at_most": 5, "max_size": agent_config.AGENT_FILE_MAX},
        "subagents_configured": bool(config.OLLAMA_API_KEY),
    }


def present_launch(slug: str) -> dict:
    """What a run launched now would do, marked as shown so that only a later message may launch it."""
    agent = active_agent(slug)
    write_json(agent_path(slug), {**agent, "launch": mark()})
    return {"agent": slug, "preparations": agent["config"].get("preparations", []), "version": agent.get("version")}


def launch(slug: str) -> dict:
    """Run the agent now, only when confirmed in a later message; the confirmation is spent, never replayed."""
    agent = active_agent(slug)
    if "launch" not in agent:
        raise PermissionError("lancement jamais proposé : le proposer d'abord, puis attendre la confirmation")
    require_confirmation(agent["launch"])
    write_json(agent_path(slug), {k: v for k, v in agent.items() if k != "launch"})
    return execute(slug)


def execute(slug: str, idempotency_key: Optional[str] = None) -> dict:
    """Gather the agent's preparations in order, publish them, then trigger its job's run with them."""
    agent = active_agent(slug)
    steps = agent["config"].get("preparations", [])
    cursors = agent.get("cursors", {})
    found = [agent_connectors.prepare(step, cursors.get(str(i), 0)) for i, step in enumerate(steps)]
    rows = [[i + 1, step["type"], f["source"], f["content"]] for i, (step, f) in enumerate(zip(steps, found))]
    rows += [
        [len(rows) + i + 1, "file", name, agent_files.read(slug, name)["content"]]
        for i, name in enumerate(agent["config"].get("files", []))
    ]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    columns = ["order", "type", "source", "content"]
    dataset = job_inputs.publish_dataset(f"agent-{slug}-{stamp}", columns, rows, fmt="jsonl") if rows else None
    run = jobs.trigger_run(
        agent["pipeline_id"], input_uri=dataset["url"] if dataset else None, idempotency_key=idempotency_key
    )
    cursors = {**cursors, **{str(i): f["next_cursor"] for i, f in enumerate(found) if "next_cursor" in f}}
    runs = [*agent.get("pending_runs", []), run["id"]]
    write_json(agent_path(slug), {**agent, "pending_runs": runs, **({"cursors": cursors} if cursors else {})})
    logger.info("agent %s run %s lancé, entrée de %d caractères", slug, run["id"], sum(len(str(r[3])) for r in rows))
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
    if not isinstance(output, dict) or "deliveries" not in output:
        raise ValueError(f"sortie du run {run_id} sans liste deliveries")
    declared = agent["config"].get("files", [])
    fed = {
        e["destination"][5:]
        for e in output["deliveries"]
        if isinstance(e, dict) and str(e.get("destination")).startswith("file:")
    }
    if errors := agent_files.output_errors(output.get("files", []), declared, fed):
        raise ValueError(f"sortie du run {run_id} refusée, rien n'est écrit : " + " ; ".join(errors))
    subagents = agent["config"].get("subagents")
    chain = partial(agent_subagents.run_chain, subagents) if subagents else None
    summary = agent_delivery.deliver(agent["config"], str(uuid.UUID(run_id)), output["deliveries"], chain)
    summary = file_entries(slug, run_id, summary)
    for f in output.get("files", []):
        agent_files.write_version(slug, f["name"], f["content"], f"run {run_id}")
    trace_path = f"{slug}/runs/{run_id}.json"
    calls = (read_json(trace_path) or {}).get("subagent_calls", 0) + sum(e["calls"] for e in summary)
    write_json(trace_path, {"delivered_at": datetime.now().isoformat(timespec="seconds"), "subagent_calls": calls})
    logger.info("agent %s run %s livré, %d appels aux sous-agents au total", slug, run_id, calls)
    retry = any(e["status"] == "subagent_failed" for e in summary)
    pending = [r for r in agent.get("pending_runs", []) if r != run_id or retry]
    write_json(agent_path(slug), {**agent, "pending_runs": pending})
    return summary


def file_entries(slug: str, run_id: str, summary: list[dict]) -> list[dict]:
    """Put the run's productions aimed at a file into it, one new version per file; they become range."""
    ranged = {}
    for item in summary:
        if item["status"] == "to_file":
            ranged.setdefault(item["destination"][5:], []).append(item)
    for name, items in ranged.items():
        records = [agent_delivery.show(slug, item["id"]) for item in items]
        entries = [(r.get("key") or item["id"], r["title"], r["text"]) for item, r in zip(items, records)]
        version = agent_files.add_entries(slug, name, entries, f"run {run_id}")
        for item, record in zip(items, records):
            write_json(f"{slug}/envois/{item['id']}.json", {**record, "status": "filed", "version": version})
            item["status"] = "filed"
    return summary


def due(schedule: object) -> bool:
    """Why: the one daily batch decides the day; days of the week cover every rhythm the batch can honour."""
    if isinstance(schedule, dict):
        day = cron.last_batch_start("maintenance", cron.utcnow()).weekday()
        return agent_config.WEEKDAYS[day] in schedule["weekdays"]
    return cron.is_due(schedule, "maintenance")


def tick() -> None:
    """Daily: deliver every active agent's completed runs, then launch the agents whose cadence is due."""
    failed = []
    for slug in s3.agents.list_directories(""):
        agent = None if slug.startswith("_") else read_json(agent_path(slug))
        if agent is None or agent["status"] != "active":
            continue
        try:
            retry = [
                run_id
                for run_id in agent.get("pending_runs", [])
                if jobs.get_run(run_id).get("status") == "completed"
                and any(e["status"] == "subagent_failed" for e in deliver_run(slug, run_id))
            ]
            schedule = agent["config"].get("schedule")
            if schedule and due(schedule):
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


def present_delivery(slug: str, delivery_id: str) -> dict:
    """A production awaiting review, marked as shown so that only a later message may approve it."""
    active_agent(slug)
    record = agent_delivery.show(slug, delivery_id)
    record["shown"] = mark()
    write_json(f"{slug}/envois/{delivery_id}.json", record)
    return record


def approve_delivery(slug: str, delivery_id: str) -> dict:
    active_agent(slug)
    record = agent_delivery.show(slug, delivery_id)
    if "shown" not in record:
        raise PermissionError("envoi jamais présenté : le montrer d'abord, puis attendre la confirmation")
    return agent_delivery.approve(slug, delivery_id, require_confirmation(record["shown"]))


def agent_file(slug: str, name: str) -> dict:
    agent = active_agent(slug)
    if name not in agent["config"].get("files", []):
        raise ValueError(
            f"l'agent {slug} n'a pas de fichier {name} ; fichiers : {', '.join(agent['config'].get('files', []))}"
        )
    return agent


def read_file(slug: str, name: str, version: Optional[int] = None) -> dict:
    agent_file(slug, name)
    return agent_files.read(slug, name, version)


def file_history(slug: str, name: str) -> list[dict]:
    agent_file(slug, name)
    return agent_files.history(slug, name)


def compare_file(slug: str, name: str, old: int, new: int) -> str:
    agent_file(slug, name)
    return agent_files.compare(slug, name, old, new)


def present_file_revert(slug: str, name: str, version: int) -> dict:
    """What a return to an earlier version would change, marked as shown so that only a later message may apply it."""
    agent = agent_file(slug, name)
    current = agent_files.read(slug, name)["version"]
    diff = agent_files.compare(slug, name, current, version)
    write_json(agent_path(slug), {**agent, "file_revert": {"name": name, "version": version, "shown": mark()}})
    return {"agent": slug, "file": name, "old": current, "new": version, "diff": diff}


def revert_file(slug: str, name: str) -> dict:
    """Write the proposed earlier version as a new one, only when confirmed in a later message; history is kept."""
    agent = agent_file(slug, name)
    proposed = agent.get("file_revert")
    if not proposed or proposed["name"] != name:
        raise PermissionError("retour jamais proposé : le proposer d'abord, puis attendre la confirmation")
    approved_by = require_confirmation(proposed["shown"])
    write_json(agent_path(slug), {k: v for k, v in agent.items() if k != "file_revert"})
    content = agent_files.read(slug, name, proposed["version"])["content"]
    version = agent_files.write_version(
        slug, name, content, f"retour à la version {proposed['version']} par {approved_by}"
    )
    return {"agent": slug, "file": name, "version": version}
