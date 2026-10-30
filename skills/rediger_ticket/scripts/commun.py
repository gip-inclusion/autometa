"""Éléments communs aux scripts de rédaction de ticket : configuration et erreurs Notion."""

import argparse
import sys
from collections.abc import Callable

import httpx

from web import config


def verifier_configuration(annuaire: bool = False) -> str | None:
    """Message de la variable d'environnement absente, ou None si tout est renseigné."""
    if not config.NOTION_BACKLOG_DB:
        return "NOTION_BACKLOG_DB absent : lecture du backlog impossible (variable d'environnement à renseigner)."
    if annuaire and not config.NOTION_ANNUAIRE_DB:
        return "NOTION_ANNUAIRE_DB absent : lecture de l'Annuaire impossible (variable d'environnement à renseigner)."
    return None


def lancer(run: Callable[[argparse.Namespace], str], parser: argparse.ArgumentParser) -> None:
    """Affiche le résultat de run, ou sort en une ligne claire si Notion échoue."""
    try:
        print(run(parser.parse_args()))
    except httpx.HTTPStatusError as erreur:
        sys.exit(f"Notion répond {erreur.response.status_code} : {erreur.response.text[:300]}")
    except httpx.TransportError:
        sys.exit("Notion ne répond pas.")
    except RuntimeError:
        sys.exit("Notion limite les appels : réessayer dans une minute.")
