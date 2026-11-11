"""Éléments communs aux scripts de rédaction de ticket : configuration et erreurs Notion."""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import httpx

from lib import notion
from web import config


def check_config(directory: bool = False) -> str | None:
    """Message de la variable d'environnement absente, ou None si tout est renseigné."""
    if not config.NOTION_BACKLOG_DB:
        return "NOTION_BACKLOG_DB absent : lecture du backlog impossible (variable d'environnement à renseigner)."
    if directory and not config.NOTION_ANNUAIRE_DB:
        return "NOTION_ANNUAIRE_DB absent : lecture de l'Annuaire impossible (variable d'environnement à renseigner)."
    return None


def conversation_folder() -> Path:
    """Dossier de travail de la conversation, sous /tmp."""
    conversation = config.agent_conversation_id()
    if not conversation:
        raise ValueError("AUTOMETA_CONVERSATION_ID absent : dossier de la conversation inconnu")
    return Path("/tmp") / conversation


def run_cli(run: Callable[[argparse.Namespace], str], parser: argparse.ArgumentParser) -> None:
    """Affiche le résultat de run, ou sort en une ligne claire si Notion échoue."""
    try:
        print(run(parser.parse_args()))
    except httpx.HTTPStatusError as error:
        sys.exit(f"Notion répond {error.response.status_code} : {error.response.text[:300]}")
    except httpx.TransportError:
        sys.exit("Notion ne répond pas.")
    except notion.NotionRateLimitError:
        sys.exit("Notion limite les appels : réessayer dans une minute.")
