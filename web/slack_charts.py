"""Les graphiques d'un extrait Slack : dessinés une fois, déposés comme fichiers de l'application, montrés en image."""

import hashlib
import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientError

from lib import mermaid_png

logger = logging.getLogger(__name__)

# L'identifiant du fichier Slack de chaque graphique déjà déposé, par l'empreinte de son texte.
files: dict[str, str] = {}


def key(source: str) -> str:
    return hashlib.sha256(source.encode()).hexdigest()


def shown(blocks: list[dict], images: bool) -> list[dict]:
    """Les blocs tels que Slack les reçoit : chaque graphique en image si son fichier est déposé, sinon nommé."""
    found = []
    for block in blocks:
        if block["type"] != "chart":
            found.append(block)
        elif images and key(block["source"]) in files:
            found.append({
                "type": "image",
                "slack_file": {"id": files[key(block["source"])]},
                "alt_text": block["title"] or "Graphique",
                **({"title": {"type": "plain_text", "text": block["title"]}} if block["title"] else {}),
            })
        else:
            text = f"Graphique : {block['title']}" if block["title"] else "Graphique"
            found.append({"type": "section", "text": {"type": "plain_text", "text": text, "emoji": False}})
    return found


def deposit(web: WebClient, source: str) -> bool:
    """Dessine un graphique pas encore déposé et le dépose dans Slack ; faux s'il l'était déjà ou si cela échoue."""
    # Why: au-delà, ce n'est plus un graphique lisible, et le navigateur y passerait son temps et sa mémoire.
    if key(source) in files or len(source) > 20_000:
        return False
    png = mermaid_png.render(source)
    if not png:
        return False
    try:
        # Why: sans canal, le fichier reste celui de l'application ; la carte le montre sans qu'il soit publié.
        response = web.files_upload_v2(content=png, filename="graphique.png", title="Graphique")
    except SlackApiError as error:
        logger.warning("Graphique non déposé dans Slack, envoi refusé : %s", error.response.get("error"))
        return False
    except (SlackClientError, OSError) as error:
        logger.warning("Graphique non déposé dans Slack, envoi impossible : %s", error)
        return False
    if len(files) >= 500:
        files.clear()
    files[key(source)] = response["files"][0]["id"]
    return True
