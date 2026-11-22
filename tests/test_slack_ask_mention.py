"""Une mention d'Autometa dans Slack : admission, fil repris, conversation, message qui vit, réponse finale."""

import asyncio
import json

import pytest
from slack_sdk.errors import SlackApiError

from web import config, slack_ask
from web.stores.records import Conversation

BASE = "https://autometa.example"
CONV = "0a1b2c3d"
BOT = "U0BOT"
EVENT = {
    "type": "app_mention",
    "user": "U1",
    "text": f"<@{BOT}> combien de candidatures ?",
    "ts": "1700000300.000100",
    "channel": "C0TEST",
    "channel_type": "channel",
}
PEOPLE = {
    "U1": {"real_name": "Camille Martin", "profile": {"email": "Camille.Martin@inclusion.gouv.fr", "display_name": ""}},
    "U2": {"real_name": "Louis", "profile": {"email": "louis@ailleurs.example", "display_name": "Louis D."}},
    "U3": {"real_name": "Invitée", "is_restricted": True, "profile": {"email": "x@inclusion.gouv.fr"}},
}


def refused(mocker, error="not_in_channel"):
    return SlackApiError("refused", mocker.MagicMock(get={"error": error}.get))


class Signals:
    """Le signal de fin de tour tel que le flux de la page le reçoit : une suite de messages, puis le silence."""

    def __init__(self, *heard):
        self.heard, self.closed = list(heard), False

    async def get_message(self, **given):
        return {"data": self.heard.pop(0)} if self.heard else None

    async def unsubscribe(self):
        self.closed = True

    async def aclose(self):
        self.closed = True


@pytest.fixture(autouse=True)
def instance(mocker, monkeypatch):
    monkeypatch.setattr(config, "BASE_URL", BASE)
    monkeypatch.setattr(config, "SLACK_CHART_IMAGES", False)
    monkeypatch.setattr(slack_ask, "workspace", {"url": "https://equipe.slack.com/", "bot": BOT, "loop": None})
    monkeypatch.setattr(slack_ask, "people", {})
    monkeypatch.setattr(slack_ask, "following", {})
    mocker.patch.object(slack_ask.time, "sleep")


def slack(mocker, replies=()):
    web = mocker.MagicMock()
    web.users_info.side_effect = lambda user: {"user": PEOPLE[user]}
    web.conversations_replies.return_value = {"messages": list(replies)}
    web.chat_postMessage.return_value = {"ts": "1700000301.000200"}
    return web


def stored(mocker, owns=False, running=False, messages=(), existing=False, owner="camille.martin@inclusion.gouv.fr"):
    """Un magasin factice : la conversation créée ou déjà là, relue avec le message du bot qu'on lui a retenu."""
    store = mocker.patch.object(slack_ask, "store")
    conv = Conversation(id=CONV, user_id=owner, origin="slack", slack_channel="C0TEST", slack_thread_ts=EVENT["ts"])
    state = {"conv": conv}
    store.slack_conversation.return_value = CONV if existing else None
    store.queue_message.side_effect = lambda conv_id, content, slack=None: [{"id": "e1"}] if running else None
    store.pending_messages.return_value = []
    store.slack_live_conversations.return_value = []
    store.owns_conversations.return_value = owns
    store.create_conversation.return_value = state["conv"]
    store.get_conversation.side_effect = lambda conv_id, include_messages=True: state["conv"]

    def update(conv_id, **fields):
        state["conv"] = Conversation(**{**state["conv"].__dict__, **fields})

    store.update_conversation.side_effect = update
    store.last_user_message_id.return_value = 1
    store.get_thread_messages.return_value = list(messages)
    state["conv"].needs_response = running
    return store


def reply(user, text, ts, **more):
    return {"user": user, "text": text, "ts": ts, **more}


