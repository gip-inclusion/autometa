"""Crée le ticket dans le Backlog unifié ; sans --go, montre seulement ce qui serait créé."""

import argparse
import json
import sys
from pathlib import Path

import httpx

from lib import backlog, backlog_creation, backlog_storage, notion
from skills.draft_ticket.scripts.common import check_config, conversation_folder
from web import config

LIST_FIELDS = ("teams", "types")


def check_fields(draft: dict) -> None:
    if not isinstance(draft, dict):
        raise ValueError("Le brouillon doit être un objet JSON")
    for field in ("title", "body", "status", *LIST_FIELDS):
        if not draft.get(field):
            raise ValueError(f"Champ manquant dans le brouillon : {field}")
    for field in LIST_FIELDS:
        if not isinstance(draft[field], list):
            raise ValueError(f"Le champ {field} du brouillon doit être une liste")


def opening(blocks: list[dict]) -> str:
    """Texte brut du premier paragraphe, le marqueur Autometa compris."""
    first = next(b for b in blocks if b["type"] == "paragraph")
    return "".join(
        backlog_creation.MARKER if t["type"] == "mention" else t["text"]["content"]
        for t in first["paragraph"]["rich_text"]
    )


def resolve(draft: dict, context: dict, author: backlog.Author | None) -> backlog_creation.Ticket:
    check_fields(draft)
    teams = {e["name"]: e for e in context["teams"]}
    unknown = [n for n in draft["teams"] if n not in teams]
    if unknown:
        raise ValueError(f"Équipe inconnue : {', '.join(unknown)}")
    ids = [teams[n]["id"] for n in draft["teams"]]
    epic = None
    if draft.get("epic"):
        epics = {e["name"]: e["id"] for n in draft["teams"] for e in teams[n]["epics"]}
        if draft["epic"] not in epics:
            raise ValueError(f"Épic inconnu pour ces équipes : {draft['epic']}")
        epic = epics[draft["epic"]]
    return backlog_creation.Ticket(
        title=draft["title"],
        body=draft["body"],
        teams=ids,
        status=draft["status"],
        types=draft["types"],
        figma=draft.get("figma") or None,
        epic=epic,
        author_field=draft.get("author_field") or (backlog.author_field(author, ids) if author else None),
        author_notion_id=author.notion_id if author else None,
        names={**{teams[n]["id"]: n for n in draft["teams"]}, **({epic: draft["epic"]} if epic else {})},
    )


def run(args: argparse.Namespace) -> str:
    missing = check_config(directory=False)
    if missing:
        raise ValueError(missing)
    path = Path(args.draft) if args.draft else conversation_folder() / "ticket-draft.json"
    draft = json.loads(path.read_text(encoding="utf-8"))
    email = config.agent_user_email()
    author, warnings = None, []
    if email:
        try:
            author = backlog.find_author(email)
        except httpx.HTTPError, notion.NotionRateLimitError:
            warnings.append("Auteur non inscrit : annuaire ou comptes Notion illisibles.")
    ticket = resolve(draft, backlog_storage.current_context(), author)
    if not args.go:
        if not ticket.author_notion_id and not warnings:
            warnings.append("Auteur non inscrit : pas de compte Notion.")
        payload = backlog_creation.prepare(ticket)
        return "\n".join([
            "Vérification seulement (sans --go) : rien n'est créé.",
            json.dumps(payload["properties"], ensure_ascii=False, indent=2),
            "Noms résolus :",
            json.dumps(ticket.names, ensure_ascii=False, indent=2),
            f"Corps : {len(payload['children'])} blocs",
            opening(payload["children"]),
            *warnings,
        ])
    _, url = backlog_creation.create_ticket(ticket)
    path.unlink(missing_ok=True)
    return "\n".join([f"Ticket créé : {url}", *warnings])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", nargs="?", help="fichier JSON du brouillon (défaut : celui de la conversation)")
    parser.add_argument("--go", action="store_true", help="créer vraiment, après l'accord explicite de l'auteur")
    try:
        print(run(parser.parse_args()))
    except (OSError, ValueError) as error:
        sys.exit(f"Refusé, rien n'est créé : {error}")
    except httpx.HTTPStatusError as error:
        if error.response.status_code >= 500:
            sys.exit(
                "Notion ne répond pas correctement : vérifier dans Notion si le ticket existe avant de relancer --go."
            )
        sys.exit(f"Notion répond {error.response.status_code} : {error.response.text[:300]}")
    except httpx.TransportError:
        sys.exit("Notion ne répond pas : vérifier dans Notion si le ticket existe avant de relancer --go.")
    except notion.NotionRateLimitError:
        sys.exit("Notion limite les appels : réessayer dans une minute, après avoir vérifié si le ticket existe.")


if __name__ == "__main__":
    main()
