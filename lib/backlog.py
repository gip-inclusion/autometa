"""Lecture du Backlog unifié pour rédiger un ticket : équipes, épics, tickets proches, auteur."""

import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote

from lib import notion
from web import config

INACTIVE_EPIC_STATUSES = ("Archivé", "𝗘𝗡 𝗣𝗥𝗢𝗗 ce trimestre")
PM_ROLES = {"Responsable d'équipe", "Gestionnaire de produit", "Product Owner", "Produit", "Responsable de Mission"}
DESIGN_ROLES = {"Designer", "Design"}
DEV_ROLES = {"Dev", "Data", "Data analyst"}
STOP_WORDS = {
    "pour",
    "dans",
    "avec",
    "sans",
    "quand",
    "plus",
    "moins",
    "leur",
    "leurs",
    "cette",
    "afin",
    "afficher",
    "ajouter",
    "permettre",
    "pouvoir",
    "faire",
    "depuis",
    "apres",
    "avant",
    "entre",
    "tous",
    "toutes",
    "tout",
    "page",
    "ecran",
    "etre",
    "avoir",
    "lors",
    "aussi",
}


@dataclass(frozen=True)
class Author:
    name: str
    roles: list[str]
    teams: list[str]
    notion_id: str | None


def title(page: dict) -> str:
    """Titre d'une page, sans espaces aux bords."""
    return notion.extract_page_title(page).strip()


def relation_ids(page: dict, prop: str) -> list[str]:
    """Identifiants des pages liées par une relation."""
    return [r["id"] for r in page["properties"].get(prop, {}).get("relation", [])]


def linked_databases() -> dict[str, str]:
    """Bases Équipes et Épics, lues dans le schéma du backlog."""
    schema = notion.notion_request("GET", f"databases/{config.NOTION_BACKLOG_DB}")
    return {
        "teams": schema["properties"]["Pizza team"]["relation"]["database_id"],
        "epics": schema["properties"]["Epic - feuille de route"]["relation"]["database_id"],
    }


def recent_titles(team_id: str, count: int) -> list[str]:
    """Titres non vides des tickets non annulés les plus récents d'une équipe."""
    pages = notion.query_database(
        config.NOTION_BACKLOG_DB,
        filter={
            "and": [
                {"property": "Pizza team", "relation": {"contains": team_id}},
                {"property": "Statut", "select": {"does_not_equal": "Annulé"}},
            ]
        },
        sorts=[{"timestamp": "created_time", "direction": "descending"}],
    )
    return [t for t in (title(p) for p in pages) if t][:count]


def load_context(per_team: int = 15) -> dict:
    """Équipes produit actives, avec leurs épics actifs et leurs titres de tickets récents."""
    bases = linked_databases()
    teams = notion.query_database(
        bases["teams"],
        filter={
            "and": [
                {"property": "Activité", "select": {"equals": "Actif"}},
                {"property": "Type", "select": {"equals": "Équipe produit"}},
            ]
        },
    )
    epics = notion.query_database(
        bases["epics"],
        filter={
            "and": [{"property": "Statut", "status": {"does_not_equal": status}} for status in INACTIVE_EPIC_STATUSES]
        },
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "teams": [
            {
                "id": team["id"],
                "name": title(team),
                "epics": [
                    {"id": e["id"], "name": title(e)} for e in epics if team["id"] in relation_ids(e, "Pizza team")
                ],
                "recent_titles": recent_titles(team["id"], per_team),
            }
            for team in teams
        ],
    }


def format_context(context: dict) -> str:
    """Le contexte des équipes en Markdown, pour l'agent."""
    lines = [f"# Équipes produit actives (au {context['generated_at'][:10]})", ""]
    for team in sorted(context["teams"], key=lambda e: e["name"]):
        lines.append(f"## {team['name']}")
        if team["epics"]:
            lines.append("- Épics actifs : " + " ; ".join(e["name"] for e in team["epics"]))
        if team["recent_titles"]:
            lines.append("- Tickets récents :")
            lines.extend(f"  - {t}" for t in team["recent_titles"])
        else:
            lines.append("- Tickets récents : aucun")
        lines.append("")
    return "\n".join(lines)