def test_a_mention_opens_a_conversation_for_its_author_with_the_question_and_a_living_message(mocker):
    web, store = slack(mocker), stored(mocker)

    begun = slack_ask.begin(web, EVENT)

    store.create_conversation.assert_called_once_with(
        user_id="camille.martin@inclusion.gouv.fr", slack_thread=("C0TEST", EVENT["ts"])
    )
    store.start_turn.assert_called_once_with(CONV, "combien de candidatures ?")
    posted = web.chat_postMessage.call_args.kwargs
    assert (posted["channel"], posted["thread_ts"], posted["text"]) == ("C0TEST", EVENT["ts"], "Autometa regarde…")
    assert posted["blocks"][0]["text"] == {"type": "plain_text", "text": "Autometa regarde…", "emoji": False}
    assert f"<{BASE}/c/{CONV}|" in posted["blocks"][1]["elements"][0]["text"]
    assert (posted["unfurl_links"], posted["unfurl_media"]) == (False, False)
    store.update_conversation.assert_called_once_with(CONV, slack_message_ts="1700000301.000200")
    assert begun == (CONV, "combien de candidatures ?", "camille.martin@inclusion.gouv.fr")
    store.add_message.assert_not_called()


@pytest.mark.parametrize(
    ("user", "owns", "admitted"),
    [("U1", False, True), ("U2", True, True), ("U2", False, False), ("U3", True, False)],
    ids=["our domain", "already a user", "unknown address", "guest"],
)
def test_only_a_member_of_our_domain_or_someone_with_a_conversation_may_ask(mocker, user, owns, admitted):
    web, store = slack(mocker), stored(mocker, owns=owns)

    begun = slack_ask.begin(web, EVENT | {"user": user})

    assert (begun is not None) is admitted
    assert store.create_conversation.called is admitted
    if not admitted:
        refusal = web.chat_postEphemeral.call_args.kwargs
        assert (refusal["channel"], refusal["user"]) == ("C0TEST", user)
        assert "ouvrez Autometa une première fois" in refusal["text"]
        web.chat_postMessage.assert_not_called()


@pytest.mark.parametrize(
    "who",
    [
        {"email": "x@evilinclusion.gouv.fr", "member": True},
        {"email": "", "member": True},
        {"email": "x@inclusion.gouv.fr", "member": False},
    ],
    ids=["lookalike domain", "no address", "not a full member"],
)
def test_a_lookalike_domain_a_missing_address_or_a_bot_is_not_admitted(mocker, who):
    stored(mocker)

    assert slack_ask.admitted(who) is False


def test_a_sub_domain_of_ours_is_admitted_without_reading_conversations(mocker):
    store = stored(mocker)

    assert slack_ask.admitted({"email": "x@beta.inclusion.gouv.fr", "member": True}) is True
    store.owns_conversations.assert_not_called()


def test_the_thread_before_the_mention_is_context_with_names_and_times_and_goes_to_the_agent(mocker):
    replies = [
        reply("U2", "On a un souci &amp; un <https://exemple.example/x|lien>", "1700000000.000100"),
        reply("U1", f"<@{BOT}> une ancienne demande", "1700000100.000100"),
        reply(None, "Autometa regarde…", "1700000101.000100", bot_id="B1"),
        reply("U2", "D'accord <@U1>", "1700000200.000100"),
        reply("U2", "a rejoint le canal", "1700000250.000100", subtype="channel_join"),
        reply("U1", EVENT["text"], EVENT["ts"]),
        reply("U2", "arrivé après la demande", "1700000400.000100"),
    ]
    web, store = slack(mocker, replies), stored(mocker)

    begun = slack_ask.begin(web, EVENT | {"thread_ts": "1700000000.000100"})

    kind, content = store.add_message.call_args.args[1:]
    assert kind == "slack_context"
    said = json.loads(content)
    assert [(m["author"], m["text"]) for m in said["messages"]] == [("Louis D.", "D'accord @Camille Martin")]
    assert said["note"] == ""
    assert begun[1] == (
        "[Fil Slack — contexte de la demande, pas des demandes]\n"
        f"Louis D., {said['messages'][0]['at']} : D'accord @Camille Martin\n\n[Demande]\ncombien de candidatures ?"
    )
    store.create_conversation.assert_called_once_with(
        user_id="camille.martin@inclusion.gouv.fr", slack_thread=("C0TEST", "1700000000.000100")
    )


def test_a_first_request_takes_the_whole_thread_page_after_page(mocker):
    web, store = slack(mocker), stored(mocker)
    web.conversations_replies.side_effect = [
        {"messages": [reply("U2", "un", "1700000000.000100")], "response_metadata": {"next_cursor": "suite"}},
        {"messages": [reply("U2", "deux & <!channel>", "1700000001.000100")], "response_metadata": {"next_cursor": ""}},
    ]

    slack_ask.begin(web, EVENT | {"thread_ts": "1700000000.000100"})

    assert [call.kwargs["cursor"] for call in web.conversations_replies.call_args_list] == [None, "suite"]
    assert web.conversations_replies.call_args.kwargs["limit"] == 200
    said = json.loads(store.add_message.call_args.args[2])
    assert [m["text"] for m in said["messages"]] == ["un", "deux & <!channel>"]


