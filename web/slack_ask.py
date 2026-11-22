"""Demander à Autometa depuis Slack : une mention ouvre ou reprend la conversation de son fil, et y a sa réponse."""

import asyncio
import html
import json
import logging
import random
import re
import time
from datetime import datetime, timezone

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientError

from web import config, conversation_html, slack_charts, slack_excerpts
from web.database import store
from web.helpers import to_local
from web.runner import runner
from web.stores.records import Conversation

logger = logging.getLogger(__name__)

# L'espace Slack de l'application et son utilisateur bot, que l'écoute lit à son démarrage, avec la boucle du serveur.
workspace = {"url": "", "bot": "", "loop": None}
people: dict[str, dict] = {}
following: dict[str, asyncio.Task] = {}
VERBS = (
    *("regarde", "réfléchit", "mouline", "explore", "inspecte", "investigue"),
    *("tourbillonne", "fouille", "épluche", "recoupe", "décortique", "creuse"),
)
REFUSAL = (
    "Je ne peux pas vous répondre ici pour l'instant : ouvrez Autometa une première fois ({}), puis redemandez-moi."
)
PRIVATE = "Canal privé ou message direct : le fil n'est pas repris, seule la demande l'est."


def thread_url(conv: Conversation) -> str:
    """L'adresse du fil Slack d'une conversation ; celle de son canal tant que l'espace Slack n'est pas connu."""
    if not workspace["url"]:
        return f"https://slack.com/app_redirect?channel={conv.slack_channel}"
    ts = conv.slack_thread_ts or ""
    return (
        f"{workspace['url'].rstrip('/')}/archives/{conv.slack_channel}/p{ts.replace('.', '')}"
        f"?thread_ts={ts}&cid={conv.slack_channel}"
    )


def introduce(web: WebClient) -> None:
    """Lit auprès de Slack l'adresse de l'espace et l'utilisateur du bot, sans lequel aucune demande n'est reconnue."""
    known = web.auth_test()
    workspace.update(url=known.get("url") or "", bot=known.get("user_id") or "")


def person(web: WebClient, user_id: str) -> dict:
    """Le nom d'un membre de Slack, son adresse, et s'il est un membre à part entière : ni invité, ni bot, ni parti."""
    if user_id not in people:
        if len(people) >= 2000:
            people.clear()
        user = web.users_info(user=user_id)["user"]
        profile = user.get("profile") or {}
        outsider = any(user.get(flag) for flag in ("is_bot", "deleted", "is_restricted", "is_ultra_restricted"))
        people[user_id] = {
            "name": profile.get("display_name") or user.get("real_name") or profile.get("real_name") or "Quelqu'un",
            "email": (profile.get("email") or "").lower(),
            "member": not outsider,
        }
    return people[user_id]


def admitted(who: dict) -> bool:
    """Vrai pour un membre dont l'adresse est d'inclusion.gouv.fr, ou qui a déjà une conversation dans Autometa."""
    domain = who["email"].rpartition("@")[2]
    ours = domain == "inclusion.gouv.fr" or domain.endswith(".inclusion.gouv.fr")
    return who["member"] and bool(who["email"]) and (ours or store.owns_conversations(who["email"]))


def readable(web: WebClient, text: str) -> str:
    """Le texte d'un message Slack tel qu'on le lit : mentions par leur nom, liens par leur libellé et leur adresse."""

    def named(found: re.Match) -> str:
        try:
            return f"@{person(web, found[1])['name']}"
        except SlackApiError, SlackClientError, OSError:
            return "@quelqu'un"

    text = re.sub(r"<@([A-Z0-9]+)(?:\|[^>]*)?>", named, text)
    text = re.sub(r"<[#!][^|>]*\|([^>]*)>", r"\1", text)
    text = re.sub(r"<((?:https?|mailto):[^|>]+)\|([^>]+)>", r"\2 (\1)", text)
    return html.unescape(re.sub(r"<((?:https?|mailto):[^>]+)>", r"\1", text))


