"""Demander à Autometa depuis Slack : une mention ou le raccourci ouvre ou reprend la conversation d'un fil."""

import asyncio
import html
import json
import logging
import random
import re
import time
import uuid
from datetime import datetime, timezone

from redis.exceptions import RedisError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientError
from sqlalchemy.exc import SQLAlchemyError

from web import complexity, config, conversation_html, slack_charts, slack_context, slack_excerpts
from web.database import store
from web.helpers import to_local
from web.redis_conn import get_redis
from web.routes.conversations import generate_conversation_tags, generate_conversation_title
from web.runner import runner
from web.stores.records import Conversation

logger = logging.getLogger(__name__)

# L'espace Slack de l'application et son utilisateur bot, que l'écoute lit à son démarrage, avec la boucle du serveur.
workspace = {"url": "", "bot": "", "loop": None}
people: dict[str, tuple[float, dict]] = {}
following: dict[str, asyncio.Task] = {}
VERBS = (
    *("regarde", "réfléchit", "mouline", "explore", "inspecte", "investigue"),
    *("tourbillonne", "fouille", "épluche", "recoupe", "décortique", "creuse"),
)
REFUSAL = (
    "Je ne peux pas vous répondre ici pour l'instant : ouvrez Autometa une première fois ({}), puis redemandez-moi."
)
PRIVATE = "Canal privé ou message direct : le fil n'est pas repris, seule la demande l'est."
SHORTCUT = "ask_autometa"
AWAY = "Je ne suis pas dans ce canal : je vous réponds ici, à vous seul, sans le reste du fil."


def thread_url(conv: Conversation) -> str:
    """L'adresse du fil Slack d'une conversation ; celle de son canal tant que l'espace Slack n'est pas connu."""
    if not workspace["url"] or not conv.slack_thread_ts:
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
    """Le nom d'un membre de Slack, son adresse, s'il est invité ou extérieur, et s'il est membre à part entière."""
    known = people.get(user_id)
    # Why: un invité promu, un compte désactivé : ce que Slack a dit d'une personne ne vaut que dix minutes.
    if known and known[0] > time.monotonic():
        return known[1]
    if len(people) >= 2000:
        people.clear()
    user = web.users_info(user=user_id)["user"]
    profile = user.get("profile") or {}
    guest = any(user.get(flag) for flag in ("is_restricted", "is_ultra_restricted", "is_stranger"))
    people[user_id] = (
        time.monotonic() + 600,
        {
            "name": profile.get("display_name") or user.get("real_name") or profile.get("real_name") or "Quelqu'un",
            "email": (profile.get("email") or "").lower(),
            "guest": guest,
            "member": not (guest or user.get("is_bot") or user.get("deleted")),
        },
    )
    return people[user_id][1]


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


def replies(web: WebClient, channel: str, thread_ts: str) -> list[dict]:
    """Tous les messages d'un fil, sans plafond, par pages de 200 comme Slack le recommande."""
    found, cursor = [], None
    while cursor != "":
        page = web.conversations_replies(channel=channel, ts=thread_ts, limit=200, cursor=cursor)
        found += page.get("messages") or []
        cursor = (page.get("response_metadata") or {}).get("next_cursor") or ""
    return found


def said_by(web: WebClient, message: dict) -> dict | None:
    """Un message Slack repris dans le contexte : auteur, heure, texte ; None pour un invité ou un auteur extérieur."""
    try:
        who = person(web, message["user"]) if message.get("user") else {"name": "Une application", "guest": False}
    except SlackApiError, SlackClientError, OSError:
        # Why: un auteur que Slack ne veut pas nommer est tenu pour extérieur.
        return None
    if who["guest"]:
        return None
    moment = to_local(datetime.fromtimestamp(float(message["ts"]), timezone.utc)).strftime("%d/%m %H:%M")
    return {"author": who["name"], "at": moment, "text": readable(web, message.get("text", "")), "ts": message["ts"]}


