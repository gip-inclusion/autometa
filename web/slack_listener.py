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

from . import config, slack_charts, slack_excerpts
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


def bold(title: str) -> str:
    """Un titre en gras pour Slack, où rien n'est lu : balises échappées, marques de mise en forme retirées."""
    inert = re.sub(r"[*~`]", "", slack_excerpts.shortened(title, 150)).replace("_", " ")
    return f"*{slack_excerpts.code_safe(' '.join(inert.split())) or 'Conversation sans titre'}*"


def facts(conv: Conversation) -> str:
    """Ce que la carte dit d'une conversation sous son titre : en cours s'il y a lieu, son auteur, ses dates."""
    created, active = (to_local(moment).strftime("%d/%m/%Y") for moment in (conv.created_at, conv.updated_at))
    found = [
        f"En cours à {to_local(utcnow()).strftime('%H:%M')}" if conv.needs_response else "",
        (conv.user_id or "").split("@")[0],
        created if created == active else f"créée le {created} · dernière activité le {active}",
    ]
    return slack_excerpts.shortened(" · ".join(fact for fact in found if fact), 300)


def card(conv: Conversation, excerpt: list[dict] = ()) -> dict:
    """La carte Slack d'une conversation : titre, extrait s'il y en a un, auteur et dates, actualisation."""
    return {
        "blocks": [
            # Why: verbatim, Slack ne lit ni @channel ni adresse dans un titre que l'agent a écrit.
            {"type": "section", "text": {"type": "mrkdwn", "verbatim": True, "text": bold(conv.title or "")}},
            *excerpt,
            {"type": "context", "elements": [{"type": "plain_text", "text": facts(conv)}]},
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


def post(web: WebClient, target: dict, found: dict[str, dict]) -> None:
    """Pose les cartes, puis dessine et dépose leurs graphiques encore inconnus de Slack et les repose avec l'image."""

    def drawn(images: bool) -> dict[str, dict]:
        return {url: {"blocks": slack_charts.shown(card["blocks"], images)} for url, card in found.items()}

    try:
        web.chat_unfurl(**target, unfurls=drawn(True))
    except SlackApiError as error:
        if drawn(True) == drawn(False):
            raise
        logger.warning(
            "Carte Slack refusée avec son image, posée sans elle : %s %s",
            error.response.get("error"),
            error.response.get("response_metadata"),
        )
        web.chat_unfurl(**target, unfurls=drawn(False))
    logger.info("Cartes Slack posées : %s", [[block["type"] for block in card["blocks"]] for card in found.values()])
    if not config.SLACK_CHART_IMAGES:
        return
    charts = [block["source"] for card in found.values() for block in card["blocks"] if block["type"] == "chart"]
    if not any([slack_charts.deposit(web, source) for source in charts]):
        return
    # Why: Slack traite un fichier déposé après coup ; la carte est déjà là, l'image la rejoint dès qu'il l'accepte.
    for wait in (1, 2, 4):
        time.sleep(wait)
        try:
            web.chat_unfurl(**target, unfurls=drawn(True))
            return
        except SlackApiError as error:
            logger.warning(
                "Carte Slack refusée avec son image %s s après le dépôt : %s %s",
                wait,
                error.response.get("error"),
                error.response.get("response_metadata"),
            )


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
            post(client.web_client, target, unfurls)
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