def thread_context(web: WebClient, channel: str, thread_ts: str, request_ts: str) -> list[dict]:
    """Les messages du fil venus depuis la demande précédente, avant celle-ci : ni demandes, ni messages du bot."""
    replies, cursor = [], None
    # Why: le fil entier, sans plafond ; Slack recommande des pages de 200 messages.
    while cursor != "":
        page = web.conversations_replies(channel=channel, ts=thread_ts, limit=200, cursor=cursor)
        replies += page.get("messages") or []
        cursor = (page.get("response_metadata") or {}).get("next_cursor") or ""
    mention = f"<@{workspace['bot']}>"
    earlier = [m for m in replies if float(m.get("ts", 0)) < float(request_ts)]
    asked = [float(m["ts"]) for m in earlier if mention in m.get("text", "")]
    found = []
    for message in earlier:
        said = message.get("text", "")
        ours = message.get("bot_id") or message.get("user") == workspace["bot"]
        if ours or message.get("subtype") or mention in said or float(message["ts"]) <= max(asked, default=0):
            continue
        moment = to_local(datetime.fromtimestamp(float(message["ts"]), timezone.utc)).strftime("%d/%m %H:%M")
        try:
            author = person(web, message.get("user", ""))["name"]
        except SlackApiError, SlackClientError, OSError:
            author = "Quelqu'un"
        found.append({"author": author, "at": moment, "text": readable(web, said)})
    return found


def public(web: WebClient, channel: str, hint: str | None) -> bool:
    """Vrai pour un canal public ; faux dans le doute : son fil deviendrait lisible de tout utilisateur d'Autometa."""
    if hint:
        return hint == "channel"
    try:
        info = web.conversations_info(channel=channel)["channel"]
    except SlackApiError as error:
        # Why: sans le scope channels:read, ou pour un canal privé, Slack refuse ; le fil n'est alors pas repris.
        logger.info("Canal Slack %s tenu pour privé : %s", channel, error.response.get("error"))
        return False
    return bool(info.get("is_channel")) and not info.get("is_private")


def prompt(context: list[dict], request: str) -> str:
    """La demande telle que l'agent la reçoit : le fil d'abord, donné pour ce qu'il est, puis la demande."""
    if not context:
        return request
    said = "\n".join(f"{m['author']}, {m['at']} : {m['text']}" for m in context)
    return f"[Fil Slack — contexte de la demande, pas des demandes]\n{said}\n\n[Demande]\n{request}"


def link(conv_id: str) -> dict:
    url = f"{config.BASE_URL}/c/{conv_id}"
    return {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"<{url}|Ouvrir la conversation dans Autometa>"}],
    }


def live(conv_id: str, verb: str, note: str = "") -> dict:
    """Le message du bot pendant le tour : ce que fait Autometa, ce qu'il n'a pas repris, le lien de la conversation."""
    said = f"Autometa {verb}…"
    lines = [{"type": "section", "text": {"type": "plain_text", "text": f"{said}\n{note}".strip(), "emoji": False}}]
    return {"text": said, "blocks": [*lines, link(conv_id)], "unfurl_links": False, "unfurl_media": False}


