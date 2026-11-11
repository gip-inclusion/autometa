"""Deliver an agent's productions to its Slack and Notion destinations, as its mode allows: publish or not, review or not."""

import logging
import re
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from lib import agent_config, agent_files, notion, slack
from web import config
from web.db import get_db
from web.helpers import to_local
from web.models import Agent, AgentDelivery, AgentRun

logger = logging.getLogger(__name__)

__all__ = [
    "DeliveryNotPending",
    "approve",
    "build_digests",
    "file_entries",
    "record",
    "reject",
    "run_subagents",
    "send",
    "send_pending",
    "show",
    "summary",
    "validate_output",
]

# Why: a production aimed at one of the agent's own files stays in Autometa, so it needs no mode.
FILE_MODE = "file"
DELIVERY_FIELDS = {"destination", "title", "text", "key"}
# Why: Slack cuts a message at 40 000 characters and a digest past a few screens is not read; beyond
# this, the digest keeps its first lines and says how many it leaves out.
DIGEST_MAX = 8_000
# Why: bounds on one run's output: the worker is told 50 at most; Notion refuses a title past 2 000
# characters and a text past this would be cut by Slack anyway.
DELIVERIES_MAX = 200
TITLE_MAX = 300
TEXT_MAX = 20_000
# Why: a write or a sub-agent chain that fails the same way N times will not succeed on its own; it is
# set aside as failed, visible and retryable by approval, instead of blocking the run or the digest.
SEND_ATTEMPTS_MAX = 3
SUBAGENT_ATTEMPTS_MAX = 3
# Why: a delivery left sending past this was taken by a process that died before recording the outcome.
CLAIM_TIMEOUT = timedelta(hours=1)
LINK = re.compile(r"https?://[^\s)>\]]+")


class DeliveryNotPending(ValueError):
    """A decision on a delivery that does not await it; status is None when the delivery does not exist."""

    def __init__(self, delivery_id: int, status: str | None, expected: str):
        super().__init__(f"envoi {delivery_id} est {status or 'introuvable'}, attendu {expected}")
        self.status = status


def now() -> datetime:
    return datetime.now(timezone.utc)


def delivery_errors(index: int, delivery: object, modes: dict[str, str]) -> list[str]:
    path = f"deliveries[{index}]"
    if not isinstance(delivery, dict) or not {"destination", "title", "text"} <= set(delivery) <= DELIVERY_FIELDS:
        return [f"{path} : attendu destination, title, text et, pour Notion ou un fichier, key."]
    if delivery["destination"] not in modes:
        return [
            f"{path} : la destination {delivery['destination']!r} n'est ni une destination de l'agent "
            "ni file:<nom> d'un de ses fichiers."
        ]
    if not all(isinstance(delivery[k], str) and delivery[k].strip() for k in ("title", "text")):
        return [f"{path} : title et text doivent être des textes non vides."]
    if len(delivery["title"]) > TITLE_MAX or len(delivery["text"]) > TEXT_MAX:
        return [f"{path} : title de {TITLE_MAX} caractères au plus, text de {TEXT_MAX} au plus."]
    if "key" in delivery and not (
        isinstance(delivery["key"], str) and re.fullmatch(r"[a-z0-9-]{1,80}", delivery["key"])
    ):
        return [f"{path} : key en minuscules, chiffres et tirets, 80 caractères au plus."]
    return []


def modes_of(agent: dict) -> dict[str, str]:
    """Each destination of the agent with its mode, and file:<name> for each of its files."""
    modes = {d["id"]: d["mode"] for d in agent["destinations"]}
    return modes | {f"file:{name}": FILE_MODE for name in agent.get("files", [])}


def validate_output(agent: dict, run_id: str, output: object, current_files: dict[str, str]) -> list[str]:
    """Every reason to refuse a run's output as a whole; empty when it may be recorded."""
    if errors := agent_config.validate(agent):
        return ["configuration d'agent refusée : " + " ; ".join(errors)]
    if not isinstance(output, dict) or not isinstance(output.get("deliveries"), list):
        return ["deliveries : attendu une liste"]
    deliveries = output["deliveries"]
    if len(deliveries) > DELIVERIES_MAX:
        return [f"deliveries : {len(deliveries)} envois, {DELIVERIES_MAX} au plus par run"]
    modes = modes_of(agent)
    if errors := [e for i, d in enumerate(deliveries) for e in delivery_errors(i, d, modes)]:
        return errors
    fed = {d["destination"][5:] for d in deliveries if d["destination"].startswith("file:")}
    if errors := agent_files.output_errors(output.get("files", []), agent.get("files", []), fed):
        return errors
    return [
        f"file:{name} : avec les envois de ce run, le fichier passerait {agent_config.AGENT_FILE_MAX} caractères."
        for name in sorted(fed)
        if len(agent_files.with_entries(current_files[name], file_entries_of(deliveries, name, run_id)))
        > agent_config.AGENT_FILE_MAX
    ]


