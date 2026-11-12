"""Création d'un ticket dans le Backlog unifié, après accord de l'auteur."""

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from lib import backlog, figma, notion
from web import config

logger = logging.getLogger(__name__)

MARKER = ":autometa:"
MAX_TEXT_LENGTH = 2000
MAX_BLOCKS = 100


@dataclass(frozen=True)
class Ticket:
    title: str
    body: str
    teams: list[str]
    status: str
    types: list[str]
    figma: str | None = None
    epic: str | None = None
    author_field: str | None = None
    author_notion_id: str | None = None
    names: dict[str, str] = field(default_factory=dict)


def build_properties(ticket: Ticket, schema: dict) -> dict:
    """Propriétés Notion du ticket, limitées à celles que l'auteur peut poser et aux options du schéma."""
    # Why: Notion crée en silence une option de select inconnue, par exemple un statut renommé depuis.
    allowed = [s for s in schema["statuses"] if s in backlog.ALLOWED_STATUSES]
    if ticket.status not in allowed:
        raise ValueError(f"Statut non proposable : {ticket.status}. Valeurs : {', '.join(allowed)}")
    if not ticket.types or not set(ticket.types) <= set(schema["types"]):
        raise ValueError(f"Type inconnu : {ticket.types}. Valeurs : {', '.join(schema['types'])}")
    if not ticket.teams:
        raise ValueError("Au moins une équipe est requise")
    props = {
        "Nom": {"title": [{"text": {"content": ticket.title}}]},
        "Pizza team": {"relation": [{"id": e} for e in ticket.teams]},
        "Statut": {"select": {"name": ticket.status}},
        "Type": {"multi_select": [{"name": t} for t in ticket.types]},
    }
    if ticket.figma:
        props["Figma"] = {"url": ticket.figma}
    if ticket.epic:
        props["Epic - feuille de route"] = {"relation": [{"id": ticket.epic}]}
    if ticket.author_field and ticket.author_field not in ("POM", "UX", "Développeurs", "Contributeurs"):
        raise ValueError(f"Champ d'auteur inconnu : {ticket.author_field}")
    if ticket.author_field and ticket.author_notion_id:
        props[ticket.author_field] = {"people": [{"id": ticket.author_notion_id}]}
    return props


def check_body(ticket: Ticket) -> None:
    """Refuse un corps que Notion tronquerait ou n'accepterait pas, un lien non http(s) ou un lien Figma invalide."""
    if len(ticket.title) >= MAX_TEXT_LENGTH:
        raise ValueError(f"Titre refusé : {MAX_TEXT_LENGTH} caractères ou plus")
    first_line = next((row for row in ticket.body.splitlines() if row.strip()), "")
    if first_line.startswith("# "):
        raise ValueError("Corps refusé : le titre ne va pas dans le corps")
    blocks = notion.markdown_to_blocks(ticket.body)
    # Why: au-delà de 100 blocs il faudrait un second appel, et un échec laisserait un ticket écrit à moitié ;
    # le marqueur peut ajouter un paragraphe.
    if len(blocks) >= MAX_BLOCKS:
        raise ValueError(f"Ticket trop long : {len(blocks)} blocs, {MAX_BLOCKS - 1} au plus")
    chunks = [c for b in blocks for c in b[b["type"]].get("rich_text", [])]
    chunks += [
        c
        for b in blocks
        if b["type"] == "table"
        for row in b["table"]["children"]
        for cell in row["table_row"]["cells"]
        for c in cell
    ]
    if any(len(c.get("text", {}).get("content", "")) >= MAX_TEXT_LENGTH for c in chunks):
        raise ValueError(
            f"Corps refusé : paragraphe, cellule ou bloc de code de {MAX_TEXT_LENGTH} caractères ou plus, "
            "le découper avec des lignes vides"
        )
    for url in re.findall(r"\]\(([^)]+)\)", ticket.body):
        if not url.strip().startswith(("http://", "https://")):
            raise ValueError(f"Lien refusé : {url}")
    if ticket.figma and not figma.parse_link(ticket.figma):
        raise ValueError(f"Ce n'est pas un lien Figma : {ticket.figma}")


def autometa_emoji() -> str | None:
    """Identifiant de l'emoji personnalisé de l'espace, s'il existe."""
    results = notion.notion_request("GET", "custom_emojis?name=autometa").get("results", [])
    return next((e["id"] for e in results if e.get("name") == "autometa"), None)


