"""Crée le ticket dans le Backlog unifié ; sans --go, montre seulement ce qui serait créé."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import backlog, backlog_creation, backlog_stockage  # noqa: E402
from web import config  # noqa: E402


def resoudre(brouillon: dict, contexte: dict, auteur: backlog.Auteur | None) -> backlog_creation.Ticket:
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
    brouillon = json.loads(Path(args.brouillon).read_text())
    email = config.agent_user_email()
    ticket = resoudre(brouillon, backlog_stockage.contexte_courant(), backlog.trouver_auteur(email) if email else None)
    backlog_creation.verifier_corps(ticket)
    proprietes = backlog_creation.construire_proprietes(ticket)
    if not args.go:
        backlog_creation.verifier_relations(ticket)
        return "Vérification seulement (sans --go) : rien n'est créé.\n" + json.dumps(
            proprietes, ensure_ascii=False, indent=2
        )
    _, url = backlog_creation.creer_ticket(ticket)
    return f"Ticket créé : {url}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brouillon", help="fichier JSON du brouillon validé par l'auteur")
    parser.add_argument("--go", action="store_true", help="créer vraiment, après l'accord explicite de l'auteur")
    print(run(parser.parse_args()))


if __name__ == "__main__":
    main()