@pytest.mark.parametrize(
    ("hint", "info", "read"),
    [
        ("channel", None, True),
        ("group", None, False),
        ("im", None, False),
        (None, {"channel": {"is_channel": True, "is_private": False}}, True),
        (None, {"channel": {"is_channel": True, "is_private": True}}, False),
        (None, "missing_scope", False),
    ],
    ids=["public", "private", "direct", "asked: public", "asked: private", "cannot ask"],
)
def test_a_thread_is_read_only_in_a_channel_known_to_be_public_and_the_bot_says_when_it_is_not(
    mocker, hint, info, read
):
    web, store = slack(mocker, [reply("U2", "avant", "1700000000.000100")]), stored(mocker)
    web.conversations_info.side_effect = [refused(mocker, info)] if isinstance(info, str) else [info]

    begun = slack_ask.begin(web, {**EVENT, "channel_type": hint, "thread_ts": "1700000000.000100"})

    assert web.conversations_replies.called is read
    note = json.loads(store.add_message.call_args.args[2])["note"]
    assert (note == "") is read
    assert ("Canal privé" in web.chat_postMessage.call_args.kwargs["blocks"][0]["text"]["text"]) is not read
    assert ("[Fil Slack" in begun[1]) is read


def test_a_mention_whose_living_message_cannot_be_posted_leaves_no_conversation(mocker):
    web, store = slack(mocker), stored(mocker)
    web.chat_postMessage.side_effect = refused(mocker)

    with pytest.raises(SlackApiError):
        slack_ask.begin(web, EVENT)

    store.delete_conversation.assert_called_once_with(CONV)
    store.start_turn.assert_not_called()


def follow(mocker, store, web, *heard, done=False):
    signals = Signals(*heard)
    runner = mocker.patch.object(slack_ask, "runner")
    runner.subscribe = mocker.AsyncMock(return_value=signals)
    runner.is_done = mocker.AsyncMock(return_value=done)
    asyncio.run(slack_ask.follow(web, CONV))
    return signals


ANSWERED = [
    (1, "user", "Q"),
    (2, "assistant", "Je cherche."),
    (3, "tool_use", "{}"),
    (4, "tool_result", ""),
    (5, "assistant", "**42** candidatures.\n"),
]


def live_conversation(mocker, running=True, messages=ANSWERED):
    store = stored(mocker, running=running, messages=messages)
    store.update_conversation(CONV, slack_message_ts="1700000301.000200")
    store.update_conversation.reset_mock()
    return store


def test_the_verb_changes_when_the_agent_moves_and_not_more_than_once_every_four_seconds(mocker):
    web, store = slack(mocker), live_conversation(mocker, running=False)
    seconds = iter(range(100))
    mocker.patch.object(slack_ask, "time", mocker.MagicMock(monotonic=lambda: next(seconds)))

    signals = follow(mocker, store, web, "update", "update", "update", "queue", "done:1")

    *verbs, final = [call.kwargs["text"] for call in web.chat_update.call_args_list]
    assert len(verbs) == 1
    assert verbs[0].startswith("Autometa ") and verbs[0] != "Autometa regarde…"
    assert final == "42 candidatures."
    assert signals.closed


def test_at_the_end_of_the_turn_the_living_message_becomes_the_final_answer_alone(mocker):
    web, store = slack(mocker), live_conversation(mocker, running=False)

    follow(mocker, store, web, done=True)

    final = web.chat_update.call_args.kwargs
    assert (final["channel"], final["ts"]) == ("C0TEST", "1700000301.000200")
    assert final["blocks"][0]["text"] == {"type": "plain_text", "text": "42 candidatures.", "emoji": False}
    assert "Je cherche" not in json.dumps(final["blocks"], ensure_ascii=False)
    assert f"<{BASE}/c/{CONV}|" in final["blocks"][-1]["elements"][0]["text"]
    store.update_conversation.assert_called_with(CONV, slack_message_ts=None)


