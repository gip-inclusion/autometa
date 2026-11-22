"""Les icônes des Work Objects de Slack : une image du dépôt par genre d'objet, déposée une fois comme fichier de l'application."""

import hashlib
import logging
from pathlib import Path

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientError

logger = logging.getLogger(__name__)

# Une image par genre d'objet : conversation.png, dashboard.png, public_dashboard.png. Sans elle, Slack met celle de
# l'application.
ICONS = Path(__file__).parent / "static" / "img" / "slack"
# L'identifiant du fichier Slack de chaque icône déjà déposée, par l'empreinte de son contenu.
files: dict[str, str] = {}


def with_icon(web: WebClient, entity: dict) -> dict:
    """L'objet avec l'icône de son genre, si le dépôt en a une et que Slack l'a déjà reçue ; sinon tel quel."""
    kind = entity["external_ref"]["type"]
    path = ICONS / f"{kind}.png"
    if not path.is_file():
        return entity
    content = path.read_bytes()
    key = hashlib.sha256(content).hexdigest()
    if key not in files:
        try:
            # Why: Autometa est derrière une authentification, Slack ne peut pas y lire une image ; sans canal, le
            # fichier reste celui de l'application.
            files[key] = web.files_upload_v2(content=content, filename=path.name, title="Icône")["files"][0]["id"]
        except SlackApiError as error:
            logger.warning("Icône Slack %s non déposée, envoi refusé : %s", kind, error.response.get("error"))
        except (SlackClientError, OSError) as error:
            logger.warning("Icône Slack %s non déposée, envoi impossible : %s", kind, error)
        # Why: Slack refuse quelques secondes un fichier qu'il vient de recevoir ; l'icône sert à partir de l'objet suivant.
        return entity
    labels = {
        "conversation": "Conversation",
        "dashboard": "Tableau de bord",
        "public_dashboard": "Tableau de bord public",
    }
    icon = {"alt_text": labels.get(kind, "Autometa"), "slack_file": {"id": files[key]}}
    payload = entity["entity_payload"]
    return entity | {"entity_payload": payload | {"attributes": payload["attributes"] | {"product_icon": icon}}}
