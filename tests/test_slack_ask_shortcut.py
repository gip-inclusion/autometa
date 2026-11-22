"""Le raccourci « Demander à Autometa » d'un message : la fenêtre, le message choisi, la réponse là où le bot peut."""

import asyncio
import json

import pytest
from slack_sdk.errors import SlackApiError

from tests.test_slack_ask_mention import BOT, CONV, PEOPLE, refused, reply, slack, stored
from web import config, slack_ask

CHOSEN = {"user": "U2", "ts": "1700000200.000100", "text": "Le message choisi"}
ACTION = {
    "type": "message_action",
    "callback_id": "ask_autometa",
    "trigger_id": "T1",
    "user": {"id": "U1"},
    "channel": {"id": "C0TEST", "name": "general"},
    "message": {**CHOSEN, "thread_ts": "1700000000.000100"},
}


@pytest.fixture(autouse=True)
def instance(mocker, monkeypatch):
    monkeypatch.setattr(config, "BASE_URL", "https://autometa.example")
    monkeypatch.setattr(config, "SLACK_CHART_IMAGES", False)
    monkeypatch.setattr(slack_ask, "workspace", {"url": "https://equipe.slack.com/", "bot": BOT, "loop": None})
    monkeypatch.setattr(slack_ask, "people", {})
    monkeypatch.setattr(slack_ask, "following", {})


def event(**more):
    asked = {"channel": "C0TEST", "channel_type": "channel", "thread_ts": "1700000000.000100", "chosen": CHOSEN}
    return {**asked, "user": "U1", "text": "Qu'en penser ?", "ts": CHOSEN["ts"], **more}


def test_the_shortcut_opens_a_window_that_asks_only_the_question_and_remembers_the_message(mocker):
    web = mocker.MagicMock()

    slack_ask.shortcut(web, ACTION)

    opened = web.views_open.call_args.kwargs
    assert opened["trigger_id"] == "T1"
    view = opened["view"]
    assert (view["type"], view["callback_id"]) == ("modal", "ask_autometa")
    assert [block["type"] for block in view["blocks"]] == ["input"]
    assert view["blocks"][0]["element"] == {"type": "plain_text_input", "action_id": "text", "multiline": True}
    assert json.loads(view["private_metadata"]) == {
        "channel": "C0TEST",
        "channel_type": None,
        "thread_ts": "1700000000.000100",
        "chosen": CHOSEN,
    }


@pytest.mark.parametrize(("name", "hint"), [("directmessage", "im"), ("privategroup", "group"), ("general", None)])
def test_the_window_remembers_a_private_channel_or_a_direct_message_as_such(mocker, name, hint):
    web = mocker.MagicMock()

    slack_ask.shortcut(web, ACTION | {"channel": {"id": "C0TEST", "name": name}})

    assert json.loads(web.views_open.call_args.kwargs["view"]["private_metadata"])["channel_type"] == hint


def test_a_long_chosen_message_is_cut_to_fit_what_a_window_keeps(mocker):
    web = mocker.MagicMock()

    slack_ask.shortcut(web, ACTION | {"message": {**CHOSEN, "text": "x" * 10_000}})

    assert len(web.views_open.call_args.kwargs["view"]["private_metadata"]) < 3000


def test_a_window_that_cannot_be_opened_is_logged_and_nothing_else_happens(mocker, caplog):
    web = mocker.MagicMock()
    web.views_open.side_effect = refused(mocker, "expired_trigger_id")

    slack_ask.shortcut(web, ACTION)

    assert "Fenêtre du raccourci Slack non ouverte : expired_trigger_id" in caplog.text


def test_the_submitted_question_is_played_as_a_request_about_the_chosen_message(mocker, monkeypatch):
    monkeypatch.setitem(slack_ask.workspace, "loop", mocker.MagicMock())
    threadsafe = mocker.patch.object(slack_ask.asyncio, "run_coroutine_threadsafe")
    played = mocker.patch.object(slack_ask, "asked", mocker.MagicMock())
    kept = {"channel": "C0TEST", "channel_type": None, "thread_ts": "1700000000.000100", "chosen": CHOSEN}
    submission = {
        "type": "view_submission",
        "user": {"id": "U1"},
        "view": {
            "callback_id": "ask_autometa",
            "private_metadata": json.dumps(kept),
            "state": {"values": {"question": {"text": {"type": "plain_text_input", "value": "Qu'en penser ?"}}}},
        },
    }
    web = mocker.MagicMock()

    slack_ask.shortcut(web, submission)

    played.assert_called_once_with(web, {**kept, "user": "U1", "text": "Qu'en penser ?", "ts": CHOSEN["ts"]})
    threadsafe.assert_called_once()