def place_marker(blocks: list[dict], emoji_id: str | None) -> list[dict]:
    """Place le marqueur Autometa en tête du premier paragraphe : emoji de l'espace, sinon texte."""
    marker = (
        {"type": "mention", "mention": {"type": "custom_emoji", "custom_emoji": {"id": emoji_id}}}
        if emoji_id
        else {"type": "text", "text": {"content": MARKER}}
    )
    space = {"type": "text", "text": {"content": " "}}
    # Why: le marqueur ouvre le ticket ; un paragraphe plus loin (« Version A » sous Attendu) ne doit pas le porter.
    index = 1 if blocks and blocks[0].get("type") in ("heading_1", "heading_2", "heading_3") else 0
    first = blocks[index] if index < len(blocks) and blocks[index].get("type") == "paragraph" else None
    if first is None:
        blocks.insert(0, {"type": "paragraph", "paragraph": {"rich_text": [marker]}})
        return blocks
    texts = first["paragraph"]["rich_text"]
    if texts and texts[0].get("text", {}).get("content", "").lstrip().startswith(MARKER):
        rest = texts[0]["text"]["content"].lstrip()[len(MARKER) :].lstrip()
        if rest:
            texts[0]["text"]["content"] = rest
        else:
            texts.pop(0)
    texts[:0] = [marker, space] if texts else [marker]
    return blocks


def check_relations(ticket: Ticket, schema: dict) -> None:
    """Vérifie dans Notion que chaque équipe est une équipe produit active, et l'épic un épic actif de l'une d'elles."""
    # Why: les identifiants viennent d'un contexte rangé hors de Notion ; on ne les écrit qu'après vérification.
    expected = [(ticket.teams, backlog.active_teams(schema["teams"]), "une équipe produit active")]
    if ticket.epic:
        expected.append(([ticket.epic], backlog.active_epics(schema["epics"]), "un épic actif"))
    for ids, pages, kind in expected:
        by_id = {page["id"]: page for page in pages}
        for page_id in ids:
            if page_id not in by_id:
                raise ValueError(f"Relation refusée : {page_id} n'est pas {kind}")
            name = ticket.names.get(page_id)
            if name is None:
                raise ValueError(f"Relation refusée : {page_id} : nom non fourni")
            if backlog.title(by_id[page_id]) != name:
                raise ValueError(f"Relation refusée : {page_id} ne s'appelle pas « {name} »")
            if page_id == ticket.epic and not set(backlog.relation_ids(by_id[page_id], "Pizza team")) & set(
                ticket.teams
            ):
                raise ValueError("Relation refusée : l'épic n'appartient à aucune des équipes choisies")


def prepare(ticket: Ticket) -> dict:
    """Vérifie le ticket et renvoie le payload exact de la création, sans rien écrire."""
    check_body(ticket)
    schema = backlog.backlog_schema()
    props = build_properties(ticket, schema)
    check_relations(ticket, schema)
    # Why: un nouvel essai après un délai dépassé ou une demande de correction ne doit pas créer un doublon.
    since = (datetime.now(UTC) - timedelta(minutes=10)).isoformat(timespec="seconds")
    existing = notion.query_database(
        config.NOTION_BACKLOG_DB,
        filter={
            "and": [
                {"property": "Nom", "title": {"equals": ticket.title}},
                {"property": "Statut", "select": {"does_not_equal": "Annulé"}},
                {"timestamp": "created_time", "created_time": {"on_or_after": since}},
            ]
        },
    )
    if existing:
        raise ValueError(
            f"Un ticket au même titre vient d'être créé : {existing[0].get('url', '')}. "
            "Corriger dans Notion plutôt que relancer --go."
        )
    blocks = place_marker(notion.markdown_to_blocks(ticket.body), autometa_emoji())
    return {"parent": {"database_id": config.NOTION_BACKLOG_DB}, "properties": props, "children": blocks}


def create_ticket(ticket: Ticket) -> tuple[str, str]:
    """Crée la page du ticket, après vérification de ses champs et relations, et renvoie son identifiant et son URL."""
    payload = prepare(ticket)
    page = notion.notion_request("POST", "pages", payload)
    logger.info("Ticket créé dans le backlog : %s", page["id"])
    return page["id"], page["url"]
