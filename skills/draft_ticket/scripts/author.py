"""Rôle et équipes de la personne connectée, et la propriété où l'inscrire comme auteur."""

import argparse

import httpx

from lib import backlog, backlog_storage
from skills.draft_ticket.scripts.common import check_config, run_cli
from web import config


def run(args: argparse.Namespace) -> str:
    missing = check_config(directory=True)
    if missing:
        return missing
    email = config.agent_user_email()
    if not email:
        return "Personne connectée inconnue : l'auteur ne sera pas inscrit."
    try:
        author = backlog.find_author(email)
    except httpx.HTTPError, RuntimeError:
        return "Auteur non inscrit : annuaire ou comptes Notion illisibles."
    if author is None:
        return "Absent de l'Annuaire et de Notion : l'auteur ne sera pas inscrit."
    teams = {e["name"]: e["id"] for e in backlog_storage.current_context()["teams"]}
    names = {i: n for n, i in teams.items()}
    lines = [
        f"Auteur : {author.name}",
        f"Rôles : {', '.join(author.roles) or 'inconnus (demander son rôle à la personne)'}",
        f"Équipes : {', '.join(names.get(i, 'équipe inactive') for i in author.teams) or 'aucune'}",
        f"Compte Notion : {'trouvé' if author.notion_id else 'introuvable'}",
    ]
    if args.team:
        unknown = [n for n in args.team if n not in teams]
        if unknown:
            lines.append(f"Équipe inconnue : {', '.join(unknown)} (nom exact : voir context.py)")
        targets = [teams[n] for n in args.team if n in teams]
        if author.notion_id:
            lines.append(f"Inscrit dans : {backlog.author_field(author, targets)}")
        else:
            lines.append("Inscrit dans : personne (pas de compte Notion)")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team", action="append", default=[], help="nom exact de l'équipe destinataire")
    run_cli(run, parser)


if __name__ == "__main__":
    main()
