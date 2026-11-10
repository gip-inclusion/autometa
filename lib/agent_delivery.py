"""Deliver an agent's productions to its Slack and Notion destinations, as its mode allows: publish or not, review or not."""

import json
import logging
import re
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any, Optional

import httpx

from lib import agent_config, notion, slack
from web import config, s3

logger = logging.getLogger(__name__)

__all__ = ["deliver", "approve", "show", "read_json", "write_json"]

# Why: a production aimed at one of the agent's own files stays in Autometa, so it needs no mode.
FILE_MODE = "file"
DELIVERY_FIELDS = {"destination", "title", "text", "key"}
# Why: Slack cuts a message at 40 000 characters and a digest past a few screens is not read; beyond
# this, the digest keeps its first lines and says how many it leaves out.
DIGEST_MAX = 8_000
LINK = re.compile(r"https?://[^\s)>\]]+")


def read_json(path: str) -> Optional[Any]:
    """Parsed object, None when absent; raises when S3 is unreachable rather than mistaking it for absence."""
    raw = s3.agents.download(path)
    if raw is None:
        if s3.agents.head(path) != {"exists": False}:
            raise RuntimeError(f"S3 read failed for {path}")
        return None
    return json.loads(raw)


def write_json(path: str, data: Any) -> None:
    if not s3.agents.upload(path, json.dumps(data, ensure_ascii=False, indent=1).encode(), "application/json"):
        raise RuntimeError(f"S3 upload failed for {path}")


def delivery_errors(index: int, delivery: object, modes: dict[str, str]) -> list[str]:
    path = f"deliveries[{index}]"
    if not isinstance(delivery, dict) or not {"destination", "title", "text"} <= set(delivery) <= DELIVERY_FIELDS:
        return [f"{path} : attendu destination, title, text et, pour Notion ou un fichier, key."]
    if delivery["destination"] not in modes:
        return [
            f"{path} : la destination {delivery['destination']!r} n'est ni un point de contact de l'agent "
            "ni file:<nom> d'un de ses fichiers."
        ]
    if not all(isinstance(delivery[k], str) and delivery[k].strip() for k in ("title", "text")):
        return [f"{path} : title et text doivent être des textes non vides."]
    if "key" in delivery and not (
        isinstance(delivery["key"], str) and re.fullmatch(r"[a-z0-9-]{1,80}", delivery["key"])
    ):
        return [f"{path} : key en minuscules, chiffres et tirets, 80 caractères au plus."]
    return []


def initial_status(mode: str) -> str:
    """Recorded only, awaiting review, or ready to send, by the mode's two flags; to_file for an agent's file."""
    if mode == FILE_MODE:
        return "to_file"
    flags = agent_config.MODES[mode]
    if not flags["can_publish"]:
        return "recorded"
    return "pending_review" if flags["review_required"] else "pending_send"


def slack_text(title: str, text: str) -> str:
    """Escape Slack control sequences so a model cannot ping a channel or forge a link."""
    escaped = [s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for s in (title, text)]
    return f"*{escaped[0]}*\n\n{escaped[1]}"


def write(slug: str, record: dict) -> dict:
    """Write one production to its destination; returns what the destination gave back."""
    destination_id = record["destination"]
    target = config.AGENT_DESTINATION_TARGETS.get(destination_id)
    if not target:
        raise RuntimeError(f"destination {destination_id} sans identifiant dans AGENT_DESTINATION_TARGETS")
    if agent_config.known_destinations()[destination_id]["channel"] == "slack":
        if not config.AGENT_SLACK_BOT_TOKEN:
            raise RuntimeError("AGENT_SLACK_BOT_TOKEN absent : le bot Slack des agents n'est pas configuré")
        if not slack.post_message(config.AGENT_SLACK_BOT_TOKEN, target, slack_text(record["title"], record["text"])):
            raise RuntimeError("Slack a refusé le message")
        return {}
    page_path = f"{slug}/pages/{destination_id}/{record.get('key')}.json"
    page = read_json(page_path) if record.get("key") else None
    if page:
        page = notion.replace_page(target, page["id"], record["title"], record["text"])
    else:
        page = notion.create_page(target, record["title"], record["text"])
    if record.get("key"):
        write_json(page_path, page)
    return {"page": page}


def send(slug: str, delivery_id: str, record: dict) -> dict:
    """Write a recorded production, keeping its outcome on the record; a failure is recorded, not raised."""
    try:
        record.update(status="sent", sent_at=datetime.now().isoformat(timespec="seconds"), **write(slug, record))
    except (RuntimeError, httpx.HTTPError) as exc:
        logger.warning("agent %s envoi %s vers %s en échec : %s", slug, delivery_id, record["destination"], exc)
        record.update(status="failure", error=str(exc))
    write_json(f"{slug}/envois/{delivery_id}.json", record)
    return record


def log(slug: str, delivery_id: str, record: dict) -> dict:
    """Why: productions may carry personal data; logs name the envoi, never its title or text."""
    logger.info(
        "agent %s envoi %s vers %s, mode %s : %s",
        slug,
        delivery_id,
        record["destination"],
        record["mode"],
        record["status"],
    )
    return {"id": delivery_id, "destination": record["destination"], "mode": record["mode"], "status": record["status"]}


