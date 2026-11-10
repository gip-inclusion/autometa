"""Agents: jobs created after a confirmation in a later message, retired the same way, their runs delivered by phases."""

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from functools import partial
from typing import Optional

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from lib import agent_config, agent_connectors, agent_delivery, agent_files, agent_subagents, job_inputs, jobs
from web import config, cron
from web.db import get_db
from web.models import Agent, AgentDelivery, AgentProposal, AgentRun, Message

logger = logging.getLogger(__name__)

__all__ = [
    "plan",
    "apply",
    "present_retire",
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
- title : une ligne, {title_max} caractères au plus. text : en markdown, {text_max} caractères au plus.
- Un envoi par élément (un ticket, un signal, une opportunité) : les sous-agents d'Autometa jugent
  chaque envoi à part, un envoi qui en regroupe plusieurs serait jugé en bloc. {deliveries_max} envois au plus.
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

SLUG = re.compile(r"[a-z][a-z0-9-]{2,40}")


def now() -> datetime:
    return datetime.now(timezone.utc)


def lock(session: Session, slug: str) -> None:
    """Serialize every change to one agent until the transaction ends."""
    session.execute(select(func.pg_advisory_xact_lock(func.hashtext(f"agent:{slug}"))))


def last_user_message_id(conversation_id: str) -> int:
    with get_db() as session:
        found = session.scalar(
            select(func.max(Message.id)).where(
                Message.conversation_id == conversation_id, func.coalesce(Message.type, Message.role) == "user"
            )
        )
    return found or 0


def propose(session: Session, slug: str, action: str, payload: dict) -> AgentProposal:
    """Record what is shown to the user, where and after which message; only a later message may confirm it."""
    conversation_id = config.agent_conversation_id()
    if not conversation_id:
        raise ValueError("une proposition se présente et se confirme dans une conversation")
    proposal = AgentProposal(
        id=f"{datetime.now():%Y-%m-%d-%H%M%S}-{slug}-{uuid.uuid4().hex[:6]}",
        agent_slug=slug,
        action=action,
        payload=payload,
        status="planned",
        conversation_id=conversation_id,
        after_message_id=last_user_message_id(conversation_id),
    )
    session.add(proposal)
    session.flush()
    return proposal


def confirm(session: Session, proposal: AgentProposal) -> str:
    """The confirming user's email, once a later message of the same conversation exists; the proposal is spent."""
    # Why: a guard against a chat agent in a hurry, not a barrier: the conversation id and the email
    # come from the chat agent's own environment, which it could change.
    conversation_id = config.agent_conversation_id()
    if conversation_id != proposal.conversation_id:
        raise PermissionError("la confirmation doit venir de la conversation où la proposition a été présentée")
    if last_user_message_id(conversation_id) <= proposal.after_message_id:
        raise PermissionError("aucune confirmation : attendre un message ultérieur de l'utilisateur")
    decided_by = config.agent_user_email() or "inconnu"
    spent = session.scalar(
        update(AgentProposal)
        .where(AgentProposal.id == proposal.id, AgentProposal.status == "planned")
        .values(status="applied", decided_by=decided_by, decided_at=now())
        .returning(AgentProposal.id)
    )
    if spent is None:
        raise ValueError(f"proposition {proposal.id} déjà utilisée")
    session.refresh(proposal)
    return decided_by


def pending(session: Session, slug: str, action: str, never: str, **payload) -> AgentProposal:
    """The latest planned proposal of this action for the agent, matching payload; refused when there is none."""
    query = (
        select(AgentProposal)
        .where(AgentProposal.agent_slug == slug, AgentProposal.action == action, AgentProposal.status == "planned")
        .order_by(AgentProposal.created_at.desc(), AgentProposal.id.desc())
    )
    for key, value in payload.items():
        query = query.where(AgentProposal.payload[key].astext == str(value))
    found = session.scalars(query.limit(1)).first()
    if found is None:
        raise PermissionError(f"{never} jamais proposé : le proposer d'abord, puis attendre la confirmation")
    return found


def find_agent(session: Session, slug: str) -> Agent | None:
    return session.scalar(select(Agent).where(Agent.slug == slug)) if SLUG.fullmatch(slug) else None


def active_agent(session: Session, slug: str) -> Agent:
    agent = find_agent(session, slug)
    if agent is None or agent.status != "active":
        raise ValueError(f"aucun agent actif {slug}")
    return agent


def as_manifest(proposal: AgentProposal) -> dict:
    return {
        "id": proposal.id,
        "status": proposal.status,
        "kind": proposal.action,
        **proposal.payload,
        "shown": {"conversation_id": proposal.conversation_id, "after_message_id": proposal.after_message_id},
        "decided_by": proposal.decided_by,
    }


def system_prompt_of(doc: dict, instructions: str) -> str:
    files = doc.get("files", [])
    destinations = ", ".join([*(c["id"] for c in doc["destinations"]), *(f"file:{f}" for f in files)])
    steps = ", ".join([
        *(agent_connectors.label(p) for p in doc.get("preparations", [])),
        *(f"file {f}" for f in files),
    ])
    output = OUTPUT_CONTRACT.format(
        destinations=destinations,
        title_max=agent_delivery.TITLE_MAX,
        text_max=agent_delivery.TEXT_MAX,
        deliveries_max=agent_delivery.DELIVERIES_MAX,
    )
    return (
        instructions
        + output
        + (INPUT_CONTRACT.format(preparations=steps) if steps else "")
        + (FILES_CONTRACT.format(files=", ".join(files), size=agent_config.AGENT_FILE_MAX) if files else "")
    )


def plan(config_yaml: str, instructions: str, initial_files: Optional[dict[str, str]] = None) -> dict:
    """Validate an agent and record its creation or change as a proposal; nothing is created in the jobs engine."""
    doc = agent_config.parse(config_yaml)
    initial_files = initial_files or {}
    if errors := agent_config.validate(doc) + agent_config.initial_errors(initial_files, doc.get("files", [])):
        raise ValueError("configuration refusée : " + " ; ".join(errors))
    if not instructions.strip():
        raise ValueError("consigne du job vide")
    with get_db() as session:
        current = find_agent(session, doc["slug"])
        if current is not None and current.status != "active":
            raise ValueError(f"l'identifiant {doc['slug']} est déjà pris par un agent retiré")
        payload = {
            "config": doc,
            "system_prompt": system_prompt_of(doc, instructions),
            "review": agent_config.describe(doc)
            + [
                f"valeur initiale de {name} : {len(c)} caractères, écrite à la création si le fichier est vide"
                for name, c in initial_files.items()
            ],
            "initial_files": initial_files,
            **({"previous_changeset": current.changeset_id} if current else {}),
        }
        proposal = propose(session, doc["slug"], "update" if current else "create", payload)
        return as_manifest(proposal)


def load(session: Session, changeset_id: str, status: str) -> AgentProposal:
    proposal = session.get(AgentProposal, changeset_id)
    if proposal is None or proposal.action not in ("create", "update"):
        raise ValueError(f"proposition {changeset_id} introuvable")
    if proposal.status != status:
        raise ValueError(f"proposition {changeset_id} est {proposal.status}, attendu {status}")
    return proposal


def apply(changeset_id: str) -> dict:
    """Create or change the agent, only when confirmed in a later message; a stale or second apply does nothing."""
    with get_db() as session:
        slug = load(session, changeset_id, "planned").agent_slug
        lock(session, slug)
        proposal = load(session, changeset_id, "planned")
        current = find_agent(session, slug)
        payload = proposal.payload
        if proposal.action == "create" and current is not None:
            raise ValueError(f"l'agent {slug} existe depuis cette proposition : en proposer une nouvelle")
        if proposal.action == "update" and (current is None or current.changeset_id != payload["previous_changeset"]):
            raise ValueError(f"l'agent {slug} a changé depuis cette proposition : en proposer une nouvelle")
        approved_by = confirm(session, proposal)
        version = current.version + 1 if current else 1
        pipeline_id = current.pipeline_id if current else None
        if current is None or payload["system_prompt"] != current.system_prompt:
            # Why: the jobs engine cannot update a pipeline's prompt; a changed prompt is a new pipeline.
            name = f"agent-{slug}" if version == 1 else f"agent-{slug}-v{version}"
            pipeline_id = jobs.create_pipeline(name, payload["system_prompt"], {"output_format": "json"})["id"]
        if current is None:
            current = Agent(slug=slug, owner_email=approved_by, cursors={})
            session.add(current)
        else:
            previous = {
                "config": current.config,
                "system_prompt": current.system_prompt,
                "pipeline_id": current.pipeline_id,
            }
            proposal.payload = {**payload, "previous": previous}
        current.config, current.system_prompt, current.pipeline_id = (
            payload["config"],
            payload["system_prompt"],
            pipeline_id,
        )
        current.version, current.status, current.changeset_id, current.updated_at = (
            version,
            "active",
            changeset_id,
            now(),
        )
        session.flush()
        for name, content in payload.get("initial_files", {}).items():
            # Why: a file the agent already wrote is its own work; an initial value never overwrites it.
            if not agent_files.latest_version(session, current.id, name):
                agent_files.write_version(
                    session, current.id, name, content, f"valeur initiale, proposition {changeset_id}"
                )
        return {**as_manifest(proposal), "pipeline_id": pipeline_id}


def present_retire(changeset_id: str) -> dict:
    """What retiring an applied proposal would undo, marked as shown so that only a later message may do it."""
    with get_db() as session:
        proposal = load(session, changeset_id, "applied")
        undo = "retire l'agent" if proposal.action == "create" else "rend la configuration et la consigne d'avant"
        propose(session, proposal.agent_slug, "retire", {"changeset": changeset_id})
        return {"agent": proposal.agent_slug, "changeset": changeset_id, "effect": undo}


def revert(changeset_id: str) -> dict:
    """Undo an applied proposal once confirmed: a creation retires the agent, a change restores what it replaced."""
    with get_db() as session:
        slug = load(session, changeset_id, "applied").agent_slug
        lock(session, slug)
        proposal = load(session, changeset_id, "applied")
        agent = find_agent(session, slug)
        if agent.changeset_id != changeset_id:
            raise ValueError(f"proposition {changeset_id} n'est plus la dernière appliquée à l'agent {slug}")
        confirm(session, pending(session, slug, "retire", "retrait", changeset=changeset_id))
        if proposal.action == "create":
            agent.status = "retired"
        else:
            previous = proposal.payload["previous"]
            agent.config, agent.system_prompt = previous["config"], previous["system_prompt"]
            agent.pipeline_id, agent.changeset_id = previous["pipeline_id"], proposal.payload["previous_changeset"]
        agent.updated_at = now()
        proposal.status = "reverted"
        return as_manifest(proposal)


def show(changeset_id: str) -> dict:
    with get_db() as session:
        proposal = session.get(AgentProposal, changeset_id)
        if proposal is None or proposal.action not in ("create", "update"):
            raise ValueError(f"proposition {changeset_id} introuvable")
        return as_manifest(proposal)


def catalogue() -> dict:
    """Everything an agent may use, and whether this instance is configured for it; reads no secret."""
    targets = config.AGENT_DESTINATION_TARGETS
    return {
        "destinations": [
            {"id": d["id"], "channel": d["channel"], "target_configured": bool(targets.get(d["id"]))}
            for d in agent_config.known_destinations().values()
        ],
        "modes": agent_config.MODES,
        "subagents": agent_config.models(),
        "preparations": agent_connectors.catalogue(),
        "cron_tasks": agent_connectors.connector("cron").tasks(),
        "schedules": {"weekdays": list(agent_config.WEEKDAYS), "shortcuts": list(agent_config.SCHEDULES)},
        "files": {"at_most": 5, "max_size": agent_config.AGENT_FILE_MAX},
        "subagents_configured": bool(config.OLLAMA_API_KEY),
    }


def present_launch(slug: str) -> dict:
    """What a run launched now would do, marked as shown so that only a later message may launch it."""
    with get_db() as session:
        agent = active_agent(session, slug)
        propose(session, slug, "launch", {})
        return {"agent": slug, "preparations": agent.config.get("preparations", []), "version": agent.version}


def launch(slug: str) -> dict:
    """Run the agent now, only when confirmed in a later message; the confirmation is spent, never replayed."""
    with get_db() as session:
        active_agent(session, slug)
        confirm(session, pending(session, slug, "launch", "lancement"))
    return execute(slug)


def execute(slug: str, idempotency_key: Optional[str] = None) -> dict:
    """Gather the agent's preparations in order, publish them, then trigger its job's run with them."""
    with get_db() as session:
        agent = active_agent(session, slug)
        agent_id, doc, pipeline_id, cursors = agent.id, agent.config, agent.pipeline_id, dict(agent.cursors)
        files = [agent_files.read(session, agent_id, name)["content"] for name in doc.get("files", [])]
    steps = doc.get("preparations", [])
    found = [agent_connectors.prepare(step, cursors.get(str(i), 0)) for i, step in enumerate(steps)]
    rows = [[i + 1, step["type"], f["source"], f["content"]] for i, (step, f) in enumerate(zip(steps, found))]
    rows += [[len(rows) + i + 1, "file", name, c] for i, (name, c) in enumerate(zip(doc.get("files", []), files))]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    columns = ["order", "type", "source", "content"]
    dataset = job_inputs.publish_dataset(f"agent-{slug}-{stamp}", columns, rows, fmt="jsonl") if rows else None
    run = jobs.trigger_run(pipeline_id, input_uri=dataset["url"] if dataset else None, idempotency_key=idempotency_key)
    moved = {str(i): f["next_cursor"] for i, f in enumerate(found) if "next_cursor" in f}
    with get_db() as session:
        if session.get(AgentRun, run["id"]) is None:
            session.add(AgentRun(id=run["id"], agent_id=agent_id, pipeline_id=pipeline_id, status="launched"))
        if moved:
            session.execute(update(Agent).where(Agent.id == agent_id).values(cursors=Agent.cursors.op("||")(moved)))
    logger.info("agent %s run %s lancé, entrée de %d caractères", slug, run["id"], sum(len(str(r[3])) for r in rows))
    return {"agent": slug, "run_id": run["id"], "preparations": [f"{r[1]} {r[2]}" for r in rows]}


def collect(run_id: str) -> Optional[str]:
    """Turn a finished run into deliveries; a refused, failed or cancelled run becomes a state. Returns any problem."""
    with get_db() as session:
        run = session.get(AgentRun, run_id)
        slug = session.get(Agent, run.agent_id).slug
    status = jobs.get_run(run_id).get("status")
    if status in ("failed", "cancelled"):
        return finish(slug, run_id, status, f"run {status} côté moteur de jobs")
    if status != "completed":
        return None
    raw = jobs.get_run_output(run_id)
    with get_db() as session:
        lock(session, slug)
        run = session.get(AgentRun, run_id)
        agent = session.get(Agent, run.agent_id)
        if run.status != "launched":
            return None
        try:
            output = json.loads(raw)
        except json.JSONDecodeError as exc:
            output, error = None, f"sortie du run {run_id} illisible : {exc}"
        else:
            current = {n: agent_files.read(session, agent.id, n)["content"] for n in agent.config.get("files", [])}
            errors = agent_delivery.validate_output(agent.config, run_id, output, current)
            error = f"sortie du run {run_id} refusée, rien n'est écrit : " + " ; ".join(errors) if errors else None
        if error:
            run.status, run.error, run.collected_at = "refused", error, now()
            logger.warning("agent %s run %s refusé", slug, run_id)
            return error
        agent_delivery.record(session, agent.config, run_id, output["deliveries"])
        written = []
        for f in output.get("files", []):
            previous = agent_files.read(session, agent.id, f["name"])
            version = agent_files.write_version(session, agent.id, f["name"], f["content"], f"run {run_id}")
            if version != previous["version"]:
                size, previous_size = len(f["content"]), len(previous["content"])
                written.append({"name": f["name"], "version": version, "size": size, "previous_size": previous_size})
        run.status, run.files_written, run.collected_at = "collected", written, now()
    return None


def finish(slug: str, run_id: str, status: str, error: str) -> str:
    with get_db() as session:
        lock(session, slug)
        session.execute(
            update(AgentRun)
            .where(AgentRun.id == run_id, AgentRun.status == "launched")
            .values(status=status, error=error, collected_at=now())
        )
    logger.warning("agent %s run %s : %s", slug, run_id, error)
    return error


def process(run_id: str) -> tuple[dict[int, int], list[str]]:
    """Sub-agents, files and digests of a collected run; returns the calls per delivery and the problems."""
    with get_db() as session:
        run = session.get(AgentRun, run_id)
        agent = session.get(Agent, run.agent_id)
        slug, doc = agent.slug, agent.config
        waiting = session.scalars(
            select(AgentDelivery.id)
            .where(AgentDelivery.run_id == run_id, AgentDelivery.status == "pending_subagents")
            .order_by(AgentDelivery.rank)
        ).all()
    chain = partial(agent_subagents.run_chain, doc["subagents"]) if doc.get("subagents") else None
    calls = {i: agent_delivery.run_subagents(doc, i, chain) for i in waiting} if chain else {}
    with get_db() as session:
        lock(session, slug)
        run = session.get(AgentRun, run_id)
        agent_delivery.file_entries(session, run.agent_id, run_id)
        agent_delivery.build_digests(session, doc, run)
        failed = session.scalars(
            select(AgentDelivery.id).where(
                AgentDelivery.id.in_(list(calls)),
                AgentDelivery.status.in_(("pending_subagents", "subagent_failed")),
            )
        ).all()
    return calls, [f"envoi {i} : sous-agent en échec" for i in failed]


def runs_to(status: str) -> list[str]:
    with get_db() as session:
        return list(
            session.scalars(
                select(AgentRun.id)
                .join(Agent, Agent.id == AgentRun.agent_id)
                .where(Agent.status == "active", AgentRun.status == status)
                .order_by(AgentRun.launched_at)
            ).all()
        )


def deliver_run(slug: str, run_id: str) -> list[dict]:
    """Collect, pass through sub-agents and send one run of the agent's job; redelivering writes nothing more."""
    if not re.fullmatch(r"[0-9a-f-]{36}", run_id):
        raise ValueError(f"run {run_id} introuvable")
    with get_db() as session:
        agent = active_agent(session, slug)
        run = session.get(AgentRun, run_id)
        if run is None:
            # Why: a run launched from /jobs rather than by the agent is adopted if it ran the agent's own job.
            if jobs.get_run(run_id).get("pipeline_id") != agent.pipeline_id:
                raise ValueError(f"le run {run_id} n'appartient pas au job de l'agent {slug}")
            session.add(AgentRun(id=run_id, agent_id=agent.id, pipeline_id=agent.pipeline_id, status="launched"))
        elif run.agent_id != agent.id:
            raise ValueError(f"le run {run_id} n'appartient pas au job de l'agent {slug}")
    if error := collect(run_id):
        raise ValueError(error)
    with get_db() as session:
        status = session.get(AgentRun, run_id).status
    if status != "collected":
        raise ValueError(f"le run {run_id} est {status} : pas encore terminé (completed) ou déjà refusé")
    calls, _ = process(run_id)
    agent_delivery.send_pending(slug, run_id)
    with get_db() as session:
        return agent_delivery.summary(session, run_id, calls)


def due(schedule: object) -> bool:
    """Why: the one daily batch decides the day; days of the week cover every rhythm the batch can honour."""
    if isinstance(schedule, dict):
        day = cron.last_batch_start("maintenance", cron.utcnow()).weekday()
        return agent_config.WEEKDAYS[day] in schedule["weekdays"]
    return cron.is_due(schedule, "maintenance")


def tick() -> None:
    """Daily, in phases that each go on past a failure: collect runs, sub-agents and digests, send, launch."""
    problems: list[str] = []
    for run_id in runs_to("launched"):
        try:
            if error := collect(run_id):
                problems.append(error)
        except (RuntimeError, httpx.HTTPError) as exc:
            problems.append(f"run {run_id} : collecte en échec : {exc}")
    for run_id in runs_to("collected"):
        problems += process(run_id)[1]
    problems += agent_delivery.send_pending()
    with get_db() as session:
        active = session.execute(select(Agent.slug, Agent.config).where(Agent.status == "active").order_by(Agent.slug))
        scheduled = [slug for slug, doc in active if doc.get("schedule") and due(doc["schedule"])]
    for slug in scheduled:
        try:
            execute(slug, idempotency_key=f"agent-{slug}-{datetime.now():%Y-%m-%d}")
        except (ValueError, RuntimeError, httpx.HTTPError) as exc:
            problems.append(f"agent {slug} : lancement en échec : {exc}")
    if problems:
        raise RuntimeError(f"{len(problems)} problèmes dans le passage des agents : " + " ; ".join(problems))


def present_delivery(slug: str, delivery_id: str) -> dict:
    """A delivery awaiting review, marked as shown so that only a later message may approve it."""
    with get_db() as session:
        agent = active_agent(session, slug)
        row = agent_delivery.show(session, agent.id, delivery_id)
        propose(session, slug, "approve_delivery", {"delivery": row.id})
        return agent_delivery.as_dict(row)


def approve_delivery(slug: str, delivery_id: str) -> dict:
    with get_db() as session:
        agent = active_agent(session, slug)
        row = agent_delivery.show(session, agent.id, delivery_id)
        approved_by = confirm(session, pending(session, slug, "approve_delivery", "envoi", delivery=row.id))
        row_id = row.id
    status = agent_delivery.approve(row_id, approved_by)
    return {"id": row_id, "status": status, "approved_by": approved_by}


def agent_file(session: Session, slug: str, name: str) -> Agent:
    agent = active_agent(session, slug)
    if name not in agent.config.get("files", []):
        raise ValueError(
            f"l'agent {slug} n'a pas de fichier {name} ; fichiers : {', '.join(agent.config.get('files', []))}"
        )
    return agent


def read_file(slug: str, name: str, version: Optional[int] = None) -> dict:
    with get_db() as session:
        agent = agent_file(session, slug, name)
        return agent_files.read(session, agent.id, name, version)


def file_history(slug: str, name: str) -> list[dict]:
    with get_db() as session:
        return agent_files.history(session, agent_file(session, slug, name).id, name)


def compare_file(slug: str, name: str, old: int, new: int) -> str:
    with get_db() as session:
        return agent_files.compare(session, agent_file(session, slug, name).id, name, old, new)


def present_file_revert(slug: str, name: str, version: int) -> dict:
    """What a return to an earlier version would change, marked as shown so that only a later message may apply it."""
    with get_db() as session:
        agent = agent_file(session, slug, name)
        current = agent_files.latest_version(session, agent.id, name)
        diff = agent_files.compare(session, agent.id, name, current, version)
        propose(session, slug, "revert_file", {"name": name, "version": version})
        return {"agent": slug, "file": name, "old": current, "new": version, "diff": diff}


def revert_file(slug: str, name: str) -> dict:
    """Write the proposed earlier version as a new one, only when confirmed in a later message; history is kept."""
    with get_db() as session:
        lock(session, slug)
        agent = agent_file(session, slug, name)
        proposal = pending(session, slug, "revert_file", "retour", name=name)
        approved_by = confirm(session, proposal)
        target = proposal.payload["version"]
        content = agent_files.read(session, agent.id, name, target)["content"]
        origin = f"retour à la version {target} par {approved_by}"
        version = agent_files.write_version(session, agent.id, name, content, origin)
        return {"agent": slug, "file": name, "version": version}