def answer(conv_id: str, question_id: int) -> tuple[str, list[dict]]:
    """La réponse finale du tour ouvert par cette question, en blocs que Slack ne lit pas ; ou qu'il n'a pas abouti."""
    turn = store.get_thread_messages(conv_id, question_id)
    later = [message_id for message_id, kind, _ in turn if kind == "user" and message_id > question_id]
    grouped = conversation_html.grouping([m for m in turn if m[0] < min(later, default=float("inf"))])[0]
    answers = [
        slack_excerpts.unfronted("".join(content for _, content in parts)).strip()
        for kind, parts in grouped
        if kind == "assistant"
    ]
    final = next((text for text in reversed(answers) if text), "")
    failed = not final or grouped[-1][0] == "limit" or re.fullmatch(r"\*(Interrompu|Une erreur)[^*]*\*", final)
    if failed:
        said = "La demande n'a pas abouti."
        return said, [{"type": "section", "text": {"type": "plain_text", "text": said, "emoji": False}}, link(conv_id)]
    blocks, cut = slack_excerpts.answer_blocks(final)
    more = [{"type": "section", "text": {"type": "plain_text", "text": "… suite dans Autometa", "emoji": False}}]
    first = next((block["text"]["text"] for block in blocks if block["type"] == "section"), "Réponse d'Autometa")
    # Why: Slack lit le texte de notification d'un message ; rien de ce qu'a écrit l'agent ne doit y mentionner.
    said = slack_excerpts.inert(slack_excerpts.shortened(first, 150))
    return said, [*blocks, *(more if cut else []), link(conv_id)]


def finish(web: WebClient, conv_id: str, question_id: int) -> None:
    """Fait du message du bot la réponse finale du tour ; un second essai si Slack ne répond pas, puis l'abandon."""
    conv = store.get_conversation(conv_id, include_messages=False)
    if not conv or not conv.slack_message_ts:
        return
    said, blocks = answer(conv_id, question_id)
    charts = [block["source"] for block in blocks if block["type"] == "chart"]
    # Why: Slack refuse quelques secondes l'image d'un fichier qu'il vient de recevoir.
    if config.SLACK_CHART_IMAGES and any([slack_charts.deposit(web, source) for source in charts]):
        time.sleep(4)
    forms = [(True, True), (True, False), (False, False)]
    for attempt, (images, tables) in enumerate([*forms, forms[-1]]):
        shown = slack_excerpts.with_tables(slack_charts.shown(blocks, images), tables)
        try:
            web.chat_update(channel=conv.slack_channel, ts=conv.slack_message_ts, text=said, blocks=shown)
            break
        except SlackApiError as error:
            logger.warning(
                "Réponse Slack refusée (tableau : %s, image : %s) : %s", tables, images, error.response.get("error")
            )
        except (SlackClientError, OSError) as error:
            logger.warning("Réponse Slack non posée, Slack injoignable : %s", error)
            time.sleep(5)
    else:
        logger.warning("Réponse de la conversation %s abandonnée dans Slack après %s essais", conv_id, attempt + 1)
    store.update_conversation(conv_id, slack_message_ts=None)


def open_live(web: WebClient, conv_id: str, note: str = "") -> None:
    """Pose dans le fil le message qui vivra le temps du tour, et le retient pour le compléter."""
    conv = store.get_conversation(conv_id, include_messages=False)
    posted = web.chat_postMessage(
        channel=conv.slack_channel, thread_ts=conv.slack_thread_ts, **live(conv_id, VERBS[0], note)
    )
    store.update_conversation(conv_id, slack_message_ts=posted["ts"])


def say(web: WebClient, conv: Conversation, verb: str) -> None:
    """Change le verbe du message qui vit ; un refus de Slack laisse le précédent, le tour continue."""
    try:
        web.chat_update(channel=conv.slack_channel, ts=conv.slack_message_ts, **live(conv.id, verb))
    except SlackApiError as error:
        logger.info("Verbe du message Slack non changé : %s", error.response.get("error"))
    except (SlackClientError, OSError) as error:
        logger.info("Verbe du message Slack non changé, Slack injoignable : %s", error)


