"""Création d'un ticket dans le Backlog unifié, après accord de l'auteur."""

import logging
from dataclasses import dataclass, field

from lib import backlog, notion
from web import config

logger = logging.getLogger(__name__)

MARQUEUR = ":autometa:"
NOM_EMOJI = "autometa"
# Why: Priorité, Période, Estimation et les statuts d'avancement de dev sont des décisions d'équipe.
STATUTS_PROPOSABLES = (
    "Bac à sable 🏝️",
    "stand-by",
    "𝗨𝗫 À faire",
    "Métier",
    "Cadrage",
    "𝗨𝗫/𝗗𝗘𝗩 Conception",
    "𝗨𝗫 Test utilisateur",
    "𝗨𝗫 À valider",
    "𝗗𝗘𝗩 Prêt à développer",
)
TYPES = ("Fonctionnalité", "Bug", "Sécurité", "Technique", "Tâche")
CHAMPS_AUTEUR = ("POM", "UX", "Développeurs", "Contributeurs")


@dataclass(frozen=True)
class Ticket:
    titre: str
    corps: str
    equipes: list[str]
    statut: str
    types: list[str]
    figma: str | None = None
    epic: str | None = None
    champ_auteur: str | None = None
    auteur_notion_id: str | None = None
    noms: dict[str, str] = field(default_factory=dict)


def construire_proprietes(ticket: Ticket) -> dict:
    """Propriétés Notion du ticket, limitées à celles que l'auteur peut poser."""
    if ticket.statut not in STATUTS_PROPOSABLES:
        raise ValueError(f"Statut non proposable : {ticket.statut}")
    if not ticket.types or not set(ticket.types) <= set(TYPES):
        raise ValueError(f"Type inconnu : {ticket.types}")
    if not ticket.equipes:
        raise ValueError("Au moins une équipe est requise")
    proprietes = {
        "Nom": {"title": [{"text": {"content": ticket.titre[:2000]}}]},
        "Pizza team": {"relation": [{"id": e} for e in ticket.equipes]},
        "Statut": {"select": {"name": ticket.statut}},
        "Type": {"multi_select": [{"name": t} for t in ticket.types]},
    }
    if ticket.figma:
        proprietes["Figma"] = {"url": ticket.figma}
    if ticket.epic:
        proprietes["Epic - feuille de route"] = {"relation": [{"id": ticket.epic}]}
    if ticket.champ_auteur and ticket.auteur_notion_id:
        if ticket.champ_auteur not in CHAMPS_AUTEUR:
            raise ValueError(f"Champ d'auteur inconnu : {ticket.champ_auteur}")
        proprietes[ticket.champ_auteur] = {"people": [{"id": ticket.auteur_notion_id}]}
    return proprietes


def emoji_autometa() -> str | None:
    """Identifiant de l'emoji personnalisé de l'espace, s'il existe."""
    curseur = None
    while True:
        reponse = notion.notion_request(
            "GET", "custom_emojis?page_size=100" + (f"&start_cursor={curseur}" if curseur else "")
        )
        for emoji in reponse.get("results", []):
            if emoji.get("name") == NOM_EMOJI:
                return emoji["id"]
        if not reponse.get("has_more"):
            return None
        curseur = reponse["next_cursor"]


def placer_marqueur(blocs: list[dict], emoji_id: str | None) -> list[dict]:
    """Remplace le marqueur en tête du premier paragraphe par l'emoji de l'espace."""
    premier = next((b for b in blocs if b.get("type") == "paragraph"), None)
    if not premier or not emoji_id:
        return blocs
    textes = premier["paragraph"]["rich_text"]
    contenu = textes[0].get("text", {}).get("content", "") if textes else ""
    if not contenu.startswith(MARQUEUR):
        return blocs
    textes[0]["text"]["content"] = contenu[len(MARQUEUR) :]
    textes.insert(0, {"type": "mention", "mention": {"type": "custom_emoji", "custom_emoji": {"id": emoji_id}}})
    return blocs


def verifier_relations(ticket: Ticket) -> None:
    """Vérifie dans Notion que chaque équipe et l'épic du ticket sont la page attendue, active, dans la bonne base."""
    # Why: les identifiants viennent d'un contexte rangé hors de Notion ; on ne les écrit qu'après vérification.
    bases = backlog.bases_liees()
    attendues = [(equipe, bases["equipes"]) for equipe in ticket.equipes]
    if ticket.epic:
        attendues.append((ticket.epic, bases["epics"]))
    for page_id, base in attendues:
        page = notion.notion_request("GET", f"pages/{page_id}")
        parent = (page.get("parent") or {}).get("database_id", "")
        if parent.replace("-", "") != base.replace("-", "") or page.get("archived") or page.get("in_trash"):
            raise ValueError(f"Relation refusée : {page_id} n'est pas une page active de la base attendue")
        if page_id in ticket.noms and backlog.titre(page) != ticket.noms[page_id]:
            raise ValueError(f"Relation refusée : {page_id} ne s'appelle pas « {ticket.noms[page_id]} »")


def creer_ticket(ticket: Ticket) -> tuple[str, str]:
    """Crée la page du ticket, après vérification de ses relations, et renvoie son identifiant et son URL."""
    verifier_relations(ticket)
    blocs = placer_marqueur(notion.markdown_to_blocks(ticket.corps), emoji_autometa())
    page = notion.notion_request(
        "POST",
        "pages",
        {
            "parent": {"database_id": config.NOTION_BACKLOG_DB},
            "properties": construire_proprietes(ticket),
            "children": blocs[:100],
        },
    )
    for debut in range(100, len(blocs), 100):
        notion.notion_request("PATCH", f"blocks/{page['id']}/children", {"children": blocs[debut : debut + 100]})
    logger.info("Ticket créé dans le backlog : %s", page["id"])
    return page["id"], page["url"]