def thread_context(web: WebClient, thread: list[dict], after: float, before: float) -> tuple[list[dict], int]:
    """Les messages du fil écrits par des personnes entre deux moments, et combien d'invités ou d'extérieurs écartés."""
    kept, left_out = [], 0
    for message in thread:
        # Why: une réponse aussi envoyée au canal et un message avec fichier sont des messages de personnes ; les
        # autres sous-types (arrivées, renommages…) n'en sont pas, ni ceux d'applications.
        human = message.get("user") and not message.get("bot_id") and message.get("user") != workspace["bot"]
        if not human or message.get("subtype") not in (None, "thread_broadcast", "file_share"):
            continue
        if not after < float(message["ts"]) < before:
            continue
        said = said_by(web, message)
        kept += [said] if said else []
        left_out += said is None
    return kept, left_out


def by_time(message: dict) -> float:
    return float(message["ts"])


def public(web: WebClient, channel: str, hint: str | None) -> bool:
    """Vrai pour un canal public de notre seul espace ; faux dans le doute : son fil serait lu de tout Autometa."""
    if hint in ("group", "im", "mpim"):
        return False
    try:
        info = web.conversations_info(channel=channel)["channel"]
    except SlackApiError as error:
        # Why: sans le scope channels:read, ou pour un canal privé, Slack refuse ; le fil n'est alors pas repris.
        logger.info("Canal Slack %s tenu pour privé : %s", channel, error.response.get("error"))
        return False
    # Why: un canal partagé avec une autre organisation porte des messages de personnes extérieures.
    elsewhere = any(info.get(flag) for flag in ("is_ext_shared", "is_org_shared", "is_pending_ext_shared"))
    return bool(info.get("is_channel")) and not info.get("is_private") and not elsewhere


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


def turn_note(conv_id: str, question_id: int) -> str:
    """Ce que le bot dit ne pas avoir repris pour le tour de cette question : rien si tout le fil l'a été."""
    kept = store.slack_contexts(conv_id, question_id)
    return json.loads(kept[0]).get("note", "") if kept else ""


def answer(conv_id: str, question_id: int) -> tuple[str, list[dict]]:
    """La réponse finale du tour ouvert par cette question, en blocs que Slack ne lit pas ; ou qu'il n'a pas abouti."""
    turn = store.get_thread_messages(conv_id, question_id)
    later = [message_id for message_id, kind, _ in turn if kind == "user" and message_id > question_id]
    # Why: l'alerte de complexité est un message du serveur glissé dans le tour, pas la réponse de l'agent.
    said = [m for m in turn if m[0] < min(later, default=float("inf")) and m[2] != complexity.ALERT_MESSAGE]
    last = next((m for m in reversed(said) if m[1] in ("assistant", "limit") and m[2].strip()), None)
    # Why: le serveur clôt un tour arrêté, en erreur ou hors budget par une note en italique, message à part ; une
    # limite d'usage par un avis. Le dernier message du tour dit donc s'il a abouti, quoi que l'agent ait écrit avant.
    note = last and re.fullmatch(r"\*(Interrompu|Une erreur|Budget de)[^*]*\*", last[2].strip())
    grouped = conversation_html.grouping(said)[0]
    answers = [
        slack_excerpts.unfronted("".join(content for _, content in parts)).strip()
        for kind, parts in grouped
        if kind == "assistant"
    ]
    final = next((text for text in reversed(answers) if text), "")
    kept = turn_note(conv_id, question_id)
    aside = [{"type": "context", "elements": [{"type": "plain_text", "text": kept, "emoji": False}]}] if kept else []
    if not last or last[1] == "limit" or note:
        failed = "La demande n'a pas abouti."
        text = {"type": "plain_text", "text": failed, "emoji": False}
        return failed, [{"type": "section", "text": text}, *aside, link(conv_id)]
    blocks, cut = slack_excerpts.answer_blocks(final)
    more = [{"type": "section", "text": {"type": "plain_text", "text": "… suite dans Autometa", "emoji": False}}]
    first = next((block["text"]["text"] for block in blocks if block["type"] == "section"), "Réponse d'Autometa")
    # Why: Slack lit le texte de notification d'un message ; rien de ce qu'a écrit l'agent ne doit y mentionner.
    notified = slack_excerpts.inert(slack_excerpts.shortened(first, 150))
    return notified, [*blocks, *(more if cut else []), *aside, link(conv_id)]


def retry_after(error: SlackApiError) -> int:
    """Les secondes que Slack demande d'attendre quand il limite le débit ; 0 pour tout autre refus."""
    if error.response.get("error") != "ratelimited":
        return 0
    asked = str((getattr(error.response, "headers", None) or {}).get("Retry-After", ""))
    return min(int(asked), 60) if asked.isdigit() else 5


