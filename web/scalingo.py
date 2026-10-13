"""Client Scalingo — juste assez pour lancer un conteneur one-off."""

import logging

import httpx

from web import config

logger = logging.getLogger(__name__)

TOKEN_EXCHANGE_URL = "https://auth.scalingo.com/v1/tokens/exchange"


class ScalingoError(RuntimeError):
    """L'API Scalingo a refusé ou n'a pas répondu."""


def is_configured() -> bool:
    return bool(config.SCALINGO_API_TOKEN and config.SCALINGO_APP_NAME)


def start_one_off(command: str) -> str:
    """Lance `command` dans un conteneur éphémère et renvoie son identifiant."""
    try:
        exchange = httpx.post(TOKEN_EXCHANGE_URL, auth=("", config.SCALINGO_API_TOKEN), timeout=10)
        exchange.raise_for_status()
        # Why: le nom `token` est dans la liste de l'EventScrubber de Sentry — sous un autre
        # nom, le bearer remonterait en clair dans les locals d'une exception imprévue.
        token = exchange.json()["token"]
        run = httpx.post(
            f"{config.SCALINGO_API_URL}/v1/apps/{config.SCALINGO_APP_NAME}/run",
            headers={"Authorization": f"Bearer {token}"},
            json={"command": command, "detached": True},
            timeout=20,
        )
        run.raise_for_status()
        return run.json()["container"]["id"]
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as e:
        logger.warning("lancement du conteneur Scalingo refusé : %s", e)
        raise ScalingoError(f"lancement du conteneur refusé : {e}") from e
