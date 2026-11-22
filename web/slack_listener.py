"""Écoute Slack en Socket Mode : un lien de conversation collé devient une carte, rafraîchie à la demande."""

import logging
import re
import threading
import time
from urllib.parse import urlsplit

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from sqlalchemy.exc import SQLAlchemyError

from . import config
from .database import store
from .helpers import CONV_ID, to_local, utcnow
from .stores.records import Conversation

logger = logging.getLogger(__name__)

CONVERSATION_PATH = re.compile(rf"/(?:c|explorations)/({CONV_ID.pattern})(?:/.*)?")
REFRESH_ACTION = "refresh_conversation_card"


def conversation_id(url: str) -> str | None:
    """L'identifiant de la conversation qu'adresse `url` sur cette instance, sinon None."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    found = CONVERSATION_PATH.fullmatch(parts.path)
    same_host = parts.netloc and parts.netloc.lower() == urlsplit(config.BASE_URL).netloc.lower()
    return found.group(1) if found and same_host else None


def card(conv: Conversation) -> dict:
    """La carte Slack d'une conversation : titre, état, auteur, dates, bouton d'actualisation."""
    facts = [
        ":hourglass_flowing_sand: En cours" if conv.needs_response else ":white_check_mark: Terminée",
        (conv.user_id or "").split("@")[0],
        f"créée le {local_date(conv.created_at)}",
        f"dernière activité le {local_date(conv.updated_at)}",
    ]
    return {
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{escape(conv.title or 'Conversation sans titre')}*"},
            },
            {"type": "context", "elements": [{"type": "mrkdwn", "text": escape(" · ".join(f for f in facts if f))}]},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "action_id": REFRESH_ACTION,
                        "text": {"type": "plain_text", "text": "Actualiser"},
                    }
                ],
            },
            {"type": "context", "elements": [{"type": "mrkdwn", "text": f"État relevé le {local_date(utcnow())}"}]},
        ]
    }


def local_date(moment) -> str:
    return to_local(moment).strftime("%d/%m/%Y à %H:%M")


def escape(text: str) -> str:
    """Le texte sans les trois caractères que Slack lit comme du balisage."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cards(urls: list[str]) -> dict[str, dict]:
    """La carte de chaque adresse qui mène à une conversation connue de cette instance."""
    found = {}
    for url in urls:
        conv_id = conversation_id(url)
        conv = conv_id and store.get_conversation(conv_id, include_messages=False)
        if conv:
            found[url] = card(conv)
    return found


def handle(client: SocketModeClient, request: SocketModeRequest) -> None:
    """Accuse réception, puis pose ou rafraîchit les cartes des liens que l'événement désigne."""
    client.send_socket_mode_response(SocketModeResponse(envelope_id=request.envelope_id))
    payload = request.payload
    event = payload.get("event", {})
    if request.type == "events_api" and event.get("type") == "link_shared":
        urls = [link["url"] for link in event["links"]]
        # Why: un lien encore dans la zone de saisie n'a ni canal ni message, seuls unfurl_id et source le désignent.
        if event.get("unfurl_id"):
            target = {"unfurl_id": event["unfurl_id"], "source": event["source"]}
        else:
            target = {"channel": event["channel"], "ts": event["message_ts"]}
    elif request.type == "interactive" and any(
        a.get("action_id") == REFRESH_ACTION for a in payload.get("actions", [])
    ):
        container = payload["container"]
        urls = [container["app_unfurl_url"]]
        target = {"channel": container["channel_id"], "ts": container["message_ts"]}
    else:
        return
    try:
        unfurls = cards(urls)
        if unfurls:
            client.web_client.chat_unfurl(**target, unfurls=unfurls)
    except SlackApiError as error:
        logger.warning("Carte Slack refusée : %s", error.response.get("error"))
    except OSError:
        logger.warning("Carte Slack non posée, Slack injoignable", exc_info=True)
    except SQLAlchemyError:
        logger.exception("Carte Slack non posée, conversation illisible")


def connect(client: SocketModeClient) -> None:
    """Première connexion, retentée jusqu'à réussir : le client ne se reconnecte seul qu'après elle."""
    while not client.closed:
        try:
            client.connect()
            return
        except (SlackApiError, OSError) as error:
            logger.warning("Connexion à Slack impossible, nouvel essai dans 30 s : %s", error)
            time.sleep(30)


def start() -> SocketModeClient | None:
    """Ouvre l'écoute si l'instance la demande ; rend le client à fermer à l'arrêt, sinon None."""
    if not config.SLACK_CHAT_LISTEN:
        return None
    if not (config.SLACK_CHAT_BOT_TOKEN and config.SLACK_CHAT_APP_TOKEN and config.BASE_URL):
        logger.warning(
            "SLACK_CHAT_LISTEN sans SLACK_CHAT_BOT_TOKEN, SLACK_CHAT_APP_TOKEN ou BASE_URL : Slack non écouté"
        )
        return None
    client = SocketModeClient(
        app_token=config.SLACK_CHAT_APP_TOKEN, web_client=WebClient(token=config.SLACK_CHAT_BOT_TOKEN, timeout=10)
    )
    client.socket_mode_request_listeners.append(handle)
    threading.Thread(target=connect, args=(client,), daemon=True, name="slack-listener").start()
    return client