def finish(web: WebClient, conv_id: str, question_id: int) -> None:
    """Fait du message du bot la réponse finale du tour, sous la première forme que Slack accepte."""
    conv = store.get_conversation(conv_id, include_messages=False)
    if not conv or not conv.slack_message_ts:
        return
    said, blocks = answer(conv_id, question_id)
    charts = [block["source"] for block in blocks if block["type"] == "chart"]
    # Why: Slack refuse quelques secondes l'image d'un fichier qu'il vient de recevoir.
    if config.SLACK_CHART_IMAGES and any([slack_charts.deposit(web, source) for source in charts]):
        time.sleep(4)
    forms, waited, unreachable = [(True, True), (True, False), (False, False)], 0, 0
    while forms:
        images, tables = forms[0]
        shown = slack_excerpts.with_tables(slack_charts.shown(blocks, images), tables)
        try:
            web.chat_update(channel=conv.slack_channel, ts=conv.slack_message_ts, text=said, blocks=shown)
            break
        except SlackApiError as error:
            wait = retry_after(error)
            if wait and waited < 300:
                # Why: une limite de débit n'est pas un refus de la forme ; la même repart après le délai demandé.
                waited += wait
                time.sleep(wait)
                continue
            if wait:
                # Why: jamais de réponse perdue pour une limite : le message reste à compléter, au prochain démarrage.
                logger.warning("Réponse de la conversation %s en attente : Slack limite le débit", conv_id)
                return
            forms = forms[1:]
            logger.warning(
                "Réponse Slack refusée (tableau : %s, image : %s) : %s", tables, images, error.response.get("error")
            )
        except (SlackClientError, OSError) as error:
            unreachable += 1
            logger.warning("Réponse Slack non posée, Slack injoignable : %s", error)
            if unreachable > 1:
                forms = []
            else:
                time.sleep(5)
    if not forms:
        logger.warning("Réponse de la conversation %s abandonnée dans Slack", conv_id)
    # Why: une mention arrivée pendant l'envoi a pu poser son propre message ; seul celui qu'on vient de compléter s'oublie.
    store.clear_slack_message(conv_id, conv.slack_message_ts)


def open_live(web: WebClient, conv_id: str, note: str = "") -> None:
    """Pose dans le fil le message qui vivra le temps du tour, et le retient pour le compléter."""
    conv = store.get_conversation(conv_id, include_messages=False)
    posted = web.chat_postMessage(
        channel=conv.slack_channel, thread_ts=conv.slack_thread_ts, **live(conv_id, VERBS[0], note)
    )
    # Why: écrire à une personne ouvre un message direct, dont Slack rend le canal ; lui seul sert à compléter.
    store.update_conversation(
        conv_id, slack_channel=posted.get("channel") or conv.slack_channel, slack_message_ts=posted["ts"]
    )


def say(web: WebClient, conv: Conversation, verb: str, note: str) -> int:
    """Change le verbe du message qui vit ; rend les secondes à laisser passer si Slack limite le débit."""
    try:
        web.chat_update(channel=conv.slack_channel, ts=conv.slack_message_ts, **live(conv.id, verb, note))
    except SlackApiError as error:
        logger.info("Verbe du message Slack non changé : %s", error.response.get("error"))
        return retry_after(error)
    except (SlackClientError, OSError) as error:
        logger.info("Verbe du message Slack non changé, Slack injoignable : %s", error)
    return 0


def next_turn(web: WebClient, conv_id: str, question_id: int, latest: int) -> None:
    """Un tour a succédé à celui qu'on suivait : celui-ci a sa réponse ; le suivant son message s'il vient de Slack."""
    finish(web, conv_id, question_id)
    # Why: un message écrit sur la page pendant un tour venu de Slack a sa réponse sur la page, pas dans le fil.
    if not store.slack_contexts(conv_id, latest):
        return
    try:
        open_live(web, conv_id, turn_note(conv_id, latest))
    except SlackApiError as error:
        logger.warning("Message Slack du tour suivant non posé : %s", error.response.get("error"))
    except (SlackClientError, OSError) as error:
        logger.warning("Message Slack du tour suivant non posé, Slack injoignable : %s", error)


