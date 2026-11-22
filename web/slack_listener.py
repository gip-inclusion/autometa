"""Écoute Slack en Socket Mode : un lien collé devient une carte ou un Work Object, rafraîchis à la demande."""

import http.client
import logging
import queue
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

from . import config, slack_charts, slack_dashboards, slack_entities, slack_excerpts, slack_icons
from .database import store
from .helpers import CONV_ID, to_local, utcnow
from .stores.records import Conversation

logger = logging.getLogger(__name__)

CONVERSATION_PATH = re.compile(rf"/(?:c|explorations)/({CONV_ID.pattern})(?:/([0-9]{{1,10}})(?:/([^/]+))?)?(?:/.*)?")
REFRESH_ACTION = "refresh_conversation_card"

refreshed: dict[str, float] = {}
# Les cartes qui attendent l'image de leur graphique, et le fil qui les sert une à une.
drawing: queue.Queue = queue.Queue(maxsize=20)
workers: list[threading.Thread] = []
starting = threading.Lock()


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
    """La carte et l'objet éventuel de chaque adresse qui mène à une conversation ou un tableau de bord connus."""
    found = {}
    for url in urls:
        conv_id, message_id, anchor = located(url) or (None, None, None)
        conv = conv_id and store.get_conversation(conv_id, include_messages=False)
        dashboard = None if conv_id or not config.SLACK_WORK_OBJECTS else slack_dashboards.entity(url)
        if dashboard:
            found[url] = {"blocks": None, "entity": dashboard}
        if not conv:
            continue
        try:
            excerpt = slack_excerpts.excerpt(conv, message_id, anchor)
        except LookupError, ValueError, TypeError, AttributeError, RecursionError:
            # Why: une réponse que l'extrait ne sait pas lire garde sa carte, et les autres liens du message la leur.
            logger.exception("Extrait Slack impossible pour la conversation %s, carte sans extrait", conv_id)
            excerpt = []
        whole = config.SLACK_WORK_OBJECTS and message_id is None
        found[url] = card(conv, excerpt) | {"entity": slack_entities.entity(url, conv) if whole else None}
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


def took(event_ts: str | None, read: float, began: float) -> str:
    """Ce qu'une pose a pris, pour sa ligne de journal : depuis l'événement de Slack, à lire, puis à appeler Slack."""
    parts = [f"lecture {read * 1000:.0f} ms", f"Slack {(time.monotonic() - began) * 1000:.0f} ms"]
    if re.fullmatch(r"\d+(\.\d+)?", event_ts or ""):
        parts.insert(0, f"événement +{time.time() - float(event_ts):.1f} s".replace(".", ","))
    return f"({', '.join(parts)})"


def post_cards(web: WebClient, target: dict, found: dict[str, dict], timed: tuple) -> tuple[bool, bool]:
    """Pose les cartes en blocs, sous la première forme que Slack accepte ; dit si elle a ses images, ses blocs table."""
    # Why: la documentation de Slack ne dit pas qu'une carte accepte un bloc table ni l'image d'un fichier : refusée,
    # elle est reposée dans l'instant avec le tableau en chasse fixe, puis sans l'image.
    forms = [(True, True), (True, False), (False, True), (False, False)]
    forms = [
        f for rank, f in enumerate(forms) if drawn(found, *f) not in [drawn(found, *seen) for seen in forms[:rank]]
    ]
    began = time.monotonic()
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
        "Cartes Slack posées : %s %s",
        [[block["type"] for block in card["blocks"]] for card in drawn(found, images, tables).values()],
        took(*timed, began),
    )
    return images, tables


def post(web: WebClient, target: dict, found: dict[str, dict], timed: tuple) -> None:
    """Pose objets et cartes sans attendre leurs graphiques : une carte sans son image la demande au fil qui dessine."""
    metadata = {
        "entities": [
            {"app_unfurl_url": url} | slack_icons.with_icon(web, card["entity"])
            for url, card in found.items()
            if card["entity"]
        ]
    }
    objects, together, images, tables = len(metadata["entities"]), {}, True, True
    cards = {url: card for url, card in found.items() if not card["entity"]}
    # Why: la documentation de Slack ne dit pas qu'un appel accepte `unfurls` et `metadata` pour des adresses
    # différentes : refusés ensemble, ils partent en deux appels ; les objets refusés seuls, tout part en cartes.
    began = time.monotonic()
    if objects and cards:
        try:
            web.chat_unfurl(**target, unfurls=drawn(cards, True, True), metadata=metadata)
            together = {"metadata": metadata}
            logger.info(
                "Work Objects et cartes Slack posés en un appel : %s et %s %s", objects, len(cards), took(*timed, began)
            )
        except SlackApiError as error:
            logger.warning(
                "Work Objects et cartes Slack refusés en un appel, posés en deux : %s %s",
                error.response.get("error"),
                error.response.get("response_metadata"),
            )
    if objects and not together:
        try:
            began = time.monotonic()
            web.chat_unfurl(**target, metadata=metadata)
            logger.info("Work Objects Slack posés : %s %s", objects, took(*timed, began))
        except SlackApiError as error:
            # Why: un tableau de bord n'a pas de carte en blocs ; son objet refusé, son lien reste nu.
            cards = {url: card for url, card in found.items() if card["blocks"]}
            logger.warning(
                "Work Objects Slack refusés, cartes posées à la place : %s %s",
                error.response.get("error"),
                error.response.get("response_metadata"),
            )
    if cards and not together:
        images, tables = post_cards(web, target, cards, timed)
    charts = [block["source"] for card in cards.values() for block in card["blocks"] if block["type"] == "chart"]
    shown = images and all(slack_charts.key(source) in slack_charts.files for source in charts)
    # Why: une carte partie sans l'image d'un fichier déjà déposé (Slack ne l'avait pas encore traité) la redemande.
    if config.SLACK_CHART_IMAGES and charts and not shown:
        queue_images((web, target, cards, tables, together))