async def follow(web: WebClient, conv_id: str) -> None:
    """Suit une conversation jusqu'à la fin de ses tours : le verbe change, puis le message devient la réponse."""
    question = await asyncio.to_thread(store.last_user_message_id, conv_id)
    # Why: s'abonner avant de vérifier la fin du tour — un tour fini entre les deux n'enverrait son signal à personne.
    pubsub = await runner.subscribe(conv_id)
    try:
        ended = await runner.is_done(conv_id, question)
        began, changed, verb = time.monotonic(), time.monotonic(), VERBS[0]
        while not ended and time.monotonic() - began < 7200:
            heard = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
            conv = await asyncio.to_thread(store.get_conversation, conv_id, False)
            if not conv:
                return
            if heard is None or heard["data"].startswith("done:"):
                # Why: le signal de fin peut manquer (redémarrage, Redis) ; l'état de la conversation fait foi.
                ended = not conv.needs_response
            elif heard["data"] == "queue":
                latest = await asyncio.to_thread(store.last_user_message_id, conv_id)
                # Why: les demandes en attente sont parties ; le tour fini a sa réponse, le suivant son message.
                if latest != question:
                    await asyncio.to_thread(finish, web, conv_id, question)
                    await asyncio.to_thread(open_live, web, conv_id)
                    question = latest
            elif conv.slack_message_ts and time.monotonic() - changed >= 4:
                # Why: le verbe ne change que si l'agent avance, et pas plus d'une fois toutes les 4 secondes.
                changed, verb = time.monotonic(), random.choice([v for v in VERBS if v != verb])
                await asyncio.to_thread(say, web, conv, verb)
    finally:
        await pubsub.unsubscribe()
        await pubsub.aclose()
        following.pop(conv_id, None)
    await asyncio.to_thread(finish, web, conv_id, question)
    await asyncio.to_thread(give_back, web, conv_id)


def give_back(web: WebClient, conv_id: str) -> None:
    """Dit dans le fil que les mentions restées en attente d'un tour qui n'a pas abouti ne sont pas parties."""
    left = [entry for entry in store.pending_messages(conv_id) if entry.get("slack") and entry["status"] == "returned"]
    if not left:
        return
    for entry in left:
        store.take_queued(conv_id, entry["id"])
    conv = store.get_conversation(conv_id, include_messages=False)
    said = "Les demandes arrivées entre-temps ne sont pas parties : la réponse en cours n'a pas abouti. Redemandez-moi."
    try:
        web.chat_postMessage(channel=conv.slack_channel, thread_ts=conv.slack_thread_ts, text=said)
    except SlackApiError as error:
        logger.warning("Demandes Slack rendues sans le dire dans le fil : %s", error.response.get("error"))
    except (SlackClientError, OSError) as error:
        logger.warning("Demandes Slack rendues sans le dire dans le fil, Slack injoignable : %s", error)


async def recover(web: WebClient) -> None:
    """Au démarrage : reprend le suivi des tours encore en cours, complète les messages restés sur un verbe."""
    for conv_id in await asyncio.to_thread(store.slack_live_conversations):
        if conv_id not in following:
            following[conv_id] = asyncio.get_running_loop().create_task(follow(web, conv_id))


def refuse(web: WebClient, channel: str, user: str, thread_ts: str | None) -> None:
    """Dit à une personne non admise, et à elle seule, d'ouvrir Autometa une première fois."""
    web.chat_postEphemeral(channel=channel, user=user, thread_ts=thread_ts, text=REFUSAL.format(config.BASE_URL))