def orphaned(web: WebClient, channel: str, message_ts: str) -> None:
    """Dit, dans le message resté sur un verbe, que sa conversation a été supprimée."""
    said = "Cette conversation a été supprimée dans Autometa."
    try:
        web.chat_update(channel=channel, ts=message_ts, text=said, blocks=[])
    except SlackApiError as error:
        logger.warning("Message Slack d'une conversation supprimée non complété : %s", error.response.get("error"))
    except (SlackClientError, OSError) as error:
        logger.warning("Message Slack d'une conversation supprimée non complété, Slack injoignable : %s", error)


async def watch(web: WebClient, conv_id: str, renew) -> None:
    """Suit les tours d'une conversation jusqu'à ce qu'aucun ne tourne : verbes, réponses, messages des suivants."""
    question = await asyncio.to_thread(store.last_user_message_id, conv_id)
    note = await asyncio.to_thread(turn_note, conv_id, question)
    pubsub, where = None, None
    try:
        # Why: s'abonner avant de lire l'état — un tour fini entre les deux n'enverrait son signal à personne.
        pubsub = await runner.subscribe(conv_id)
    except (RedisError, OSError) as error:
        logger.warning("Suivi Slack de %s sans signal, par sondage : %s", conv_id, error)
    try:
        began, changed, quiet, verb, heard = time.monotonic(), time.monotonic(), 0.0, VERBS[0], None
        while time.monotonic() - began < 7200:
            try:
                conv = await asyncio.to_thread(store.get_conversation, conv_id, False)
                latest = await asyncio.to_thread(store.last_user_message_id, conv_id)
            except SQLAlchemyError as error:
                logger.warning("Suivi Slack de %s : base illisible, nouvel essai : %s", conv_id, error)
                await asyncio.sleep(10)
                continue
            if not conv:
                # Why: une conversation supprimée pendant son tour ne laisse pas son message sur un verbe.
                if where:
                    await asyncio.to_thread(orphaned, web, *where)
                return
            where = (conv.slack_channel, conv.slack_message_ts) if conv.slack_message_ts else where
            # Why: l'état en base fait foi, pas le signal reçu : un signal peut manquer, ou dater d'un tour passé.
            if latest != question:
                await asyncio.to_thread(next_turn, web, conv_id, question, latest)
                question, note = latest, await asyncio.to_thread(turn_note, conv_id, latest)
                continue
            if not conv.needs_response:
                break
            moved = heard is not None and heard["data"] == "update"
            if moved and conv.slack_message_ts and time.monotonic() - changed >= 4 and time.monotonic() >= quiet:
                # Why: le verbe ne change que si l'agent avance, pas plus d'une fois toutes les 4 secondes, et
                # jamais tant que Slack demande d'attendre : ce débit doit rester à la réponse finale.
                changed, verb = time.monotonic(), random.choice([v for v in VERBS if v != verb])
                quiet = time.monotonic() + await asyncio.to_thread(say, web, conv, verb, note)
            await renew()
            try:
                if pubsub:
                    heard = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
                else:
                    heard = await asyncio.sleep(10)
            except (RedisError, OSError) as error:
                logger.warning("Suivi Slack de %s : signal perdu, suite par sondage : %s", conv_id, error)
                pubsub, heard = None, None
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe()
                await pubsub.aclose()
            except (RedisError, OSError) as error:
                logger.info("Abonnement Slack de %s non fermé : %s", conv_id, error)
    await asyncio.to_thread(finish, web, conv_id, question)
    await asyncio.to_thread(give_back, web, conv_id)


