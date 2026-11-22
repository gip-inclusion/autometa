"""Faux Slack et faux magasin des tests de « Demander à Autometa » : assez fidèles pour jouer un fil entier."""

import json
from dataclasses import replace

from slack_sdk.errors import SlackApiError

from web import config, slack_ask, slack_context
from web.stores.records import Conversation

BASE = "https://autometa.example"
BOT = "U0BOT"
CHANNEL = "C0TEST"
OWNER = "camille.martin@inclusion.gouv.fr"
PEOPLE = {
    "U1": {"real_name": "Camille Martin", "profile": {"email": "Camille.Martin@inclusion.gouv.fr", "display_name": ""}},
    "U2": {"real_name": "Louis", "profile": {"email": "louis@ailleurs.example", "display_name": "Louis D."}},
    "U3": {"real_name": "Invitée", "is_restricted": True, "profile": {"email": "x@inclusion.gouv.fr"}},
    "U4": {"real_name": "Externe", "is_stranger": True, "profile": {}},
    "U5": {"real_name": "Noa", "profile": {"email": "noa@inclusion.gouv.fr", "display_name": "Noa"}},
    "U6": {"real_name": "Admin", "profile": {"email": "admin@inclusion.gouv.fr", "display_name": "Admin"}},
    BOT: {"real_name": "Autometa", "is_bot": True, "profile": {}},
}


def refused(mocker, error="not_in_channel", retry_after=None):
    response = mocker.MagicMock(get={"error": error}.get)
    response.headers = {"Retry-After": retry_after} if retry_after else {}
    return SlackApiError("refused", response)


def reply(user, text, ts, **more):
    return {"user": user, "text": text, "ts": ts, **more}


def slack(mocker, replies=(), info=None):
    """Un Slack qui connaît quelques personnes, un fil, un canal public, et poste des messages numérotés."""
    web = mocker.MagicMock()

    def users_info(user):
        if user not in PEOPLE:
            raise refused(mocker, "user_not_found")
        return {"user": PEOPLE[user]}

    posted = iter(range(1, 100))
    web.users_info.side_effect = users_info
    web.conversations_replies.return_value = {"messages": list(replies)}
    web.conversations_info.return_value = {"channel": info or {"is_channel": True, "is_private": False}}
    web.chat_postMessage.side_effect = lambda **given: {
        "channel": given["channel"],
        "ts": f"17000009{next(posted):02d}.0",
    }
    return web