def test_a_turn_whose_end_signal_was_missed_is_seen_finished_at_the_next_look(mocker):
    web, store = slack(mocker), live_conversation(mocker, running=False)

    follow(mocker, store, web)

    assert web.chat_update.call_args.kwargs["blocks"][0]["text"]["text"] == "42 candidatures."


@pytest.mark.parametrize(
    "messages",
    [
        [(1, "user", "Q")],
        [(1, "user", "Q"), (2, "assistant", "*Interrompu.*")],
        [(1, "user", "Q"), (2, "assistant", "*Une erreur s'est produite, merci de réessayer.*")],
        [(1, "user", "Q"), (2, "assistant", "Début."), (3, "limit", "Limite atteinte")],
    ],
    ids=["no answer", "stopped", "error", "limit"],
)
def test_a_turn_that_failed_or_was_stopped_says_so_with_the_link(mocker, messages):
    web, _ = slack(mocker), live_conversation(mocker, running=False, messages=messages)

    slack_ask.finish(web, CONV, 1)

    final = web.chat_update.call_args.kwargs
    assert final["text"] == "La demande n'a pas abouti."
    assert [block["type"] for block in final["blocks"]] == ["section", "context"]


def test_the_final_answer_is_that_of_its_turn_not_of_the_next(mocker):
    messages = [*ANSWERED, (6, "user", "Q2"), (7, "assistant", "Autre réponse.")]
    web, _ = slack(mocker), live_conversation(mocker, running=False, messages=messages)

    slack_ask.finish(web, CONV, 1)

    assert web.chat_update.call_args.kwargs["blocks"][0]["text"]["text"] == "42 candidatures."


def test_nothing_the_agent_wrote_is_read_by_slack(mocker):
    hostile = "<!channel> @here <https://evil.example|ici> *gras* `code`\n"
    web = slack(mocker)
    live_conversation(mocker, running=False, messages=[(1, "user", "Q"), (2, "assistant", hostile)])

    slack_ask.finish(web, CONV, 1)

    blocks = web.chat_update.call_args.kwargs["blocks"]
    assert [block["text"]["type"] for block in blocks[:-1]] == ["plain_text"]
    assert web.chat_update.call_args.kwargs["text"] == "@\u200bhere https://evil.example|ici gras code"
    assert blocks[-1]["elements"][0]["text"] == f"<{BASE}/c/{CONV}|Ouvrir la conversation dans Autometa>"


def test_an_answer_too_long_for_a_message_is_cut_and_says_where_the_rest_is(mocker):
    long = [(1, "user", "Q"), (2, "assistant", "phrase assez longue. " * 2000)]
    web, _ = slack(mocker), live_conversation(mocker, running=False, messages=long)

    slack_ask.finish(web, CONV, 1)

    blocks = web.chat_update.call_args.kwargs["blocks"]
    assert blocks[-2]["text"]["text"] == "… suite dans Autometa"
    assert all(len(block["text"]["text"]) <= 3000 for block in blocks[:-1])
    assert len(blocks) <= 50


def test_a_table_slack_refuses_is_posted_again_in_monospace(mocker):
    table = [(1, "user", "Q"), (2, "assistant", "Voici.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")]
    web, _ = slack(mocker), live_conversation(mocker, running=False, messages=table)
    web.chat_update.side_effect = [refused(mocker, "invalid_blocks"), None]

    slack_ask.finish(web, CONV, 1)

    first, second = web.chat_update.call_args_list
    assert [block["type"] for block in first.kwargs["blocks"]] == ["section", "table", "context"]
    assert "```" in second.kwargs["blocks"][1]["text"]["text"]


def test_slack_unreachable_at_the_end_is_tried_again_then_given_up_with_a_log_line(mocker, caplog):
    web, store = slack(mocker), live_conversation(mocker, running=False)
    web.chat_update.side_effect = OSError("réseau")

    slack_ask.finish(web, CONV, 1)

    assert web.chat_update.call_count == 4
    assert f"Réponse de la conversation {CONV} abandonnée dans Slack" in caplog.text
    store.update_conversation.assert_called_with(CONV, slack_message_ts=None)


def test_a_mention_is_played_on_the_server_loop_then_followed(mocker):
    web, _ = slack(mocker), stored(mocker)
    runner = mocker.patch.object(slack_ask, "runner")
    runner.submit = mocker.AsyncMock()
    followed = mocker.patch.object(slack_ask, "follow", mocker.AsyncMock())

    asyncio.run(slack_ask.asked(web, EVENT))

    runner.submit.assert_awaited_once_with(CONV, "combien de candidatures ?", [], "camille.martin@inclusion.gouv.fr")
    followed.assert_awaited_once_with(web, CONV)