async def follow(web: WebClient, conv_id: str) -> None:
    """Suit une conversation, dans un seul processus à la fois, tant qu'un tour venu de Slack y attend sa réponse."""
    following[conv_id] = asyncio.current_task()
    key, token, held = f"autometa:slack:follow:{conv_id}", uuid.uuid4().hex, False

    async def renew() -> None:
        try:
            await (await get_redis()).expire(key, 90)
        except (RedisError, OSError) as error:
            logger.info("Verrou du suivi Slack de %s non prolongé : %s", conv_id, error)

    try:
        try:
            # Why: plusieurs processus du serveur reprendraient chacun les mêmes messages ; un verrou court, prolongé
            # tant que le suivi vit, en laisse un seul, et se libère de lui-même s'il meurt.
            held = bool(await (await get_redis()).set(key, token, nx=True, ex=90))
        except (RedisError, OSError) as error:
            logger.warning("Suivi Slack de %s sans verrou : %s", conv_id, error)
            held = True
        left = None
        while held:
            await watch(web, conv_id, renew)
            # Why: une mention arrivée pendant que la réponse partait a posé un message que personne ne suit encore ;
            # un message que Slack n'a pas laissé compléter n'est repris qu'une fois, le reste attend un redémarrage.
            conv = await asyncio.to_thread(store.get_conversation, conv_id, False)
            if not conv or conv.slack_message_ts in (None, left):
                break
            left = conv.slack_message_ts
    finally:
        following.pop(conv_id, None)
        if held:
            try:
                redis = await get_redis()
                if await redis.get(key) == token:
                    await redis.delete(key)
            except (RedisError, OSError) as error:
                logger.info("Verrou du suivi Slack de %s non rendu : %s", conv_id, error)


def give_back(web: WebClient, conv_id: str) -> None:
    """Dit dans le fil que les mentions restées en attente d'un tour qui n'a pas abouti ne sont pas parties."""
    left = [entry for entry in store.pending_messages(conv_id) if entry.get("slack") and entry["status"] == "returned"]
    if not left:
        return
    for entry in left:
        store.take_queued(conv_id, entry["id"], slack=True)
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
    try:
        # Why: le lien du fil d'une conversation demande l'adresse de l'espace Slack, dès le démarrage.
        await asyncio.to_thread(introduce, web)
    except SlackApiError as error:
        logger.warning("Espace Slack non lu au démarrage : %s", error.response.get("error"))
    except (SlackClientError, OSError) as error:
        logger.warning("Espace Slack non lu au démarrage, Slack injoignable : %s", error)
    for conv_id in await asyncio.to_thread(store.slack_live_conversations):
        if conv_id not in following:
            following[conv_id] = asyncio.get_running_loop().create_task(follow(web, conv_id))
            following[conv_id].add_done_callback(reported)


def whisper(web: WebClient, channel: str, user: str, thread_ts: str | None, said: str) -> None:
    """Dit quelque chose à une seule personne : dans le canal si le bot y est, sinon en message direct."""
    try:
        try:
            web.chat_postEphemeral(channel=channel, user=user, thread_ts=thread_ts, text=said)
        except SlackApiError:
            # Why: Slack ne laisse écrire à une seule personne que dans un canal où est le bot ; ailleurs, en direct.
            web.chat_postMessage(channel=user, text=said)
    except SlackApiError as error:
        logger.warning("Mot à %s non remis : %s", user, error.response.get("error"))
    except (SlackClientError, OSError) as error:
        logger.warning("Mot à %s non remis, Slack injoignable : %s", user, error)


def thread_of(web: WebClient, event: dict, conv_id: str | None, shared: bool) -> str:
    """Le fil gardé avec une demande : ses messages depuis la demande précédente, ce qui n'a pas été repris, et jusqu'où."""
    channel, chosen = event["channel"], event.get("chosen")
    thread_ts = event.get("thread_ts") or event["ts"]
    # Why: une mention s'arrête à elle-même ; le raccourci, qui n'a pas de message à lui, à maintenant.
    through = f"{time.time():.6f}" if chosen else event["ts"]
    conv = store.get_conversation(conv_id, include_messages=False) if conv_id else None
    waiting = [e["slack"] for e in (conv.pending_messages if conv else []) if e.get("slack")]
    # Why: le fil repris part de la dernière demande acceptée, mention ou raccourci, en attente comprise ; une
    # mention refusée ou celle d'un autre bot n'en est pas une.
    kept = [*(store.slack_contexts(conv_id) if conv_id else []), *waiting]
    after = max((float(json.loads(held).get("through") or 0) for held in kept), default=0.0)
    thread, away = [], False
    try:
        thread = replies(web, channel, thread_ts) if shared else []
    except SlackApiError:
        if not chosen:
            raise
        # Why: le raccourci marche aussi là où le bot n'est pas ; Slack ne lui laisse alors pas lire le fil.
        away = True
    messages, left_out = thread_context(web, thread, after, float("inf") if chosen else float(through))
    notes = [AWAY if away else "" if shared else PRIVATE]
    if chosen:
        whole = next((m for m in thread if m.get("ts") == chosen["ts"]), None)
        picked = said_by(web, whole or chosen)
        left_out += picked is None and whole is None
        messages = sorted(
            [*(m for m in messages if m["ts"] != chosen["ts"]), *([picked] if picked else [])], key=by_time
        )
        notes += (
            ["Le message choisi, trop long, n'a été repris qu'en partie."] if chosen.get("cut") and not whole else []
        )
    plural = "s" if left_out > 1 else ""
    left = f"{left_out} message{plural} d'invités ou de personnes extérieures non repris" if left_out else ""
    note = " ".join(part for part in notes if part)
    return json.dumps({"messages": messages, "note": note, "left_out": left, "through": through}, ensure_ascii=False)