def file_entries_of(deliveries: list[dict], name: str, run_id: str) -> list[tuple[str, str, str]]:
    return [
        (d.get("key") or f"{run_id}-{i}", d["title"], d["text"])
        for i, d in enumerate(deliveries)
        if d["destination"] == f"file:{name}"
    ]


def initial_status(mode: str) -> str:
    """Recorded only, awaiting review, or ready to send, by the mode's two flags; to_file for an agent's file."""
    if mode == FILE_MODE:
        return "to_file"
    flags = agent_config.MODES[mode]
    if not flags["can_publish"]:
        return "recorded"
    return "pending_review" if flags["review_required"] else "pending_send"


def digests(agent: dict) -> set[str]:
    return {d["id"] for d in agent["destinations"] if d.get("grouping") == "digest"}


def kept_status(agent: dict, destination: str, mode: str) -> str:
    return "grouped" if destination in digests(agent) else initial_status(mode)


def record(session: Session, agent: dict, run_id: str, deliveries: list[dict]) -> None:
    """One row per production of an accepted output; a production already recorded for that rank is left as is."""
    modes, chained = modes_of(agent), bool(agent.get("subagents"))
    for rank, d in enumerate(deliveries):
        exists = session.scalar(
            select(AgentDelivery.id).where(AgentDelivery.run_id == run_id, AgentDelivery.rank == rank)
        )
        if exists is not None:
            continue
        mode = modes[d["destination"]]
        session.add(
            AgentDelivery(
                run_id=run_id,
                rank=rank,
                destination=d["destination"],
                mode=mode,
                status="pending_subagents" if chained else kept_status(agent, d["destination"], mode),
                title=d["title"],
                text=d["text"],
                key=d.get("key") or (f"{run_id}-{rank}" if mode == FILE_MODE else None),
            )
        )
    session.flush()
    for row in session.scalars(
        select(AgentDelivery).where(AgentDelivery.run_id == run_id).order_by(AgentDelivery.rank)
    ):
        # Why: productions may carry personal data; logs name the delivery, never its title or text.
        logger.info(
            "agent %s envoi %s vers %s, mode %s : %s", agent["slug"], row.id, row.destination, row.mode, row.status
        )


def run_subagents(agent: dict, delivery_id: int, chain: Callable[[dict], dict]) -> int:
    """Pass one production through the agent's sub-agents; returns the calls made. A failure is retried, then set aside."""
    with get_db() as session:
        row = session.get(AgentDelivery, delivery_id)
        production = {"destination": row.destination, "title": row.title, "text": row.text}
    trace = chain(production)
    with get_db() as session:
        row = session.get(AgentDelivery, delivery_id, with_for_update=True)
        if row.status != "pending_subagents":
            return 0
        row.subagent_steps = trace["steps"]
        if trace["failure"]:
            row.subagent_attempts += 1
            row.error = trace["failure"]
            if row.subagent_attempts >= SUBAGENT_ATTEMPTS_MAX:
                row.status = "subagent_failed"
            logger.warning("agent envoi %s : %s", delivery_id, trace["failure"])
        else:
            row.title, row.text = trace["delivery"]["title"], trace["delivery"]["text"]
            row.labels = trace["delivery"].get("labels", [])
            row.error = None
            discarded = any(s.get("kept") is False for s in trace["steps"])
            row.status = "discarded" if discarded else kept_status(agent, row.destination, row.mode)
        session.execute(
            update(AgentRun)
            .where(AgentRun.id == row.run_id)
            .values(subagent_calls=AgentRun.subagent_calls + trace["calls"])
        )
    return trace["calls"]


