"""Rôle et équipes de la personne connectée, et la propriété où l'inscrire comme auteur."""

import argparse
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import backlog, backlog_stockage  # noqa: E402
from web import config  # noqa: E402


def run(args: argparse.Namespace) -> str:
    if not config.NOTION_BACKLOG_DB:
        return "NOTION_BACKLOG_DB absent : lecture du backlog impossible (variable d'environnement à renseigner)."
    email = config.agent_user_email()
    if not email:
        return "Personne connectée inconnue : l'auteur ne sera pas inscrit."
    auteur = backlog.trouver_auteur(email)
    if auteur is None:
        return "Absent de l'Annuaire et de Notion : l'auteur ne sera pas inscrit."
    equipes = {e["nom"]: e["id"] for e in backlog_stockage.contexte_courant()["equipes"]}
    noms = {i: n for n, i in equipes.items()}
    lignes = [
        f"Auteur : {auteur.nom}",
        f"Rôles : {', '.join(auteur.roles) or 'inconnus (demander son rôle à la personne)'}",
        f"Équipes : {', '.join(noms.get(i, 'équipe inactive') for i in auteur.equipes) or 'aucune'}",
        f"Compte Notion : {'trouvé' if auteur.notion_id else 'introuvable'}",
    ]
    if args.equipe:
        inconnues = [n for n in args.equipe if n not in equipes]
        if inconnues:
            lignes.append(f"Équipe inconnue : {', '.join(inconnues)} (nom exact : voir contexte.py)")
        cibles = [equipes[n] for n in args.equipe if n in equipes]
        lignes.append(f"Inscrit dans : {backlog.champ_auteur(auteur, cibles)}")
    return "\n".join(lignes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--equipe", action="append", default=[], help="nom exact de l'équipe destinataire")
    try:
        print(run(parser.parse_args()))
    except httpx.HTTPStatusError as erreur:
        sys.exit(f"Notion répond {erreur.response.status_code} : {erreur.response.text[:300]}")
    except httpx.TransportError:
        sys.exit("Notion ne répond pas : réessayer dans une minute.")


if __name__ == "__main__":
    main()