def begin(web: WebClient, event: dict) -> tuple[str, str | None, str] | None:
    """Ouvre ou reprend la conversation d'une demande : son identifiant, la demande (None en file d'attente), pour qui."""
    channel, asker, said, chosen = event["channel"], event["user"], event.get("text", ""), event.get("chosen")
    thread_ts = event.get("thread_ts") or event["ts"]
    try:
        who = person(web, asker)
    except SlackApiError as error:
        logger.info("Demandeur Slack %s inconnu de Slack : %s", asker, error.response.get("error"))
        who = None
    if not who or not admitted(who):
        whisper(web, channel, asker, event.get("thread_ts"), REFUSAL.format(config.BASE_URL))
        logger.info("Demande Slack refusée : %s n'est pas admis", asker)
        return None
    existing = store.slack_conversation(channel, thread_ts)
    kept = thread_of(web, event, existing, public(web, channel, event.get("channel_type")))
    request = readable(web, said.replace(f"<@{workspace['bot']}>", "")).strip() or "(demande sans texte)"
    conv_id, created = (
        (existing, False) if existing else store.slack_thread_conversation(channel, thread_ts, who["email"])
    )
    conv = store.get_conversation(conv_id, include_messages=False)
    if who["email"] != (conv.user_id or "").lower():
        # Why: une relance d'une autre personne entre dans la conversation de la première, sous son propre nom.
        request = f"{who['name']} : {request}"
    waiting = [e for e in conv.pending_messages if e["status"] == "waiting"]
    held = slack_context.merged([*(e["slack"] for e in waiting if e.get("slack")), kept])
    # Why: la demande part vers l'agent en un seul argument de commande, que Linux borne à 128 Kio ; un fil trop
    # long pour y tenir le dit, plutôt que d'échouer plus loin sans raison lisible.
    if len(slack_context.prompt(held, request).encode()) > 100_000:
        whisper(
            web,
            channel,
            asker,
            thread_ts,
            "Ce fil est trop long pour que je le reprenne en entier : je ne peux pas y répondre.",
        )
        if created:
            store.delete_conversation(conv_id)
        return None
    if store.start_turn(conv_id, request) is None:
        # Why: comme sur la page, des demandes en attente trop longues seraient coupées au rattrapage sans le dire.
        if sum(len(e["content"]) for e in waiting) + len(request) > 20_000:
            whisper(web, channel, asker, thread_ts, "Trop de demandes attendent déjà la fin de la réponse en cours.")
            return None
        if store.queue_message(conv_id, request, kept) is not None:
            whisper(web, channel, asker, thread_ts, "Autometa finit sa réponse en cours, puis prendra votre demande.")
            return conv_id, None, conv.user_id
        # Why: le tour s'est fini entre les deux ; la demande ouvre le suivant.
        if store.start_turn(conv_id, request) is None:
            whisper(web, channel, asker, thread_ts, "Je n'ai pas pu prendre votre demande : redemandez-moi.")
            return None
    store.add_message(conv_id, "slack_context", kept)
    note = json.loads(kept)["note"]
    try:
        try:
            open_live(web, conv_id, note)
        except SlackApiError:
            if not (chosen and created):
                raise
            # Why: par le raccourci, là où le bot ne peut pas écrire, la réponse va à la seule personne qui a
            # demandé, en message direct ; la conversation, neuve, suit alors ce message.
            store.update_conversation(conv_id, slack_channel=asker, slack_thread_ts=None)
            open_live(web, conv_id, note or AWAY)
    except SlackApiError, SlackClientError, OSError:
        # Why: sans son message dans Slack, la demande n'a pas commencé : le tour est rendu, et une conversation
        # neuve ne reste pas ; une conversation déjà là garde son fil.
        store.end_turn(conv_id, False)
        if created:
            store.delete_conversation(conv_id)
        else:
            whisper(web, channel, asker, None, "Je ne peux plus écrire dans ce fil : votre demande n'est pas partie.")
        raise
    if created:
        generate_conversation_title(request, conv_id)
        generate_conversation_tags(request, conv_id)
    return conv_id, slack_context.prompt(kept, request), conv.user_id