def test_a_turn_that_cannot_be_submitted_is_released(mocker):
    web, store = slack(mocker), stored(mocker)
    runner = mocker.patch.object(slack_ask, "runner")
    runner.submit = mocker.AsyncMock(side_effect=ConnectionError("redis"))

    with pytest.raises(ConnectionError):
        asyncio.run(slack_ask.asked(web, EVENT))

    store.end_turn.assert_called_once_with(CONV, False)


@pytest.mark.parametrize(
    "event",
    [EVENT | {"bot_id": "B1"}, EVENT | {"edited": {"ts": "1"}}, {k: v for k, v in EVENT.items() if k != "user"}],
    ids=["a bot", "edited", "no author"],
)
def test_a_mention_by_a_bot_or_an_edited_message_is_ignored(mocker, monkeypatch, event):
    monkeypatch.setitem(slack_ask.workspace, "loop", mocker.MagicMock())
    threadsafe = mocker.patch.object(slack_ask.asyncio, "run_coroutine_threadsafe")

    slack_ask.mentioned(mocker.MagicMock(), event)

    threadsafe.assert_not_called()


def test_the_bot_learns_who_it_is_at_its_first_mention(mocker, monkeypatch):
    monkeypatch.setattr(slack_ask, "workspace", {"url": "", "bot": "", "loop": None})
    web = slack(mocker)
    web.auth_test.return_value = {"url": "https://equipe.slack.com/", "user_id": BOT}
    begin = mocker.patch.object(slack_ask, "begin", return_value=None)

    asyncio.run(slack_ask.asked(web, EVENT))

    assert slack_ask.workspace["bot"] == BOT
    begin.assert_called_once_with(web, EVENT)


def test_a_second_mention_in_a_thread_continues_its_conversation(mocker):
    web, store = slack(mocker), stored(mocker, existing=True)

    begun = slack_ask.begin(web, EVENT | {"thread_ts": "1700000000.000100"})

    store.slack_conversation.assert_called_once_with("C0TEST", "1700000000.000100")
    store.create_conversation.assert_not_called()
    store.start_turn.assert_called_once_with(CONV, "combien de candidatures ?")
    assert begun == (CONV, "combien de candidatures ?", "camille.martin@inclusion.gouv.fr")
    assert web.chat_postMessage.call_args.kwargs["text"] == "Autometa regarde…"


def test_a_follow_up_by_someone_else_enters_under_their_name_and_plays_for_the_owner(mocker):
    web, store = slack(mocker), stored(mocker, existing=True, owns=True)

    begun = slack_ask.begin(web, EVENT | {"user": "U2"})

    store.start_turn.assert_called_once_with(CONV, "Louis D. : combien de candidatures ?")
    assert begun == (CONV, "Louis D. : combien de candidatures ?", "camille.martin@inclusion.gouv.fr")


def test_a_follow_up_by_someone_not_admitted_is_refused_and_does_not_enter(mocker):
    web, store = slack(mocker), stored(mocker, existing=True)

    assert slack_ask.begin(web, EVENT | {"user": "U2"}) is None

    store.start_turn.assert_not_called()
    store.queue_message.assert_not_called()
    assert web.chat_postEphemeral.call_args.kwargs["user"] == "U2"


def test_a_mention_during_a_turn_joins_the_queue_with_the_thread_since_the_previous_one(mocker):
    replies = [
        reply("U1", f"<@{BOT}> première demande", "1700000000.000100"),
        reply("U2", "entre-temps", "1700000200.000100"),
        reply("U1", EVENT["text"], EVENT["ts"]),
    ]
    web, store = slack(mocker, replies), stored(mocker, existing=True, running=True)

    begun = slack_ask.begin(web, EVENT | {"thread_ts": "1700000000.000100"})

    assert begun == (CONV, None, "camille.martin@inclusion.gouv.fr")
    conv_id, content, held = store.queue_message.call_args.args
    assert (conv_id, content) == (CONV, "combien de candidatures ?")
    assert [m["text"] for m in json.loads(held["context"])["messages"]] == ["entre-temps"]
    assert held["prompt"].startswith("[Fil Slack") and held["prompt"].endswith("[Demande]\ncombien de candidatures ?")
    store.start_turn.assert_not_called()
    web.chat_postMessage.assert_not_called()
    waits = web.chat_postEphemeral.call_args.kwargs
    assert (waits["user"], waits["thread_ts"]) == ("U1", "1700000000.000100")
    assert "prendra votre demande" in waits["text"]