def file_entries(session: Session, agent_id: int, run_id: str) -> None:
    """Put the run's productions aimed at a file into it, one new version per file; they become filed."""
    rows = session.scalars(
        select(AgentDelivery)
        .where(AgentDelivery.run_id == run_id, AgentDelivery.status == "to_file")
        .order_by(AgentDelivery.rank)
    ).all()
    by_file: dict[str, list[AgentDelivery]] = {}
    for row in rows:
        by_file.setdefault(row.destination[5:], []).append(row)
    for name, items in by_file.items():
        content = agent_files.read(session, agent_id, name)["content"]
        entries = [(r.key, r.title, r.text) for r in items]
        version = agent_files.write_version(
            session, agent_id, name, agent_files.with_entries(content, entries), f"run {run_id}"
        )
        for r in items:
            r.status, r.file_version = "filed", version


def build_digests(session: Session, agent: dict, run: AgentRun) -> None:
    """One delivery per run and digest destination, once none of its productions waits for its sub-agents."""
    for destination in sorted(digests(agent)):
        members = session.scalars(
            select(AgentDelivery)
            .where(
                AgentDelivery.run_id == run.id,
                AgentDelivery.destination == destination,
                AgentDelivery.rank.is_not(None),
            )
            .order_by(AgentDelivery.rank)
        ).all()
        exists = session.scalar(
            select(AgentDelivery.id).where(
                AgentDelivery.run_id == run.id, AgentDelivery.destination == destination, AgentDelivery.rank.is_(None)
            )
        )
        # Why: a production whose sub-agents still retry is waited for; the digest is built once, never again.
        if exists is not None or not members or any(m.status == "pending_subagents" for m in members):
            continue
        kept = [m for m in members if m.status == "grouped"]
        mode = next(d["mode"] for d in agent["destinations"] if d["id"] == destination)
        digest = AgentDelivery(
            run_id=run.id,
            rank=None,
            destination=destination,
            mode=mode,
            status=initial_status(mode),
            title=f"{agent['title']}, run du {to_local(run.launched_at):%d/%m/%Y} : retenus {len(kept)}, "
            f"écartés {len(members) - len(kept)}",
            text=digest_text(agent, kept, run.files_written),
        )
        session.add(digest)
        session.flush()
        for m in kept:
            m.digest_id = digest.id


def digest_text(agent: dict, kept: list[AgentDelivery], files_written: list[dict]) -> str:
    labels = [e["name"] for o in agent.get("subagents", []) for e in o.get("labels", [])]
    sections: dict[str, list[str]] = {heading: [] for heading in [*labels, "Autres"]}
    for row in kept:
        link = LINK.search(row.text)
        line = f"- {row.title}" + (f" : {link.group(0)}" if link else "")
        # Why: a production stands in every section of its labels, and under Autres only without any.
        for heading in [label for label in labels if label in row.labels] or ["Autres"]:
            sections[heading].append(line)
    text = digest_lines({h: rows for h, rows in sections.items() if rows}) or "Aucune production retenue."
    # Why: a file the worker rewrote after reading untrusted sources becomes its next instructions; say so.
    rewritten = [
        f"- {f['name']} : version {f['version']}, {f['size']} caractères (avant : {f['previous_size']}) ; "
        f"comparer avec la commande diff du skill agents"
        for f in files_written
    ]
    return text + ("\n\n## Fichiers réécrits par ce run, à relire\n" + "\n".join(rewritten) if rewritten else "")


def digest_lines(sections: dict[str, list[str]]) -> str:
    """Sections in order, one line per production, cut to DIGEST_MAX with the number of lines left out."""
    entries = [(heading, row) for heading, rows in sections.items() for row in rows]
    lines, kept = [], 0
    for heading, row in entries:
        added = [] if f"## {heading}" in lines else [*([""] if lines else []), f"## {heading}"]
        if len("\n".join([*lines, *added, row])) > DIGEST_MAX:
            break
        lines += [*added, row]
        kept += 1
    if kept < len(entries):
        lines += ["", f"{len(entries) - kept} lignes omises au-delà de {DIGEST_MAX} caractères."]
    return "\n".join(lines)


def slack_text(title: str, text: str) -> str:
    """Escape Slack control sequences so a model cannot ping a channel or forge a link."""
    escaped = [s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for s in (title, text)]
    return f"*{escaped[0]}*\n\n{escaped[1]}"


def target(destination: str) -> str:
    found = config.AGENT_DESTINATION_TARGETS.get(destination)
    if not found:
        raise RuntimeError(f"destination {destination} sans identifiant dans AGENT_DESTINATION_TARGETS")
    return found


