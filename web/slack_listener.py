"""Écoute Slack en Socket Mode : un lien de conversation collé devient une carte, rafraîchie à la demande."""

import http.client
import logging
import re
import threading
import time
from urllib.parse import unquote, urlsplit

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientError
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from sqlalchemy.exc import SQLAlchemyError

from . import config, slack_excerpts
from .database import store
from .helpers import CONV_ID, to_local, utcnow
from .stores.records import Conversation

logger = logging.getLogger(__name__)

CONVERSATION_PATH = re.compile(rf"/(?:c|explorations)/({CONV_ID.pattern})(?:/([0-9]{{1,10}})(?:/([^/]+))?)?(?:/.*)?")
REFRESH_ACTION = "refresh_conversation_card"

refreshed: dict[str, float] = {}


def located(url: str) -> tuple[str, int | None, str | None] | None:
    """La conversation qu'adresse `url` sur cette instance, avec le message et l'élément d'un permalien ; sinon None."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    # Why: comme la route, qui lit le chemin décodé : « %73ection-… » y désigne une section.
    found = CONVERSATION_PATH.fullmatch(unquote(parts.path))
    same_host = parts.netloc and parts.netloc.lower() == urlsplit(config.BASE_URL).netloc.lower()
    if not found or not same_host:
        return None
    conv_id, message, anchor = found.groups()
    return conv_id, message and int(message), anchor


def card(conv: Conversation, excerpt: list[dict] = ()) -> dict:
    """La carte Slack d'une conversation : titre, extrait s'il y en a un, état, auteur, dates, actualisation."""
    facts = [
        "⏳ En cours" if conv.needs_response else "✅ Terminée",
        (conv.user_id or "").split("@")[0],
        f"créée le {local_date(conv.created_at)}",
        f"dernière activité le {local_date(conv.updated_at)}",
        f"état relevé le {local_date(utcnow())}",
    ]
    # Why: tout en plain_text, que Slack affiche tel quel : dans du mrkdwn, un titre ferait vivre @channel et liens.
    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": slack_excerpts.shortened(conv.title or "Conversation sans titre", 150),
                },
            },
            *excerpt,
            {
                "type": "context",
                "elements": [
                    {"type": "plain_text", "text": slack_excerpts.shortened(" · ".join(f for f in facts if f), 300)}
                ],
            },
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
        ]
    }


def local_date(moment) -> str:
    return to_local(moment).strftime("%d/%m/%Y à %H:%M")


def cards(urls: list[str]) -> dict[str, dict]:
    """La carte de chaque adresse qui mène à une conversation connue de cette instance."""
    found = {}
    for url in urls:
        conv_id, message_id, anchor = located(url) or (None, None, None)
        conv = conv_id and store.get_conversation(conv_id, include_messages=False)
        if not conv:
            continue
        try:
            found[url] = card(conv, slack_excerpts.excerpt(conv, message_id, anchor))
        except LookupError, ValueError, TypeError, AttributeError, RecursionError:
            # Why: une réponse que l'extrait ne sait pas lire garde sa carte, et les autres liens du message la leur.
            logger.exception("Extrait Slack impossible pour la conversation %s, carte sans extrait", conv_id)
            found[url] = card(conv)
    return found


def just_refreshed(url: str) -> bool:
    """Vrai si la carte de `url` a été actualisée il y a moins de 5 s ; sinon retient qu'elle l'est maintenant."""
    now = time.monotonic()
    if now - refreshed.get(url, float("-inf")) < 5:
        return True
    if len(refreshed) >= 1000:
        refreshed.clear()
    refreshed[url] = now
    return False


def asked(request: SocketModeRequest) -> tuple[list[str], dict] | None:
    """Les adresses à mettre en carte et ce qui désigne leur message pour Slack, None s'il n'y a rien à faire."""
    payload = request.payload
    if request.type == "events_api" and (payload.get("event") or {}).get("type") == "link_shared":
        event = payload["event"]
        urls = [link.get("url") for link in event.get("links") or []]
        # Why: un lien encore dans la zone de saisie n'a ni canal ni message, seuls unfurl_id et source le désignent.
        if event.get("unfurl_id"):
            target = {"unfurl_id": event["unfurl_id"], "source": event.get("source")}
        else:
            target = {"channel": event.get("channel"), "ts": event.get("message_ts")}
    elif request.type == "interactive" and any(
        a.get("action_id") == REFRESH_ACTION for a in payload.get("actions") or []
    ):
        container = payload.get("container") or {}
        urls = [container.get("app_unfurl_url")]
        target = {"channel": container.get("channel_id"), "ts": container.get("message_ts")}
        if urls[0] and just_refreshed(urls[0]):
            return None
    else:
        return None
    if not urls or not all(urls) or not all(target.values()):
        logger.warning("Événement Slack incomplet, ignoré : %s", request.type)
        return None
    return urls, target


def handle(client: SocketModeClient, request: SocketModeRequest) -> None:
    """Accuse réception, puis pose ou rafraîchit les cartes des liens que l'événement désigne."""
    client.send_socket_mode_response(SocketModeResponse(envelope_id=request.envelope_id))
    found = asked(request)
    if not found:
        return
    urls, target = found
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
        except (SlackClientError, OSError, http.client.HTTPException) as error:
            logger.warning("Connexion à Slack impossible, nouvel essai dans 30 s : %s", error)
            time.sleep(30)
            continue
        # Why: fermé pendant la connexion, le client garderait une session ouverte et sa surveillance.
        if client.closed:
            client.close()
        return


def start() -> SocketModeClient | None:
    """Ouvre l'écoute si l'instance la demande ; rend le client à fermer à l'arrêt, sinon None."""
    if not config.SLACK_CHAT_LISTEN:
        return None
    base = urlsplit(config.BASE_URL)
    # Why: une instance qui écoute sans pouvoir reconnaître ses liens prend des événements destinés à une autre.
    if not (config.SLACK_CHAT_BOT_TOKEN and config.SLACK_CHAT_APP_TOKEN and base.netloc and not base.path):
        logger.warning(
            "SLACK_CHAT_LISTEN sans SLACK_CHAT_BOT_TOKEN, SLACK_CHAT_APP_TOKEN ou BASE_URL "
            "(adresse complète, sans chemin) : Slack non écouté"
        )
        return None
    client = SocketModeClient(
        app_token=config.SLACK_CHAT_APP_TOKEN, web_client=WebClient(token=config.SLACK_CHAT_BOT_TOKEN, timeout=10)
    )
    client.socket_mode_request_listeners.append(handle)
    threading.Thread(target=connect, args=(client,), daemon=True, name="slack-listener").start()
    return client
