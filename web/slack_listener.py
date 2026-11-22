"""Écoute Slack en Socket Mode : un lien collé devient une carte ou un Work Object, rafraîchis à la demande."""

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

from . import config, slack_charts, slack_entities, slack_excerpts
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
    """Un titre en gras après l'icône d'Autometa, où rien n'est lu : balises échappées, mise en forme retirée."""
    inert = re.sub(r"[*~`]", "", slack_excerpts.shortened(title, 150)).replace("_", " ")
    # Why: `:autometa:` est un emoji de l'espace Slack de l'équipe ; ailleurs, Slack en affiche le nom tel quel.
    return f":autometa: *{slack_excerpts.code_safe(' '.join(inert.split())) or 'Conversation sans titre'}*"


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
            excerpt = slack_excerpts.excerpt(conv, message_id, anchor)
        except LookupError, ValueError, TypeError, AttributeError, RecursionError:
            # Why: une réponse que l'extrait ne sait pas lire garde sa carte, et les autres liens du message la leur.
            logger.exception("Extrait Slack impossible pour la conversation %s, carte sans extrait", conv_id)
            excerpt = []
        found[url] = card(conv, excerpt) | {"conv": conv, "object": config.SLACK_WORK_OBJECTS and message_id is None}
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


def drawn(found: dict[str, dict], images: bool, tables: bool) -> dict[str, dict]:
    """Les cartes telles que Slack les reçoit : graphiques en image ou nommés, tableaux en bloc table ou chasse fixe."""
    return {
        url: {"blocks": slack_excerpts.with_tables(slack_charts.shown(card["blocks"], images), tables)}
        for url, card in found.items()
    }


def post_cards(web: WebClient, target: dict, found: dict[str, dict]) -> bool:
    """Pose les cartes en blocs, sous la première forme que Slack accepte ; vrai si leurs tableaux sont en bloc table."""
    # Why: la documentation de Slack ne dit pas qu'une carte accepte un bloc table ni l'image d'un fichier : refusée,
    # elle est reposée dans l'instant avec le tableau en chasse fixe, puis sans l'image.
    forms = [(True, True), (True, False), (False, True), (False, False)]
    forms = [
        f for rank, f in enumerate(forms) if drawn(found, *f) not in [drawn(found, *seen) for seen in forms[:rank]]
    ]
    for images, tables in forms:
        try:
            web.chat_unfurl(**target, unfurls=drawn(found, images, tables))
            break
        except SlackApiError as error:
            if (images, tables) == forms[-1]:
                raise
            logger.warning(
                "Carte Slack refusée (tableau Slack : %s, image : %s), reposée autrement : %s %s",
                tables,
                images,
                error.response.get("error"),
                error.response.get("response_metadata"),
            )
    logger.info(
        "Cartes Slack posées : %s",
        [[block["type"] for block in card["blocks"]] for card in drawn(found, images, tables).values()],
    )
    return tables


def post(web: WebClient, target: dict, found: dict[str, dict]) -> None:
    """Pose objets et cartes, puis dessine et dépose les graphiques encore inconnus de Slack et repose leurs cartes."""
    metadata = {
        "entities": [
            {"app_unfurl_url": url} | slack_entities.entity(url, card["conv"])
            for url, card in found.items()
            if card["object"]
        ]
    }
    objects, together, tables = len(metadata["entities"]), {}, True
    cards = {url: card for url, card in found.items() if not card["object"]}
    # Why: la documentation de Slack ne dit pas qu'un appel accepte `unfurls` et `metadata` pour des adresses
    # différentes : refusés ensemble, ils partent en deux appels ; les objets refusés seuls, tout part en cartes.
    if objects and cards:
        try:
            web.chat_unfurl(**target, unfurls=drawn(cards, True, True), metadata=metadata)
            together = {"metadata": metadata}
            logger.info("Work Objects et cartes Slack posés en un appel : %s et %s", objects, len(cards))
        except SlackApiError as error:
            logger.warning(
                "Work Objects et cartes Slack refusés en un appel, posés en deux : %s %s",
                error.response.get("error"),
                error.response.get("response_metadata"),
            )
    if objects and not together:
        try:
            web.chat_unfurl(**target, metadata=metadata)
            logger.info("Work Objects Slack posés : %s", objects)
        except SlackApiError as error:
            cards = found
            logger.warning(
                "Work Objects Slack refusés, cartes posées à la place : %s %s",
                error.response.get("error"),
                error.response.get("response_metadata"),
            )
    if cards and not together:
        tables = post_cards(web, target, cards)
    if not config.SLACK_CHART_IMAGES:
        return
    charts = [block["source"] for card in cards.values() for block in card["blocks"] if block["type"] == "chart"]
    if not any([slack_charts.deposit(web, source) for source in charts]):
        return
    # Why: Slack traite un fichier déposé après coup et rien, avec les droits du bot, ne dit quand il est prêt ; il
    # refuse la carte d'ici là (cannot_parse_attachment, observé jusqu'à 7 s) : nouvel essai toutes les 2 s, 15 s durant.
    for wait in (3, 2, 2, 2, 2, 2, 2):
        time.sleep(wait)
        try:
            web.chat_unfurl(**target, unfurls=drawn(cards, True, tables), **together)
            logger.info("Carte Slack reposée avec son image")
            return
        except SlackApiError as error:
            refusal = error.response.get("error")
            logger.log(
                logging.INFO if refusal == "cannot_parse_attachment" else logging.WARNING,
                "Carte Slack pas encore acceptée avec son image : %s %s",
                refusal,
                error.response.get("response_metadata"),
            )
    logger.warning("Carte Slack laissée sans son image : Slack ne l'a pas acceptée dans les 15 s après le dépôt")


def present(web: WebClient, event: dict) -> None:
    """Remplit le volet de détails que Slack ouvre au clic sur un Work Object, ou y dit la conversation introuvable."""
    url, trigger = event.get("app_unfurl_url") or event.get("entity_url"), event.get("trigger_id")
    conv_id = url and trigger and (located(url) or [None])[0]
    if not conv_id:
        logger.warning("Détails d'un Work Object Slack demandés sans adresse de cette instance, ignorés")
        return
    conv = store.get_conversation(conv_id, include_messages=False)
    if conv:
        web.entity_presentDetails(trigger_id=trigger, metadata=slack_entities.entity(url, conv))
    else:
        web.entity_presentDetails(trigger_id=trigger, error={"status": "not_found"})
        logger.info("Détails d'un Work Object Slack demandés pour une conversation inconnue : %s", conv_id)


def handle(client: SocketModeClient, request: SocketModeRequest) -> None:
    """Accuse réception, puis pose ou rafraîchit les cartes des liens que l'événement désigne."""
    client.send_socket_mode_response(SocketModeResponse(envelope_id=request.envelope_id))
    event = request.payload.get("event") or {}
    details = request.type == "events_api" and event.get("type") == "entity_details_requested"
    found = None if details else asked(request)
    if not found and not (details and config.SLACK_WORK_OBJECTS):
        return
    try:
        if details:
            present(client.web_client, event)
            return
        urls, target = found
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