def test_in_a_public_channel_of_the_bot_the_request_takes_the_chosen_message_and_the_whole_thread(mocker):
    replies = [
        reply("U2", "début du fil", "1700000000.000100"),
        reply("U2", CHOSEN["text"], CHOSEN["ts"]),
        reply("U1", "après le message choisi", "1700000250.000100"),
    ]
    web, store = slack(mocker, replies), stored(mocker)

    begun = slack_ask.begin(web, event())

    said = json.loads(store.add_message.call_args.args[2])
    assert [m["text"] for m in said["messages"]] == ["début du fil", "Le message choisi", "après le message choisi"]
    store.start_turn.assert_called_once_with(CONV, "Qu'en penser ?")
    assert begun[1].endswith("[Demande]\nQu'en penser ?")
    assert web.chat_postMessage.call_args.kwargs["channel"] == "C0TEST"
    store.create_conversation.assert_called_once_with(
        user_id="camille.martin@inclusion.gouv.fr", slack_thread=("C0TEST", "1700000000.000100")
    )


@pytest.mark.parametrize("hint", ["group", "im"], ids=["private channel", "direct message"])
def test_in_a_private_place_the_request_takes_the_chosen_message_alone_and_says_so(mocker, hint):
    web, store = slack(mocker, [reply("U2", "début du fil", "1700000000.000100")]), stored(mocker)

    slack_ask.begin(web, event(channel_type=hint))

    web.conversations_replies.assert_not_called()
    said = json.loads(store.add_message.call_args.args[2])
    assert [m["text"] for m in said["messages"]] == ["Le message choisi"]
    assert "Canal privé" in said["note"]


def test_where_the_bot_is_not_the_request_takes_the_chosen_message_and_is_answered_to_the_asker_alone(mocker):
    web, store = slack(mocker), stored(mocker)
    web.conversations_replies.side_effect = refused(mocker, "not_in_channel")
    web.chat_postMessage.side_effect = [
        refused(mocker, "not_in_channel"),
        {"channel": "D0ASKER", "ts": "1700000600.000100"},
    ]

    begun = slack_ask.begin(web, event())

    said = json.loads(store.add_message.call_args.args[2])
    assert [m["text"] for m in said["messages"]] == ["Le message choisi"]
    assert "Je ne suis pas dans ce canal" in said["note"]
    direct = web.chat_postMessage.call_args.kwargs
    assert (direct["channel"], direct["thread_ts"]) == ("U1", None)
    assert "Je ne suis pas dans ce canal" in direct["blocks"][0]["text"]["text"]
    conv = store.get_conversation(CONV)
    assert (conv.slack_channel, conv.slack_thread_ts, conv.slack_message_ts) == ("D0ASKER", None, "1700000600.000100")
    assert begun[0] == CONV


def test_a_mention_is_never_answered_in_direct_when_its_message_cannot_be_posted(mocker):
    web, store = slack(mocker), stored(mocker)
    web.chat_postMessage.side_effect = refused(mocker, "not_in_channel")

    with pytest.raises(SlackApiError):
        slack_ask.begin(web, {k: v for k, v in event().items() if k != "chosen"})

    web.chat_postMessage.assert_called_once()
    store.delete_conversation.assert_called_once_with(CONV)


def test_someone_not_admitted_is_refused_in_direct_where_the_bot_cannot_whisper(mocker):
    web = slack(mocker)
    stored(mocker)
    web.chat_postEphemeral.side_effect = refused(mocker, "no_permission")

    assert slack_ask.begin(web, event(user="U2")) is None

    direct = web.chat_postMessage.call_args.kwargs
    assert direct["channel"] == "U2" and "ouvrez Autometa une première fois" in direct["text"]


def test_a_message_chosen_from_an_application_is_named_as_such(mocker):
    web, store = slack(mocker), stored(mocker)

    slack_ask.begin(web, event(channel_type="group", chosen={"user": None, "ts": CHOSEN["ts"], "text": "Alerte"}))

    assert json.loads(store.add_message.call_args.args[2])["messages"][0]["author"] == "Une application"


def test_a_direct_conversation_links_to_its_channel(mocker):
    stored(mocker)
    conv = slack_ask.store.get_conversation(CONV)
    conv.slack_channel, conv.slack_thread_ts = "D0ASKER", None

    assert slack_ask.thread_url(conv) == "https://slack.com/app_redirect?channel=D0ASKER"
    assert PEOPLE["U1"]["real_name"] == "Camille Martin"


def test_the_shortcut_goes_through_the_same_admission_and_loop_as_a_mention(mocker):
    web = slack(mocker)
    stored(mocker)
    runner = mocker.patch.object(slack_ask, "runner")
    runner.submit = mocker.AsyncMock()
    followed = mocker.patch.object(slack_ask, "follow", mocker.AsyncMock())

    asyncio.run(slack_ask.asked(web, event(channel_type="group")))

    assert runner.submit.await_args.args[0] == CONV
    assert runner.submit.await_args.args[1].endswith("[Demande]\nQu'en penser ?")
    followed.assert_awaited_once_with(web, CONV)
