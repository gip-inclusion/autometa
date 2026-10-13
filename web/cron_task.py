"""Point d'entrée commun des crons système : un `cron.py` déclare sa fonction, le contrat est ici."""

import logging
import sys
from collections.abc import Callable

from . import config
from .log import setup_logging

logger = logging.getLogger(__name__)


def run(task: Callable[[], None]) -> None:
    """Exécute une tâche cron avec les logs du produit, et traduit son échec en code de retour."""
    setup_logging(level=logging.DEBUG if config.DEBUG else logging.INFO)
    try:
        task()
    except Exception:
        # Why: un échec doit ressortir en log structuré et en code de retour, pas en traceback nu
        # — c'est ce que le runner lit pour enregistrer le run, fermer Sentry et alerter une fois.
        logger.exception("cron task failed")
        sys.exit(1)
