"""Lecture du Backlog unifié pour rédiger un ticket : équipes, épics, tickets proches, auteur."""

import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote

from lib import notion
from web import config

STATUTS_EPIC_INACTIFS = ("Archivé", "𝗘𝗡 𝗣𝗥𝗢𝗗 ce trimestre")
ROLES_PM = {"Responsable d'équipe", "Gestionnaire de produit", "Product Owner", "Produit", "Responsable de Mission"}
ROLES_DESIGN = {"Designer", "Design"}
ROLES_DEV = {"Dev", "Data", "Data analyst"}
MOTS_VIDES = {
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
class Auteur:
    nom: str
    roles: list[str]
    equipes: list[str]
    notion_id: str | None


def requeter(
    base: str, filtre: dict | None = None, tri: list[dict] | None = None, limite: int | None = None
) -> list[dict]:
    """Pages d'une base Notion, filtrées et triées, jusqu'à limite."""
    pages: list[dict] = []
    cursor = None
    while True:
        payload: dict = {"page_size": min(100, limite or 100)}
        if filtre:
            payload["filter"] = filtre
        if tri:
            payload["sorts"] = tri
        if cursor:
            payload["start_cursor"] = cursor
        response = notion.notion_request("POST", f"databases/{base}/query", payload)
        pages.extend(response["results"])
        if limite and len(pages) >= limite:
            return pages[:limite]
        if not response.get("has_more"):
            return pages
        cursor = response["next_cursor"]


def titre(page: dict) -> str:
    """Titre d'une page, sans espaces aux bords."""
    return notion.extract_page_title(page).strip()


def ids_relation(page: dict, propriete: str) -> list[str]:
    """Identifiants des pages liées par une relation."""
    return [r["id"] for r in page["properties"].get(propriete, {}).get("relation", [])]


def bases_liees() -> dict[str, str]:
    """Bases Équipes et Épics, lues dans le schéma du backlog."""
    schema = notion.notion_request("GET", f"databases/{config.NOTION_BACKLOG_DB}")
    return {
        "equipes": schema["properties"]["Pizza team"]["relation"]["database_id"],
        "epics": schema["properties"]["Epic - feuille de route"]["relation"]["database_id"],
    }


def tickets_recents(equipe_id: str, nombre: int) -> list[str]:
    """Titres non vides des tickets non annulés les plus récents d'une équipe."""
    pages = requeter(
        config.NOTION_BACKLOG_DB,
        {
            "and": [
                {"property": "Pizza team", "relation": {"contains": equipe_id}},
                {"property": "Statut", "select": {"does_not_equal": "Annulé"}},
            ]
        },
        [{"timestamp": "created_time", "direction": "descending"}],
        limite=nombre + 5,
    )
    return [t for t in (titre(p) for p in pages) if t][:nombre]


def charger_contexte(par_equipe: int = 15) -> dict:
    """Équipes produit actives, avec leurs épics actifs et leurs titres de tickets récents."""
    bases = bases_liees()
    equipes = requeter(
        bases["equipes"],
        {
            "and": [
                {"property": "Activité", "select": {"equals": "Actif"}},
                {"property": "Type", "select": {"equals": "Équipe produit"}},
            ]
        },
    )
    epics = requeter(
        bases["epics"],
        {"and": [{"property": "Statut", "status": {"does_not_equal": statut}} for statut in STATUTS_EPIC_INACTIFS]},
    )
    return {
        "genere_le": datetime.now(UTC).isoformat(),
        "equipes": [
            {
                "id": equipe["id"],
                "nom": titre(equipe),
                "epics": [
                    {"id": e["id"], "nom": titre(e)} for e in epics if equipe["id"] in ids_relation(e, "Pizza team")
                ],
                "tickets_recents": tickets_recents(equipe["id"], par_equipe),
            }
            for equipe in equipes
        ],
    }


def formater_contexte(contexte: dict) -> str:
    """Le contexte des équipes en Markdown, pour l'agent."""
    lignes = [f"# Équipes produit actives (au {contexte['genere_le'][:10]})", ""]
    for equipe in sorted(contexte["equipes"], key=lambda e: e["nom"]):
        lignes.append(f"## {equipe['nom']}")
        if equipe["epics"]:
            lignes.append("- Épics actifs : " + " ; ".join(e["nom"] for e in equipe["epics"]))
        if equipe["tickets_recents"]:
            lignes.append("- Tickets récents :")
            lignes.extend(f"  - {t}" for t in equipe["tickets_recents"])
        else:
            lignes.append("- Tickets récents : aucun")
        lignes.append("")
    return "\n".join(lignes)


def normaliser(texte: str) -> str:
    """Texte en minuscules, sans accents."""
    return unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode().lower()


def mots_cles(texte: str, maximum: int = 8) -> list[str]:
    """Mots porteurs de sens d'un titre, sans doublon."""
    mots: list[str] = []
    texte = re.sub(r"^\s*\[[^\]]*\]\s*", "", texte)
    for mot in re.findall(r"[^\W\d_][\w-]{3,}", texte):
        if normaliser(mot) not in MOTS_VIDES and normaliser(mot) not in {normaliser(m) for m in mots}:
            mots.append(mot)
    return mots[:maximum]


def chercher_doublons(texte: str, limite: int = 5) -> list[dict]:
    """Tickets non annulés dont le titre partage au moins la moitié des mots-clés de texte (et deux), les plus proches d'abord."""
    mots = mots_cles(texte)
    if len(mots) < 2:
        return []
    pages = requeter(
        config.NOTION_BACKLOG_DB,
        {
            "and": [
                {"property": "Statut", "select": {"does_not_equal": "Annulé"}},
                {"or": [{"property": "Nom", "title": {"contains": mot}} for mot in mots]},
            ]
        },
    )
    cibles = {normaliser(m) for m in mots}
    # Why: avec « deux mots en commun », 66 % des titres du backlog avaient des candidats (mesure du 2026-10-30) ;
    # avec la moitié des mots-clés, 37 %, et rarement plus de cinq.
    seuil = max(2, math.ceil(len(cibles) / 2))
    notes = [(sum(1 for c in cibles if re.search(rf"\b{re.escape(c)}", normaliser(titre(p)))), p) for p in pages]
    notes.sort(key=lambda note: note[0], reverse=True)
    return [
        {
            "titre": titre(p),
            "url": p.get("url", ""),
            "statut": (p["properties"].get("Statut", {}).get("select") or {}).get("name", ""),
            "communs": communs,
        }
        for communs, p in notes[:limite]
        if communs >= seuil
    ]


def utilisateur_notion(email: str) -> tuple[str, str] | None:
    """Identifiant et nom du compte Notion qui porte cet e-mail."""
    cursor = None
    while True:
        suffixe = f"&start_cursor={quote(cursor, safe='')}" if cursor else ""
        response = notion.notion_request("GET", "users?page_size=100" + suffixe)
        for compte in response["results"]:
            if (
                compte.get("type") == "person"
                and (compte.get("person") or {}).get("email", "").lower() == email.lower()
            ):
                return compte["id"], compte.get("name", "")
        if not response.get("has_more"):
            return None
        cursor = response["next_cursor"]


def trouver_auteur(email: str) -> Auteur | None:
    """Rôles et équipes de l'auteur d'après l'Annuaire, et son compte Notion."""
    fiches = requeter(config.NOTION_ANNUAIRE_DB, {"property": "Email", "email": {"equals": email}}, limite=1)
    compte = utilisateur_notion(email)
    if not fiches and not compte:
        return None
    proprietes = notion.extract_page_properties(fiches[0]) if fiches else {}
    return Auteur(
        nom=compte[1] if compte else titre(fiches[0]),
        roles=proprietes.get("Rôle") or [],
        equipes=ids_relation(fiches[0], "🍕 Équipes") if fiches else [],
        notion_id=compte[0] if compte else None,
    )


def champ_auteur(auteur: Auteur, equipes_destinataires: list[str]) -> str:
    """Propriété de personne où inscrire l'auteur, selon son rôle et l'équipe destinataire."""
    roles = set(auteur.roles)
    if roles & ROLES_PM:
        return "POM" if set(auteur.equipes) & set(equipes_destinataires) else "Contributeurs"
    if roles & ROLES_DESIGN:
        return "UX"
    if roles & ROLES_DEV:
        return "Développeurs"
    return "Contributeurs"