def queue_images(job: tuple) -> None:
    """Confie une carte au fil qui dessine, relancé s'il n'est plus ; au-delà de 20 en attente, elle reste sans image."""
    try:
        drawing.put_nowait(job)
    except queue.Full:
        logger.warning("Carte Slack laissée sans image : 20 cartes attendent déjà la leur")
        return
    with starting:
        # Why: un fil mort d'une erreur imprévue repart à la carte suivante, sans qu'il faille tout attraper.
        if not any(worker.is_alive() for worker in workers):
            workers[:] = [threading.Thread(target=illustrator, daemon=True, name="slack-charts")]
            workers[0].start()


def illustrator() -> None:
    """Sert une à une les cartes en attente d'image, hors des fils qui accusent réception à Slack."""
    while True:
        job = drawing.get()
        try:
            illustrate(*job)
        except (SlackClientError, OSError) as error:
            logger.warning("Carte Slack laissée sans son image, Slack injoignable : %s", error)


def illustrate(web: WebClient, target: dict, cards: dict[str, dict], tables: bool, together: dict) -> None:
    """Dessine et dépose les graphiques encore inconnus de Slack, puis repose leurs cartes avec l'image."""
    charts = [block["source"] for card in cards.values() for block in card["blocks"] if block["type"] == "chart"]
    for source in charts:
        slack_charts.deposit(web, source)
    if not any(slack_charts.key(source) in slack_charts.files for source in charts):
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


def panes(url: str) -> list[dict] | None:
    """Le volet de détails de l'objet qu'adresse `url`, puis l'objet seul ; aucun s'il est inconnu, None hors instance."""
    conv_id = (located(url) or [None])[0]
    if not conv_id:
        if not slack_dashboards.located(url):
            return None
        return [shown for shown in (slack_dashboards.entity(url, detailed=True), slack_dashboards.entity(url)) if shown]
    conv = store.get_conversation(conv_id, include_messages=False)
    if not conv:
        return []
    try:
        details = slack_entities.details(conv)
    except LookupError, ValueError, TypeError, AttributeError, RecursionError:
        # Why: une conversation que le volet ne sait pas lire garde son volet, réduit à ce que l'objet dit déjà.
        logger.exception("Détails Slack impossibles pour la conversation %s, volet sans eux", conv_id)
        details = []
    return [slack_entities.entity(url, conv, details), slack_entities.entity(url, conv)]


def present(web: WebClient, event: dict) -> None:
    """Remplit le volet de détails que Slack ouvre au clic sur un Work Object, ou y dit l'objet introuvable."""
    url, trigger = event.get("app_unfurl_url") or event.get("entity_url"), event.get("trigger_id")
    began = time.monotonic()
    found = panes(url) if url and trigger else None
    read, began = time.monotonic() - began, time.monotonic()
    if found is None:
        logger.warning("Détails d'un Work Object Slack demandés sans adresse de cette instance, ignorés")
        return
    if not found:
        web.entity_presentDetails(trigger_id=trigger, error={"status": "not_found"})
        logger.info("Détails d'un Work Object Slack demandés pour un objet inconnu : %s", urlsplit(url).path)
        return
    full, bare = (slack_icons.with_icon(web, shown) for shown in found)
    try:
        web.entity_presentDetails(trigger_id=trigger, metadata=full)
        logger.info(
            "Volet de détails Slack rempli : %s %s",
            [shown["key"] for shown in full["entity_payload"]["custom_fields"]],
            took(event.get("event_ts"), read, began),
        )
    except SlackApiError as error:
        if full["entity_payload"]["custom_fields"] == bare["entity_payload"]["custom_fields"]:
            raise
        # Why: la documentation de Slack ne borne pas un champ long ; refusé avec eux, le volet garde l'objet seul.
        logger.warning(
            "Volet de détails Slack refusé avec ses champs, rempli sans eux : %s %s",
            error.response.get("error"),
            error.response.get("response_metadata"),
        )
        web.entity_presentDetails(trigger_id=trigger, metadata=bare)


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
        began = time.monotonic()
        unfurls = cards(urls)
        if unfurls:
            post(client.web_client, target, unfurls, (event.get("event_ts"), time.monotonic() - began))
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