def known_page(session: Session, row: AgentDelivery) -> str | None:
    """The Notion page this production already wrote, or an earlier one of the same agent, destination and key."""
    if row.notion_page_id or not row.key:
        return row.notion_page_id
    agent_id = select(AgentRun.agent_id).where(AgentRun.id == row.run_id).scalar_subquery()
    return session.scalar(
        select(AgentDelivery.notion_page_id)
        .join(AgentRun, AgentRun.id == AgentDelivery.run_id)
        .where(
            AgentRun.agent_id == agent_id,
            AgentDelivery.destination == row.destination,
            AgentDelivery.key == row.key,
            AgentDelivery.notion_page_id.is_not(None),
        )
        .order_by(AgentDelivery.id.desc())
        .limit(1)
    )


def write_notion(delivery_id: int, database_id: str, title: str, text: str) -> None:
    """Why: the page id is kept as soon as the page exists, so a retry replaces it instead of creating another."""
    with get_db() as session:
        page_id = known_page(session, session.get(AgentDelivery, delivery_id))
    if page_id:
        page = notion.replace_page(database_id, page_id, title, text)
        with get_db() as session:
            session.execute(
                update(AgentDelivery)
                .where(AgentDelivery.id == delivery_id)
                .values(notion_page_id=page["id"], notion_page_url=page["url"])
            )
    else:
        page = notion.create_page(database_id, title)
        with get_db() as session:
            session.execute(
                update(AgentDelivery)
                .where(AgentDelivery.id == delivery_id)
                .values(notion_page_id=page["id"], notion_page_url=page["url"])
            )
        notion.append_markdown(page["id"], text)


def write(delivery_id: int, destination: str, title: str, text: str) -> None:
    """Write one production to its destination; raises on any refusal."""
    found = target(destination)
    if agent_config.known_destinations()[destination]["channel"] == "notion":
        write_notion(delivery_id, found, title, text)
        return
    if not config.AGENT_SLACK_BOT_TOKEN:
        raise RuntimeError("AGENT_SLACK_BOT_TOKEN absent : le bot Slack des agents n'est pas configuré")
    if not slack.post_message(config.AGENT_SLACK_BOT_TOKEN, found, slack_text(title, text)):
        raise RuntimeError("Slack a refusé le message")


def claim(delivery_id: int) -> AgentDelivery | None:
    """Take a delivery for sending, once: only one process gets it, and a failed attempt counts."""
    with get_db() as session:
        row = session.scalar(
            update(AgentDelivery)
            .where(
                AgentDelivery.id == delivery_id,
                or_(
                    AgentDelivery.status == "pending_send",
                    (AgentDelivery.status == "sending") & (AgentDelivery.claimed_at < now() - CLAIM_TIMEOUT),
                ),
            )
            .values(status="sending", claimed_at=now(), attempts=AgentDelivery.attempts + 1)
            .returning(AgentDelivery)
        )
        if row is not None:
            session.expunge(row)
        return row


def refusal(agent: Agent, row: AgentDelivery) -> str | None:
    """Why a delivery taken for sending may no longer go under its agent's current configuration; None when it may."""
    if agent.status != "active":
        return f"agent {agent.slug} {agent.status}"
    found = [(i, c) for i, c in enumerate(agent.config["destinations"]) if c["id"] == row.destination]
    if not found:
        return f"{row.destination} n'est plus une destination de l'agent"
    index, contact = found[0]
    if errors := agent_config.destination_errors(agent.slug, index, contact, agent_config.known_destinations()):
        return errors[0]
    flags = agent_config.MODES[contact["mode"]]
    if not flags["can_publish"]:
        return f"le mode {contact['mode']} de {row.destination} ne publie pas"
    if flags["review_required"] and not row.approved_by:
        return f"le mode {contact['mode']} de {row.destination} demande une relecture, l'envoi n'est pas approuvé"
    return None