def test_mentions_waiting_together_leave_with_the_whole_thread_since_the_running_turn(mocker):
    web, store = (
        slack(mocker, [reply("U2", "second", "1700000250.000100")]),
        stored(mocker, existing=True, running=True),
    )
    first = json.dumps({"messages": [{"author": "Louis D.", "at": "x", "text": "premier"}], "note": ""})
    waiting = [{"id": "e0", "status": "waiting", "content": "q", "slack": {"context": first, "prompt": "p"}}]
    store.get_conversation.side_effect = None
    store.get_conversation.return_value = Conversation(
        id=CONV, user_id="camille.martin@inclusion.gouv.fr", needs_response=True, pending_messages=waiting
    )

    slack_ask.begin(web, EVENT | {"thread_ts": "1700000000.000100"})

    held = store.queue_message.call_args.args[2]
    assert [m["text"] for m in json.loads(held["context"])["messages"]] == ["premier", "second"]
    assert "premier" in held["prompt"] and "second" in held["prompt"]


def test_a_queued_mention_only_signals_the_queue_and_starts_no_second_follower(mocker):
    web = slack(mocker)
    stored(mocker, existing=True, running=True)
    runner = mocker.patch.object(slack_ask, "runner")
    runner.notify, runner.submit = mocker.AsyncMock(), mocker.AsyncMock()
    followed = mocker.patch.object(slack_ask, "follow", mocker.AsyncMock())
    slack_ask.following[CONV] = mocker.MagicMock()

    asyncio.run(slack_ask.asked(web, EVENT))

    runner.notify.assert_awaited_once_with(CONV, "queue")
    runner.submit.assert_not_awaited()
    followed.assert_not_awaited()


def test_when_the_queue_leaves_the_finished_turn_gets_its_answer_and_the_next_its_own_message(mocker):
    web, store = slack(mocker), live_conversation(mocker, running=False)
    store.last_user_message_id.side_effect = [1, 6, 6]
    web.chat_postMessage.return_value = {"ts": "1700000500.000100"}

    follow(mocker, store, web, "queue", "done:6")

    first, second = web.chat_update.call_args_list
    assert (first.kwargs["ts"], second.kwargs["ts"]) == ("1700000301.000200", "1700000500.000100")
    assert first.kwargs["blocks"][0]["text"]["text"] == "42 candidatures."
    assert web.chat_postMessage.call_args.kwargs["text"] == "Autometa regarde…"
    assert [call.args[1] for call in store.get_thread_messages.call_args_list] == [1, 6]


def test_mentions_left_waiting_by_a_turn_that_failed_are_said_not_to_have_left(mocker):
    web, store = slack(mocker), live_conversation(mocker, running=False)
    store.pending_messages.return_value = [
        {"id": "e1", "status": "returned", "content": "q1", "slack": {"context": "", "prompt": "q1"}},
        {"id": "e2", "status": "returned", "content": "depuis la page"},
    ]

    slack_ask.give_back(web, CONV)

    store.take_queued.assert_called_once_with(CONV, "e1")
    said = web.chat_postMessage.call_args.kwargs
    assert said["thread_ts"] == EVENT["ts"] and "Redemandez-moi" in said["text"]


def test_after_a_restart_messages_left_on_a_verb_are_followed_again_or_completed(mocker):
    web, store = slack(mocker), live_conversation(mocker, running=False)
    store.slack_live_conversations.return_value = [CONV]
    runner = mocker.patch.object(slack_ask, "runner")
    runner.subscribe = mocker.AsyncMock(return_value=Signals())
    runner.is_done = mocker.AsyncMock(return_value=False)

    async def restart():
        await slack_ask.recover(web)
        await asyncio.gather(*slack_ask.following.values())

    asyncio.run(restart())

    assert web.chat_update.call_args.kwargs["blocks"][0]["text"]["text"] == "42 candidatures."
    store.update_conversation.assert_called_with(CONV, slack_message_ts=None)
    assert slack_ask.following == {}