async def first_delivery(event: dict) -> bool:
    """Vrai la première fois que cette mention arrive : Slack peut la livrer deux fois, ou à deux processus."""
    try:
        key = f"autometa:slack:seen:{event['channel']}:{event['ts']}"
        return bool(await (await get_redis()).set(key, "1", nx=True, ex=600))
    except (RedisError, OSError) as error:
        logger.warning("Mention Slack non dédoublonnée : %s", error)
        return True


async def asked(web: WebClient, event: dict) -> None:
    """Une demande, hors des fils qui accusent réception à Slack : la conversation, son tour, puis son suivi."""
    # Why: chaque validation de la fenêtre du raccourci est une demande ; seule une mention peut arriver deux fois.
    if not event.get("chosen") and not await first_delivery(event):
        return
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


def remembered(message: dict, channel: dict) -> str:
    """Ce que la fenêtre du raccourci retient du message choisi, dans les 3 000 caractères que Slack lui laisse."""
    text = message.get("text") or ""
    hints = {"directmessage": "im", "privategroup": "group"}
    kept = {
        "channel": channel.get("id"),
        "channel_type": hints.get(channel.get("name")),
        "thread_ts": message.get("thread_ts") or message.get("ts"),
        "chosen": {"user": message.get("user"), "ts": message.get("ts"), "text": text, "cut": False},
    }
    # Why: le texte n'est gardé que pour un canal où le bot ne pourra pas le relire ; coupé à ce qui tient, à sa
    # longueur une fois écrite, et la demande le dira.
    while len(json.dumps(kept, ensure_ascii=False)) > 2900:
        text = text[: len(text) - max(100, len(text) // 10)]
        kept["chosen"] |= {"text": text, "cut": True}
    return json.dumps(kept, ensure_ascii=False)


def shortcut(web: WebClient, payload: dict) -> None:
    """Le raccourci « Demander à Autometa » d'un message : ouvre la fenêtre de la question, puis la joue."""
    if payload.get("type") == "message_action":
        field = {"type": "plain_text_input", "action_id": "text", "multiline": True}
        view = {
            "type": "modal",
            "callback_id": SHORTCUT,
            "private_metadata": remembered(payload.get("message") or {}, payload.get("channel") or {}),
            "title": {"type": "plain_text", "text": "Demander à Autometa"},
            "submit": {"type": "plain_text", "text": "Demander"},
            "close": {"type": "plain_text", "text": "Annuler"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "question",
                    "label": {"type": "plain_text", "text": "Votre question"},
                    "element": field,
                }
            ],
        }
        try:
            web.views_open(trigger_id=payload.get("trigger_id"), view=view)
        except SlackApiError as error:
            logger.warning("Fenêtre du raccourci Slack non ouverte : %s", error.response.get("error"))
        except (SlackClientError, OSError) as error:
            logger.warning("Fenêtre du raccourci Slack non ouverte, Slack injoignable : %s", error)
    elif payload.get("type") == "view_submission" and workspace["loop"]:
        view = payload.get("view") or {}
        typed = (((view.get("state") or {}).get("values") or {}).get("question") or {}).get("text") or {}
        event = {
            **json.loads(view.get("private_metadata") or "{}"),
            "user": (payload.get("user") or {}).get("id"),
            "text": typed.get("value") or "",
        }
        event["ts"] = event["chosen"]["ts"]
        asyncio.run_coroutine_threadsafe(asked(web, event), workspace["loop"]).add_done_callback(reported)