class Store:
    """Le magasin en mémoire : une conversation par fil, ses messages, sa file, son tour, comme le vrai."""

    def __init__(self, owners=()):
        self.convs, self.messages, self.owners, self.ids = {}, {}, set(owners), iter(range(1, 1000))
        self.spellings = {}

    def owns_conversations(self, user_id):
        return user_id in self.owners

    def slack_conversation(self, channel, thread_ts):
        found = [c.id for c in self.convs.values() if (c.slack_channel, c.slack_thread_ts) == (channel, thread_ts)]
        return found[0] if found else None

    def slack_thread_conversation(self, channel, thread_ts, user_id):
        existing = self.slack_conversation(channel, thread_ts)
        if existing:
            return existing, False
        conv_id = f"conv{len(self.convs) + 1:04d}"
        self.convs[conv_id] = Conversation(
            id=conv_id, user_id=user_id, origin="slack", slack_channel=channel, slack_thread_ts=thread_ts
        )
        self.messages[conv_id] = []
        return conv_id, True

    def get_conversation(self, conv_id, include_messages=True):
        return self.convs.get(conv_id)

    def update_conversation(self, conv_id, **fields):
        self.convs[conv_id] = replace(self.convs[conv_id], **fields)

    def delete_conversation(self, conv_id):
        self.convs.pop(conv_id, None)

    def add_message(self, conv_id, kind, content):
        self.messages[conv_id].append((next(self.ids), kind, content))
        return self.messages[conv_id][-1][0]

    def author_of(self, conv_id, entry=None):
        conv = self.convs[conv_id]
        return ((entry.get("author") if entry else conv.turn_user) or conv.user_id or "").lower()

    def shut_out(self, conv_id, author):
        conv = self.convs[conv_id]
        return bool(conv.slack_locked and author and author.lower() != (conv.user_id or "").lower())

    def owner_spelling(self, email):
        return self.spellings.get(email.lower(), email)

    def start_turn(self, conv_id, content, author=None):
        conv = self.convs[conv_id]
        if conv.needs_response or self.shut_out(conv_id, author):
            return None
        locked = conv.slack_locked or (conv.origin == "slack" and author is None)
        self.update_conversation(conv_id, needs_response=True, turn_user=author, slack_locked=locked)
        return self.add_message(conv_id, "user", content)

    def queue_message(self, conv_id, content, **slack):
        conv = self.convs[conv_id]
        waiting = [e for e in conv.pending_messages if e["status"] == "waiting"]
        if not (conv.needs_response or (slack and waiting)) or self.shut_out(conv_id, slack.get("author")):
            return None
        entry = {"id": f"e{next(self.ids)}", "content": content, "status": "waiting", **slack}
        locked = conv.slack_locked or (conv.origin == "slack" and not slack)
        self.update_conversation(conv_id, pending_messages=[*conv.pending_messages, entry], slack_locked=locked)
        return [e for e in self.convs[conv_id].pending_messages if not e.get("slack")]

    def first_group(self, conv_id):
        pending = self.convs[conv_id].pending_messages
        waiting = [e for e in pending if e["status"] == "waiting" and not self.shut_out(conv_id, e.get("author"))]
        return [e for e in waiting if self.author_of(conv_id, e) == self.author_of(conv_id, waiting[0])]

    def leave(self, conv_id, group):
        kept = [e for e in self.convs[conv_id].pending_messages if e not in group]
        self.update_conversation(conv_id, pending_messages=kept)
        sent = [self.add_message(conv_id, "user", entry["content"]) for entry in group]
        threads = [e["slack"] for e in group if e.get("slack")]
        if not threads:
            return sent, group[-1]["content"], False
        self.add_message(conv_id, "slack_context", slack_context.merged(threads))
        return sent, slack_context.prompt(slack_context.merged(threads), group[-1]["content"]), True

    def end_turn(self, conv_id, flush):
        conv = self.convs[conv_id]
        group = self.first_group(conv_id)
        if flush and group and self.author_of(conv_id, group[0]) == self.author_of(conv_id):
            return self.leave(conv_id, group)[0]
        if not (flush and group):
            returned = [{**e, "status": "returned"} for e in conv.pending_messages]
            self.update_conversation(conv_id, pending_messages=returned)
        self.update_conversation(conv_id, needs_response=False)
        return []

    def next_turn(self, conv_id):
        group = self.first_group(conv_id) if conv_id in self.convs else []
        if not group or self.convs[conv_id].needs_response:
            return None
        self.update_conversation(conv_id, needs_response=True, turn_user=group[0].get("author"))
        sent, asked, from_slack = self.leave(conv_id, group)
        return sent[-1], asked, group[0].get("author") or self.convs[conv_id].user_id, from_slack

    def turned_away(self, conv_id):
        conv = self.convs[conv_id]
        if not conv.slack_locked:
            return []
        others = [e for e in conv.pending_messages if e.get("slack") and e.get("author") != conv.user_id]
        self.update_conversation(conv_id, pending_messages=[e for e in conv.pending_messages if e not in others])
        return others

    def pending_messages(self, conv_id):
        return self.convs[conv_id].pending_messages

    def take_queued(self, conv_id, entry_id, slack=False):
        kept = [e for e in self.convs[conv_id].pending_messages if e["id"] != entry_id]
        self.update_conversation(conv_id, pending_messages=kept)

    def slack_contexts(self, conv_id, since=0):
        return [
            content for n, kind, content in self.messages.get(conv_id, []) if kind == "slack_context" and n >= since
        ]

    def clear_slack_message(self, conv_id, message_ts):
        if conv_id in self.convs and self.convs[conv_id].slack_message_ts == message_ts:
            self.update_conversation(conv_id, slack_message_ts=None)
            return True
        return False

    def last_user_message_id(self, conv_id):
        return max((n for n, kind, _ in self.messages.get(conv_id, []) if kind == "user"), default=0)

    def get_thread_messages(self, conv_id, since=0):
        return [m for m in self.messages.get(conv_id, []) if m[0] >= since]

    def slack_live_conversations(self):
        return [
            c.id
            for c in self.convs.values()
            if c.slack_message_ts or [e for e in c.pending_messages if e["status"] == "waiting"]
        ]

    def thread(self, conv_id):
        """Le dernier fil gardé par la conversation, lu."""
        return json.loads(self.slack_contexts(conv_id)[-1])


class Signals:
    """Le signal de la conversation tel que le flux de la page le reçoit : une suite de messages, puis le silence."""

    def __init__(self, *heard):
        self.heard, self.closed = list(heard), False

    async def get_message(self, **given):
        step = self.heard.pop(0) if self.heard else None
        if callable(step):
            step = step()
        return {"data": step} if step else None

    async def unsubscribe(self):
        self.closed = True

    async def aclose(self):
        self.closed = True


class Redis:
    """Un Redis qui ne sait que poser une clé si elle manque, la lire, la prolonger, la retirer."""

    def __init__(self):
        self.keys = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.keys:
            return None
        self.keys[key] = value
        return True

    async def get(self, key):
        return self.keys.get(key)

    async def expire(self, key, seconds):
        return key in self.keys

    async def delete(self, key):
        self.keys.pop(key, None)


def instance(mocker, monkeypatch):
    """Une instance qui écoute, un magasin vide, un moteur et un Redis factices."""
    monkeypatch.setattr(config, "BASE_URL", BASE)
    monkeypatch.setattr(config, "SLACK_CHART_IMAGES", False)
    monkeypatch.setattr(
        slack_ask, "workspace", {"url": "https://equipe.slack.com/", "bot": BOT, "bot_id": "B0BOT", "loop": None}
    )
    mocker.patch.object(slack_ask.uploads, "upload_file")
    monkeypatch.setattr(slack_ask, "people", {})
    monkeypatch.setattr(slack_ask, "following", {})
    mocker.patch.object(slack_ask.time, "sleep")
    mocker.patch.object(slack_ask.asyncio, "sleep", mocker.AsyncMock(return_value=None))
    mocker.patch.object(slack_ask, "generate_conversation_title")
    mocker.patch.object(slack_ask, "generate_conversation_tags")
    store = mocker.patch.object(slack_ask, "store", Store())
    runner = mocker.patch.object(slack_ask, "runner")
    runner.submit, runner.notify = mocker.AsyncMock(), mocker.AsyncMock()
    runner.subscribe, runner.is_done = mocker.AsyncMock(return_value=Signals()), mocker.AsyncMock(return_value=False)
    redis = Redis()
    mocker.patch.object(slack_ask, "get_redis", mocker.AsyncMock(return_value=redis))
    return mocker.MagicMock(store=store, runner=runner, redis=redis)