def send(delivery_id: int) -> str:
    """Write a delivery ready to send, recording its outcome; returns its status. A failure is recorded, not raised."""
    row = claim(delivery_id)
    if row is None:
        return show_status(delivery_id)
    with get_db() as session:
        agent = session.scalar(
            select(Agent).join(AgentRun, AgentRun.agent_id == Agent.id).where(AgentRun.id == row.run_id)
        )
        slug, error = agent.slug, refusal(agent, row)
    # Why: the configuration may have changed since the collect; a delivery goes only as the current one allows.
    status = "refused" if error else "sent"
    if error:
        logger.warning("agent envoi %s vers %s refusé : %s", row.id, row.destination, error)
    else:
        try:
            write(row.id, row.destination, row.title, row.text)
        # Why: Slack may answer something that is not JSON (ValueError), Notion an HTTP error; each is an outcome.
        except (RuntimeError, ValueError, httpx.HTTPError) as exc:
            status = "failed" if row.attempts >= SEND_ATTEMPTS_MAX else "pending_send"
            error = str(exc)
            logger.warning(
                "agent envoi %s vers %s en échec (essai %d) : %s", row.id, row.destination, row.attempts, exc
            )
    with get_db() as session:
        session.execute(
            update(AgentDelivery)
            .where(AgentDelivery.id == row.id)
            .values(status=status, error=error, sent_at=now() if status == "sent" else None)
        )
    logger.info("agent %s envoi %s vers %s, mode %s : %s", slug, row.id, row.destination, row.mode, status)
    return status


def show_status(delivery_id: int) -> str:
    with get_db() as session:
        return session.scalar(select(AgentDelivery.status).where(AgentDelivery.id == delivery_id))


def send_pending(slug: str | None = None, run_id: str | None = None) -> list[str]:
    """Send every delivery ready to send of active agents; returns the errors of those that failed."""
    with get_db() as session:
        query = (
            select(AgentDelivery.id)
            .join(AgentRun, AgentRun.id == AgentDelivery.run_id)
            .join(Agent, Agent.id == AgentRun.agent_id)
            .where(Agent.status == "active", AgentDelivery.status.in_(("pending_send", "sending")))
            .order_by(AgentDelivery.id)
        )
        if slug:
            query = query.where(Agent.slug == slug)
        if run_id:
            query = query.where(AgentDelivery.run_id == run_id)
        ids = session.scalars(query).all()
    return [f"envoi {i} {status}" for i in ids if (status := send(i)) in ("failed", "pending_send", "refused")]


def as_dict(row: AgentDelivery) -> dict:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "rank": row.rank,
        "destination": row.destination,
        "mode": row.mode,
        "status": row.status,
        "title": row.title,
        "text": row.text,
        "key": row.key,
        "labels": row.labels,
        "subagent_steps": row.subagent_steps,
        "attempts": row.attempts,
        "error": row.error,
        "digest_id": row.digest_id,
        "notion_page_url": row.notion_page_url,
        "file_version": row.file_version,
        "approved_by": row.approved_by,
    }


def show(session: Session, agent_id: int, delivery_id: object) -> AgentDelivery:
    row = (
        session.scalar(
            select(AgentDelivery)
            .join(AgentRun, AgentRun.id == AgentDelivery.run_id)
            .where(AgentDelivery.id == int(str(delivery_id)), AgentRun.agent_id == agent_id)
        )
        if str(delivery_id).isdigit()
        else None
    )
    if row is None:
        raise ValueError(f"envoi {delivery_id} introuvable pour cet agent")
    return row


def approve(delivery_id: int, approved_by: str) -> str:
    """Send a delivery awaiting review, or retry a failed one; anything else is refused without writing."""
    with get_db() as session:
        row = session.get(AgentDelivery, delivery_id, with_for_update=True)
        if row is None or row.status not in ("pending_review", "failed"):
            raise DeliveryNotPending(delivery_id, row and row.status, "pending_review ou failed")
        row.status, row.attempts, row.approved_by = "pending_send", 0, approved_by
    return send(delivery_id)


def reject(delivery_id: int, rejected_by: str) -> None:
    """Set aside a delivery awaiting review, writing nothing anywhere; anything else is refused."""
    with get_db() as session:
        row = session.get(AgentDelivery, delivery_id, with_for_update=True)
        if row is None or row.status != "pending_review":
            raise DeliveryNotPending(delivery_id, row and row.status, "pending_review")
        row.status, row.error = "rejected", f"refusé à la relecture par {rejected_by}"
        rejected = row.id
    logger.info("agent envoi %d refusé à la relecture", rejected)


def summary(session: Session, run_id: str, calls: dict[int, int]) -> list[dict]:
    """Why: productions may carry personal data; what is reported names each delivery, never its title or text."""
    rows = session.scalars(
        select(AgentDelivery).where(AgentDelivery.run_id == run_id).order_by(AgentDelivery.rank.nulls_last())
    ).all()
    return [
        {"id": r.id, "destination": r.destination, "mode": r.mode, "status": r.status, "calls": calls.get(r.id, 0)}
        for r in rows
    ]
