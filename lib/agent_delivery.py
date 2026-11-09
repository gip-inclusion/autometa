"""Deliver an agent's productions to its Slack and Notion destinations, by mode: shadow, review or real."""

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
STATUS_BY_MODE = {"ombre": "ombre", "relecture": "a_relire", "reel": "a_envoyer", "fichier": "a_ranger"}
ENVOI_FIELDS = {"destination", "titre", "texte", "cle"}
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


def envoi_errors(index: int, envoi: object, modes: dict[str, str]) -> list[str]:
    path = f"envois[{index}]"
    if not isinstance(envoi, dict) or not {"destination", "titre", "texte"} <= set(envoi) <= ENVOI_FIELDS:
        return [f"{path} : attendu destination, titre, texte et, pour Notion ou un fichier, cle."]
    if envoi["destination"] not in modes:
        return [
            f"{path} : la destination {envoi['destination']!r} n'est ni un point de contact de l'agent "
            "ni fichier:<nom> d'un de ses fichiers."
        ]
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


def deliver(agent: dict, run_id: str, envois: list, chain: Optional[Callable[[dict], dict]] = None) -> list[dict]:
    """Record every production of a run through its sub-agents, writing only in real mode; failed chains rerun."""
    run_id = str(uuid.UUID(run_id))
    if errors := agent_config.validate(agent):
        raise ValueError("configuration d'agent refusée : " + " ; ".join(errors))
    modes = {c["id"]: c["mode"] for c in agent["points_de_contact"]}
    digests = {c["id"] for c in agent["points_de_contact"] if c.get("regroupement") == "digest"}
    modes.update({f"fichier:{nom}": "fichier" for nom in agent.get("fichiers", [])})
    if not isinstance(envois, list):
        raise ValueError("envois : attendu une liste")
    if errors := [e for i, envoi in enumerate(envois) for e in envoi_errors(i, envoi, modes)]:
        raise ValueError("passage refusé, rien n'est écrit : " + " ; ".join(errors))
    slug, summary = agent["slug"], []
    for i, envoi in enumerate(envois):
        envoi_id, appels = f"{run_id}-{i}", 0
        record = read_json(f"{slug}/envois/{envoi_id}.json")
        if record is None or record["statut"] == "echec_sous_agent":
            mode = modes[envoi["destination"]]
            record = {**envoi, "run_id": run_id, "mode": mode, "statut": STATUS_BY_MODE[mode]}
            if chain:
                trace = chain(envoi)
                appels = trace["appels"]
                record.update(trace["envoi"], sous_agents=trace["etapes"])
                if trace["echec"]:
                    record.update(statut="echec_sous_agent", erreur=trace["echec"])
                elif any(e.get("retenu") is False for e in trace["etapes"]):
                    record["statut"] = "ecarte"
            if envoi["destination"] in digests and record["statut"] not in ("ecarte", "echec_sous_agent"):
                record.update(statut="regroupe", digest=digest_id(run_id, envoi["destination"]))
            write_json(f"{slug}/envois/{envoi_id}.json", record)
            if record["statut"] == "a_envoyer":
                record = send(slug, envoi_id, record)
        summary.append({**log(slug, envoi_id, record), "appels": appels})
    for destination in sorted(digests):
        members = [(item["id"], item["statut"]) for item in summary if item["destination"] == destination]
        # Why: a production whose sub-agents failed is retried at the next delivery; the digest waits for it.
        if members and all(statut != "echec_sous_agent" for _, statut in members):
            summary.append({**deliver_digest(agent, run_id, destination, modes[destination], members), "appels": 0})
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
    slug, envoi_id = agent["slug"], digest_id(run_id, destination)
    if (record := read_json(f"{slug}/envois/{envoi_id}.json")) is not None:
        return log(slug, envoi_id, record)
    kept = [i for i, statut in members if statut == "regroupe"]
    labels = [e["nom"] for o in agent.get("outils_modeles", []) for e in o.get("etiquettes", [])]
    sections = {heading: [] for heading in [*labels, "Autres"]}
    for record in (show(slug, i) for i in kept):
        link = LINK.search(record["texte"])
        line = f"- {record['titre']}" + (f" : {link.group(0)}" if link else "")
        # Why: a production stands in every section of its labels, and under Autres only without any.
        for heading in [label for label in labels if label in record.get("etiquettes", [])] or ["Autres"]:
            sections[heading].append(line)
    ecartes = len(members) - len(kept)
    record = {
        "destination": destination,
        "titre": f"{agent['titre']}, run du {datetime.now():%d/%m/%Y} : retenus {len(kept)}, écartés {ecartes}",
        "texte": digest_text({h: rows for h, rows in sections.items() if rows}) or "Aucune production retenue.",
        "run_id": run_id,
        "mode": mode,
        "statut": STATUS_BY_MODE[mode],
        "productions": kept,
    }
    write_json(f"{slug}/envois/{envoi_id}.json", record)
    if record["statut"] == "a_envoyer":
        record = send(slug, envoi_id, record)
    return log(slug, envoi_id, record)


def approve(slug: str, envoi_id: str, approved_by: str) -> dict:
    """Write a production awaiting review, or retry a failed one; anything else is refused without writing."""
    record = show(slug, envoi_id)
    if record["statut"] not in ("a_relire", "echec"):
        raise ValueError(f"envoi {envoi_id} est {record['statut']}, attendu a_relire ou echec")
    record["approuve_par"] = approved_by
    return log(slug, envoi_id, send(slug, envoi_id, record))


def show(slug: str, envoi_id: str) -> dict:
    known = re.fullmatch(r"[a-z][a-z0-9-]{2,40}", slug) and re.fullmatch(
        r"[0-9a-f-]{36}-(\d+|digest-[a-z0-9_.-]+)", envoi_id
    )
    if not known or (record := read_json(f"{slug}/envois/{envoi_id}.json")) is None:
        raise ValueError(f"envoi {envoi_id} introuvable pour l'agent {slug}")
    return record