def normalize(text: str) -> str:
    """Texte en minuscules, sans accents."""
    return unicodedata.normalize("NFKD", text.replace("’", "'")).encode("ascii", "ignore").decode().lower()


def keywords(text: str, maximum: int = 8) -> list[str]:
    """Mots porteurs de sens d'un titre, sans doublon."""
    words: list[str] = []
    text = re.sub(r"^\s*\[[^\]]*\]\s*", "", text)
    for word in re.findall(r"[^\W\d_][\w-]{3,}", text):
        if normalize(word) not in STOP_WORDS and normalize(word) not in {normalize(m) for m in words}:
            words.append(word)
    return words[:maximum]


def find_duplicates(text: str, limit: int = 5) -> list[dict]:
    """Tickets non annulés dont le titre partage au moins la moitié des mots-clés de text (et deux), les plus proches d'abord."""
    words = keywords(text)
    if len(words) < 2:
        return []
    pages = notion.query_database(
        config.NOTION_BACKLOG_DB,
        filter={
            "and": [
                {"property": "Statut", "select": {"does_not_equal": "Annulé"}},
                {"or": [{"property": "Nom", "title": {"contains": word}} for word in words]},
            ]
        },
    )
    targets = {normalize(m) for m in words}
    # Why: seuil mesuré sur le backlog réel, voir la décision 3 de paved-road/rediger-ticket/definition-of-done.md.
    threshold = max(2, math.ceil(len(targets) / 2))
    scores = [(sum(1 for c in targets if re.search(rf"\b{re.escape(c)}", normalize(title(p)))), p) for p in pages]
    scores.sort(key=lambda score: score[0], reverse=True)
    return [
        {
            "title": title(p),
            "url": p.get("url", ""),
            "status": (p["properties"].get("Statut", {}).get("select") or {}).get("name", ""),
            "shared": shared,
        }
        for shared, p in scores[:limit]
        if shared >= threshold
    ]


def notion_user(email: str) -> tuple[str, str] | None:
    """Identifiant et nom du compte Notion qui porte cet e-mail."""
    cursor = None
    while True:
        suffix = f"&start_cursor={quote(cursor, safe='')}" if cursor else ""
        response = notion.notion_request("GET", "users?page_size=100" + suffix)
        for account in response["results"]:
            if (
                account.get("type") == "person"
                and (account.get("person") or {}).get("email", "").lower() == email.lower()
            ):
                return account["id"], account.get("name", "")
        if not response.get("has_more"):
            return None
        cursor = response["next_cursor"]


def find_author(email: str) -> Author | None:
    """Rôles et équipes de l'auteur d'après l'Annuaire, et son compte Notion."""
    records = notion.query_database(
        config.NOTION_ANNUAIRE_DB, filter={"property": "Email", "email": {"equals": email}}
    )[:1]
    account = notion_user(email)
    if not records and not account:
        return None
    props = notion.extract_page_properties(records[0]) if records else {}
    return Author(
        name=account[1] if account else title(records[0]),
        roles=props.get("Rôle") or [],
        teams=relation_ids(records[0], "🍕 Équipes") if records else [],
        notion_id=account[0] if account else None,
    )


def author_field(author: Author, target_teams: list[str]) -> str:
    """Propriété de personne où inscrire l'auteur, selon son rôle et l'équipe destinataire."""
    roles = set(author.roles)
    if roles & PM_ROLES:
        return "POM" if set(author.teams) & set(target_teams) else "Contributeurs"
    if roles & DESIGN_ROLES:
        return "UX"
    if roles & DEV_ROLES:
        return "Développeurs"
    return "Contributeurs"