def deliver(agent: dict, run_id: str, deliveries: list, chain: Optional[Callable[[dict], dict]] = None) -> list[dict]:
    """Record every production of a run through its sub-agents, publishing only what its mode allows; failed chains rerun."""
    run_id = str(uuid.UUID(run_id))
    if errors := agent_config.validate(agent):
        raise ValueError("configuration d'agent refusée : " + " ; ".join(errors))
    modes = {c["id"]: c["mode"] for c in agent["destinations"]}
    digests = {c["id"] for c in agent["destinations"] if c.get("grouping") == "digest"}
    modes.update({f"file:{name}": FILE_MODE for name in agent.get("files", [])})
    if not isinstance(deliveries, list):
        raise ValueError("deliveries : attendu une liste")
    if errors := [e for i, delivery in enumerate(deliveries) for e in delivery_errors(i, delivery, modes)]:
        raise ValueError("passage refusé, rien n'est écrit : " + " ; ".join(errors))
    slug, summary = agent["slug"], []
    for i, delivery in enumerate(deliveries):
        delivery_id, calls = f"{run_id}-{i}", 0
        record = read_json(f"{slug}/envois/{delivery_id}.json")
        if record is None or record["status"] == "subagent_failed":
            mode = modes[delivery["destination"]]
            record = {**delivery, "run_id": run_id, "mode": mode, "status": initial_status(mode)}
            if chain:
                trace = chain(delivery)
                calls = trace["calls"]
                record.update(trace["delivery"], subagents=trace["steps"])
                if trace["failure"]:
                    record.update(status="subagent_failed", error=trace["failure"])
                elif any(e.get("kept") is False for e in trace["steps"]):
                    record["status"] = "discarded"
            if delivery["destination"] in digests and record["status"] not in ("discarded", "subagent_failed"):
                record.update(status="grouped", digest=digest_id(run_id, delivery["destination"]))
            write_json(f"{slug}/envois/{delivery_id}.json", record)
            if record["status"] == "pending_send":
                record = send(slug, delivery_id, record)
        summary.append({**log(slug, delivery_id, record), "calls": calls})
    for destination in sorted(digests):
        members = [(item["id"], item["status"]) for item in summary if item["destination"] == destination]
        # Why: a production whose sub-agents failed is retried at the next delivery; the digest waits for it.
        if members and all(status != "subagent_failed" for _, status in members):
            summary.append({**deliver_digest(agent, run_id, destination, modes[destination], members), "calls": 0})
    return summary


def digest_id(run_id: str, destination: str) -> str:
    return f"{run_id}-digest-{destination}"


def digest_text(sections: dict[str, list[str]]) -> str:
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


def deliver_digest(agent: dict, run_id: str, destination: str, mode: str, members: list[tuple[str, str]]) -> dict:
    """One envoi per run and destination gathering its kept productions by label; built once, never rebuilt."""
    slug, delivery_id = agent["slug"], digest_id(run_id, destination)
    if (record := read_json(f"{slug}/envois/{delivery_id}.json")) is not None:
        return log(slug, delivery_id, record)
    kept = [i for i, status in members if status == "grouped"]
    labels = [e["name"] for o in agent.get("subagents", []) for e in o.get("labels", [])]
    sections = {heading: [] for heading in [*labels, "Autres"]}
    for record in (show(slug, i) for i in kept):
        link = LINK.search(record["text"])
        line = f"- {record['title']}" + (f" : {link.group(0)}" if link else "")
        # Why: a production stands in every section of its labels, and under Autres only without any.
        for heading in [label for label in labels if label in record.get("labels", [])] or ["Autres"]:
            sections[heading].append(line)
    discarded = len(members) - len(kept)
    record = {
        "destination": destination,
        "title": f"{agent['title']}, run du {datetime.now():%d/%m/%Y} : retenus {len(kept)}, écartés {discarded}",
        "text": digest_text({h: rows for h, rows in sections.items() if rows}) or "Aucune production retenue.",
        "run_id": run_id,
        "mode": mode,
        "status": initial_status(mode),
        "productions": kept,
    }
    write_json(f"{slug}/envois/{delivery_id}.json", record)
    if record["status"] == "pending_send":
        record = send(slug, delivery_id, record)
    return log(slug, delivery_id, record)


def approve(slug: str, delivery_id: str, approved_by: str) -> dict:
    """Write a production awaiting review, or retry a failed one; anything else is refused without writing."""
    record = show(slug, delivery_id)
    if record["status"] not in ("pending_review", "failure"):
        raise ValueError(f"envoi {delivery_id} est {record['status']}, attendu pending_review ou failed")
    record["approved_by"] = approved_by
    return log(slug, delivery_id, send(slug, delivery_id, record))


def show(slug: str, delivery_id: str) -> dict:
    known = re.fullmatch(r"[a-z][a-z0-9-]{2,40}", slug) and re.fullmatch(
        r"[0-9a-f-]{36}-(\d+|digest-[a-z0-9_.-]+)", delivery_id
    )
    if not known or (record := read_json(f"{slug}/envois/{delivery_id}.json")) is None:
        raise ValueError(f"envoi {delivery_id} introuvable pour l'agent {slug}")
    return record
