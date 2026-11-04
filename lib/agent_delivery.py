"""Deliver an agent's productions to its Slack and Notion destinations, by mode: shadow, review or real."""

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Optional

import httpx

from lib import agent_config, notion, slack
from web import config, s3

logger = logging.getLogger(__name__)

__all__ = ["deliver", "approve", "show"]

STATUS_BY_MODE = {"ombre": "ombre", "relecture": "a_relire", "reel": "a_envoyer"}
ENVOI_FIELDS = {"destination", "titre", "texte", "cle"}


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


def envoi_errors(index: int, envoi: object, modes: dict[str, str]) -> list[str]:
    path = f"envois[{index}]"
    if not isinstance(envoi, dict) or not {"destination", "titre", "texte"} <= set(envoi) <= ENVOI_FIELDS:
        return [f"{path} : attendu destination, titre, texte et, pour Notion, cle."]
    if envoi["destination"] not in modes:
        return [f"{path} : la destination {envoi['destination']!r} n'est pas un point de contact de l'agent."]
    if not all(isinstance(envoi[k], str) and envoi[k].strip() for k in ("titre", "texte")):
        return [f"{path} : titre et texte doivent être des textes non vides."]
    if "cle" in envoi and not (isinstance(envoi["cle"], str) and re.fullmatch(r"[a-z0-9-]{1,80}", envoi["cle"])):
        return [f"{path} : cle en minuscules, chiffres et tirets, 80 caractères au plus."]
    return []


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
    if agent_config.destinations()[destination_id]["canal"] == "slack":
        if not config.AGENT_SLACK_BOT_TOKEN:
            raise RuntimeError("AGENT_SLACK_BOT_TOKEN absent : le bot Slack des agents n'est pas configuré")
        if not slack.post_message(config.AGENT_SLACK_BOT_TOKEN, target, slack_text(record["titre"], record["texte"])):
            raise RuntimeError("Slack a refusé le message")
        return {}
    page_path = f"{slug}/pages/{destination_id}/{record.get('cle')}.json"
    page = read_json(page_path) if record.get("cle") else None
    if page:
        page = notion.replace_page(target, page["id"], record["titre"], record["texte"])
    else:
        page = notion.create_page(target, record["titre"], record["texte"])
    if record.get("cle"):
        write_json(page_path, page)
    return {"page": page}


def send(slug: str, envoi_id: str, record: dict) -> dict:
    """Write a recorded production, keeping its outcome on the record; a failure is recorded, not raised."""
    try:
        record.update(statut="envoyee", envoye_le=datetime.now().isoformat(timespec="seconds"), **write(slug, record))
    except (RuntimeError, httpx.HTTPError) as exc:
        logger.warning("agent %s envoi %s vers %s en échec : %s", slug, envoi_id, record["destination"], exc)
        record.update(statut="echec", erreur=str(exc))
    write_json(f"{slug}/envois/{envoi_id}.json", record)
    return record


def log(slug: str, envoi_id: str, record: dict) -> dict:
    """Why: productions may carry personal data; logs name the envoi, never its title or text."""
    logger.info(
        "agent %s envoi %s vers %s, mode %s : %s",
        slug,
        envoi_id,
        record["destination"],
        record["mode"],
        record["statut"],
    )
    return {"id": envoi_id, "destination": record["destination"], "mode": record["mode"], "statut": record["statut"]}


def deliver(agent: dict, run_id: str, envois: list) -> list[dict]:
    """Record every production of a run, writing only in real mode; one refused production refuses the whole run."""
    run_id = str(uuid.UUID(run_id))
    if errors := agent_config.validate(agent):
        raise ValueError("configuration d'agent refusée : " + " ; ".join(errors))
    modes = {c["id"]: c["mode"] for c in agent["points_de_contact"]}
    if not isinstance(envois, list):
        raise ValueError("envois : attendu une liste")
    if errors := [e for i, envoi in enumerate(envois) for e in envoi_errors(i, envoi, modes)]:
        raise ValueError("passage refusé, rien n'est écrit : " + " ; ".join(errors))
    slug, summary = agent["slug"], []
    for i, envoi in enumerate(envois):
        envoi_id = f"{run_id}-{i}"
        if (record := read_json(f"{slug}/envois/{envoi_id}.json")) is None:
            mode = modes[envoi["destination"]]
            record = {**envoi, "run_id": run_id, "mode": mode, "statut": STATUS_BY_MODE[mode]}
            write_json(f"{slug}/envois/{envoi_id}.json", record)
            if mode == "reel":
                record = send(slug, envoi_id, record)
        summary.append(log(slug, envoi_id, record))
    return summary


def approve(slug: str, envoi_id: str, approved_by: str) -> dict:
    """Write a production awaiting review, or retry a failed one; anything else is refused without writing."""
    record = show(slug, envoi_id)
    if record["statut"] not in ("a_relire", "echec"):
        raise ValueError(f"envoi {envoi_id} est {record['statut']}, attendu a_relire ou echec")
    record["approuve_par"] = approved_by
    return log(slug, envoi_id, send(slug, envoi_id, record))


def show(slug: str, envoi_id: str) -> dict:
    known = re.fullmatch(r"[a-z][a-z0-9-]{2,40}", slug) and re.fullmatch(r"[0-9a-f-]{36}-\d+", envoi_id)
    if not known or (record := read_json(f"{slug}/envois/{envoi_id}.json")) is None:
        raise ValueError(f"envoi {envoi_id} introuvable pour l'agent {slug}")
    return record