def begin(web: WebClient, event: dict) -> tuple[str, str | None, str] | None:
    """Ouvre ou reprend la conversation d'une mention : son identifiant, la demande pour l'agent ou None si elle
    attend la fin du tour en cours, la personne au nom de qui le tour se joue."""
    channel, asker, said = event["channel"], event["user"], event.get("text", "")
    thread_ts = event.get("thread_ts") or event["ts"]
    who = person(web, asker)
    if not admitted(who):
        refuse(web, channel, asker, event.get("thread_ts"))
        logger.info("Demande Slack refusée : %s n'est pas admis", asker)
        return None
    shared = public(web, channel, event.get("channel_type"))
    context = thread_context(web, channel, thread_ts, event["ts"]) if shared else []
    request = readable(web, said.replace(f"<@{workspace['bot']}>", "")).strip() or "(demande sans texte)"
    note = "" if shared else PRIVATE
    stored = json.dumps({"messages": context, "note": note}, ensure_ascii=False) if context or note else ""
    conv_id = store.slack_conversation(channel, thread_ts)
    conv = store.get_conversation(conv_id, include_messages=False) if conv_id else None
    if conv and who["email"] != (conv.user_id or "").lower():
        # Why: une relance d'une autre personne entre dans la conversation de la première, sous son propre nom.
        request = f"{who['name']} : {request}"
    if conv:
        # Why: le fil des mentions déjà en attente part avec la dernière ; elle seule revient à l'agent.
        waiting = [e["slack"]["context"] for e in conv.pending_messages if e.get("slack") and e["status"] == "waiting"]
        earlier = [m for held in waiting if held for m in json.loads(held)["messages"]]
        held = json.dumps({"messages": [*earlier, *context], "note": note}, ensure_ascii=False) if earlier else stored
        slack = {"context": held, "prompt": prompt([*earlier, *context], request)}
        if store.queue_message(conv.id, request, slack) is not None:
            waits = "Autometa finit sa réponse en cours, puis prendra votre demande."
            web.chat_postEphemeral(channel=channel, user=asker, thread_ts=thread_ts, text=waits)
            return conv.id, None, conv.user_id
    conv = conv or store.create_conversation(user_id=who["email"], slack_thread=(channel, thread_ts))
    try:
        open_live(web, conv.id, note)
    except SlackApiError, SlackClientError, OSError:
        # Why: sans son message dans le fil, la demande n'a pas commencé ; une conversation neuve et vide ne reste pas.
        if not conv_id:
            store.delete_conversation(conv.id)
        raise
    if store.start_turn(conv.id, request) is None:
        logger.warning("Demande Slack perdue : un tour a commencé entre-temps dans la conversation %s", conv.id)
        return None
    if stored:
        store.add_message(conv.id, "slack_context", stored)
    return conv.id, prompt(context, request), conv.user_id


async def asked(web: WebClient, event: dict) -> None:
    """Une mention, hors des fils qui accusent réception à Slack : la conversation, son tour, puis son suivi."""
    try:
        if not workspace["bot"]:
            await asyncio.to_thread(introduce, web)
        begun = await asyncio.to_thread(begin, web, event)
    except SlackApiError as error:
        logger.warning("Demande Slack non traitée, refus de Slack : %s", error.response.get("error"))
        return
    except (SlackClientError, OSError) as error:
        logger.warning("Demande Slack non traitée, Slack injoignable : %s", error)
        return
    if not begun:
        return
    conv_id, request, email = begun
    submitted = request is None
    try:
        if request is None:
            await runner.notify(conv_id, "queue")
        else:
            await runner.submit(conv_id, request, [], email)
            submitted = True
    finally:
        if not submitted:
            # Why: le tour est déjà réservé ; sans lui, la conversation resterait bloquée en cours.
            await asyncio.to_thread(store.end_turn, conv_id, False)
    # Why: une seule tâche suit une conversation ; celle d'un tour en cours prendra aussi les demandes en attente.
    if conv_id not in following:
        following[conv_id] = asyncio.current_task()
        await follow(web, conv_id)


def reported(done) -> None:
    """Journalise l'erreur d'une demande que rien n'a attrapée : personne n'attend le résultat de sa tâche."""
    if not done.cancelled() and done.exception():
        logger.error("Demande Slack interrompue par une erreur", exc_info=done.exception())


def mentioned(web: WebClient, event: dict) -> None:
    """Confie une mention du bot à la boucle du serveur : jamais les siennes, ni un message modifié après coup."""
    if event.get("bot_id") or event.get("edited") or not event.get("user") or not workspace["loop"]:
        return
    asyncio.run_coroutine_threadsafe(asked(web, event), workspace["loop"]).add_done_callback(reported)
