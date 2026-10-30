"""Création d'un ticket dans le Backlog unifié, après accord de l'auteur."""

import logging
import re
from dataclasses import dataclass, field

from lib import backlog, figma, notion
from web import config

logger = logging.getLogger(__name__)

MARQUEUR = ":autometa:"
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
LIGNE_MAX = 2000
BLOCS_MAX = 100
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


def verifier_corps(ticket: Ticket) -> None:
    """Refuse les lignes que Notion tronquerait, les liens non http(s) et les liens Figma invalides."""
    if any(len(ligne) >= LIGNE_MAX for ligne in ticket.corps.splitlines()):
        raise ValueError("Corps refusé : ligne de plus de 2000 caractères : la découper")
    for url in re.findall(r"\]\(([^)\s]+)\)", ticket.corps):
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"Lien refusé : {url}")
    if ticket.figma and figma.analyser_lien(ticket.figma) is None:
        raise ValueError(f"Ce n'est pas un lien Figma : {ticket.figma}")


def emoji_autometa() -> str | None:
    """Identifiant de l'emoji personnalisé de l'espace, s'il existe."""
    resultats = notion.notion_request("GET", "custom_emojis?name=autometa").get("results", [])
    return resultats[0]["id"] if resultats else None


def placer_marqueur(blocs: list[dict], emoji_id: str | None) -> list[dict]:
    """Place le marqueur Autometa en tête du premier paragraphe : emoji de l'espace, sinon texte."""
    marqueur = (
        {"type": "mention", "mention": {"type": "custom_emoji", "custom_emoji": {"id": emoji_id}}}
        if emoji_id
        else {"type": "text", "text": {"content": MARQUEUR + " "}}
    )
    premier = next((b for b in blocs if b.get("type") == "paragraph"), None)
    if premier is None:
        blocs.insert(0, {"type": "paragraph", "paragraph": {"rich_text": [marqueur]}})
        return blocs
    textes = premier["paragraph"]["rich_text"]
    if textes and textes[0].get("text", {}).get("content", "").startswith(MARQUEUR):
        textes[0]["text"]["content"] = textes[0]["text"]["content"][len(MARQUEUR) :]
    textes.insert(0, marqueur)
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
        if backlog.titre(page) != ticket.noms.get(page_id):
            raise ValueError(f"Relation refusée : {page_id} ne s'appelle pas « {ticket.noms.get(page_id)} »")
        if page_id == ticket.epic and not set(backlog.ids_relation(page, "Pizza team")) & set(ticket.equipes):
            raise ValueError("Relation refusée : l'épic n'appartient à aucune des équipes choisies")


def creer_ticket(ticket: Ticket) -> tuple[str, str]:
    """Crée la page du ticket, après vérification de ses champs et relations, et renvoie son identifiant et son URL."""
    verifier_corps(ticket)
    proprietes = construire_proprietes(ticket)
    verifier_relations(ticket)
    blocs = placer_marqueur(notion.markdown_to_blocks(ticket.corps), emoji_autometa())
    # Why: au-delà de 100 blocs il faudrait un second appel, et un échec laisserait un ticket écrit à moitié.
    if len(blocs) > BLOCS_MAX:
        raise ValueError(f"Ticket trop long : {len(blocs)} blocs, {BLOCS_MAX} au plus")
    page = notion.notion_request(
        "POST",
        "pages",
        {"parent": {"database_id": config.NOTION_BACKLOG_DB}, "properties": proprietes, "children": blocs},
    )
    logger.info("Ticket créé dans le backlog : %s", page["id"])
    return page["id"], page["url"]
