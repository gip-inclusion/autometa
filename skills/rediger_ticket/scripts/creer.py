"""Crée le ticket dans le Backlog unifié ; sans --go, montre seulement ce qui serait créé."""

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import backlog, backlog_creation, backlog_stockage  # noqa: E402
from web import config  # noqa: E402

CHAMPS_LISTES = ("equipes", "types")
CHAMPS_TEXTES = ("titre", "corps", "statut")


def chemin_brouillon() -> Path:
    return Path("/tmp/rediger_ticket") / (config.agent_conversation_id() or "local") / "brouillon.json"


def verifier_champs(brouillon: dict) -> None:
    for champ in (*CHAMPS_TEXTES, *CHAMPS_LISTES):
        if not brouillon.get(champ):
            raise ValueError(f"Champ manquant dans le brouillon : {champ}")
    for champ in CHAMPS_LISTES:
        if not isinstance(brouillon[champ], list):
            raise ValueError(f"Le champ {champ} du brouillon doit être une liste")


def resoudre(brouillon: dict, contexte: dict, auteur: backlog.Auteur | None) -> backlog_creation.Ticket:
    verifier_champs(brouillon)
    equipes = {e["nom"]: e for e in contexte["equipes"]}
    inconnues = [n for n in brouillon["equipes"] if n not in equipes]
    if inconnues:
        raise ValueError(f"Équipe inconnue : {', '.join(inconnues)}")
    ids = [equipes[n]["id"] for n in brouillon["equipes"]]
    epic = None
    if brouillon.get("epic"):
        epics = {e["nom"]: e["id"] for n in brouillon["equipes"] for e in equipes[n]["epics"]}
        if brouillon["epic"] not in epics:
            raise ValueError(f"Épic inconnu pour ces équipes : {brouillon['epic']}")
        epic = epics[brouillon["epic"]]
    return backlog_creation.Ticket(
        titre=brouillon["titre"],
        corps=brouillon["corps"],
        equipes=ids,
        statut=brouillon["statut"],
        types=brouillon["types"],
        figma=brouillon.get("figma") or None,
        epic=epic,
        champ_auteur=brouillon.get("champ_auteur") or (backlog.champ_auteur(auteur, ids) if auteur else None),
        auteur_notion_id=auteur.notion_id if auteur else None,
        noms={**{equipes[n]["id"]: n for n in brouillon["equipes"]}, **({epic: brouillon["epic"]} if epic else {})},
    )


def run(args: argparse.Namespace) -> str:
    if not config.NOTION_BACKLOG_DB:
        raise ValueError("NOTION_BACKLOG_DB absent : variable d'environnement à renseigner")
    chemin = Path(args.brouillon) if args.brouillon else chemin_brouillon()
    brouillon = json.loads(chemin.read_text(encoding="utf-8"))
    email = config.agent_user_email()
    auteur, avis = None, []
    if email:
        try:
            auteur = backlog.trouver_auteur(email)
        except httpx.HTTPError:
            avis.append("Auteur non inscrit : annuaire ou comptes Notion illisibles.")
    ticket = resoudre(brouillon, backlog_stockage.contexte_courant(), auteur)
    if not args.go:
        backlog_creation.verifier_corps(ticket)
        proprietes = backlog_creation.construire_proprietes(ticket)
        backlog_creation.verifier_relations(ticket)
        return "\n".join([
            "Vérification seulement (sans --go) : rien n'est créé.",
            json.dumps(proprietes, ensure_ascii=False, indent=2),
            json.dumps(ticket.noms, ensure_ascii=False, indent=2),
            *avis,
        ])
    _, url = backlog_creation.creer_ticket(ticket)
    chemin.unlink()
    return "\n".join([f"Ticket créé : {url}", *avis])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brouillon", nargs="?", help="fichier JSON du brouillon (défaut : celui de la conversation)")
    parser.add_argument("--go", action="store_true", help="créer vraiment, après l'accord explicite de l'auteur")
    try:
        print(run(parser.parse_args()))
    except (OSError, json.JSONDecodeError, ValueError) as erreur:
        sys.exit(f"Refusé, rien n'est créé : {erreur}")
    except httpx.HTTPStatusError as erreur:
        sys.exit(f"Notion répond {erreur.response.status_code} : {erreur.response.text[:300]}")
    except httpx.TransportError:
        sys.exit("Notion ne répond pas : vérifier dans Notion si le ticket existe avant de relancer --go.")


if __name__ == "__main__":
    main()
