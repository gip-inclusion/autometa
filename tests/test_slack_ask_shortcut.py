"""Le raccourci « Demander à Autometa » d'un message : la fenêtre, le message choisi, la réponse là où le bot peut."""

import asyncio

import pytest

from tests.slack_ask_fakes import CHANNEL, OWNER, instance, refused, reply, slack
from web import slack_ask

THREAD = "1700000000.000100"
CHOSEN = {"user": "U2", "ts": "1700000200.000100", "text": "Le message choisi", "cut": False}
ACTION = {
    "type": "message_action",
    "callback_id": "ask_autometa",
    "trigger_id": "T1",
    "user": {"id": "U1"},
    "channel": {"id": CHANNEL, "name": "general"},
    "message": {"user": "U2", "ts": CHOSEN["ts"], "text": CHOSEN["text"], "thread_ts": THREAD},
}


@pytest.fixture(autouse=True)
def world(mocker, monkeypatch):
    return instance(mocker, monkeypatch)


def event(**more):
    asked = {"channel": CHANNEL, "channel_type": None, "thread_ts": THREAD, "chosen": CHOSEN}
    return {**asked, "user": "U1", "text": "Qu'en penser ?", "ts": CHOSEN["ts"], **more}


@pytest.mark.parametrize(("name", "hint"), [("directmessage", "im"), ("privategroup", "group"), ("general", None)])
def test_the_shortcut_asks_at_once_for_an_answer_to_the_selected_message_without_a_window(
    mocker, monkeypatch, name, hint
):
    monkeypatch.setitem(slack_ask.workspace, "loop", mocker.MagicMock())
    threadsafe = mocker.patch.object(slack_ask.asyncio, "run_coroutine_threadsafe")
    played = mocker.patch.object(slack_ask, "asked", mocker.MagicMock())
    web = mocker.MagicMock()

    slack_ask.shortcut(web, ACTION | {"channel": {"id": CHANNEL, "name": name}})

    played.assert_called_once_with(
        web,
        {
            "channel": CHANNEL,
            "channel_type": hint,
            "thread_ts": THREAD,
            "chosen": CHOSEN,
            "user": "U1",
            "text": "Réponds au message sélectionné.",
            "ts": CHOSEN["ts"],
        },
    )
    threadsafe.assert_called_once()
    web.views_open.assert_not_called()


def test_in_a_public_channel_of_the_bot_the_request_takes_the_whole_thread_and_the_chosen_message_as_slack_has_it(
    mocker, world
):
    replies = [
        reply("U2", "début du fil", "1700000000.000100"),
        reply("U2", "Le message choisi, en entier", CHOSEN["ts"]),
        reply("U1", "après le message choisi", "1700000250.000100"),
    ]
    web = slack(mocker, replies)

    conv_id, asked, email = slack_ask.begin(web, event(chosen=CHOSEN | {"cut": True}))

    kept = world.store.thread(conv_id)
    assert [m["text"] for m in kept["messages"]] == [
        "début du fil",
        "Le message choisi, en entier",
        "après le message choisi",
    ]
    assert kept["note"] == ""
    assert float(kept["through"]) > 1_700_000_300
    assert asked.endswith("Qu'en penser ?\n" + asked.split("\n")[-1]) and email == OWNER
    conv = world.store.get_conversation(conv_id)
    assert (conv.slack_channel, conv.slack_thread_ts) == (CHANNEL, THREAD)


def test_a_mention_after_a_shortcut_request_takes_the_thread_from_that_request_on(mocker, world):
    web = slack(mocker, [reply("U2", CHOSEN["text"], CHOSEN["ts"])])
    mocker.patch.object(slack_ask.time, "time", return_value=1700000300.0)
    conv_id, _, _ = slack_ask.begin(web, event())
    world.store.end_turn(conv_id, False)
    later = [reply("U2", CHOSEN["text"], CHOSEN["ts"]), reply("U2", "depuis le raccourci", "1700000350.000100")]
    web.conversations_replies.return_value = {"messages": later}

    slack_ask.begin(web, {"channel": CHANNEL, "thread_ts": THREAD, "user": "U1", "text": "et ?", "ts": "1700000400.0"})

    assert [m["text"] for m in world.store.thread(conv_id)["messages"]] == ["depuis le raccourci"]


@pytest.mark.parametrize("hint", ["group", "im"], ids=["private channel", "direct message"])
def test_in_a_private_place_the_request_takes_the_chosen_message_alone_and_says_so(mocker, world, hint):
    web = slack(mocker, [reply("U2", "début du fil", "1700000000.000100")])

    conv_id, _, _ = slack_ask.begin(web, event(channel_type=hint))

    web.conversations_replies.assert_not_called()
    kept = world.store.thread(conv_id)
    assert [m["text"] for m in kept["messages"]] == ["Le message choisi"]
    place = "Message direct" if hint == "im" else "Canal privé"
    assert kept["note"] == (
        f"{place} : l'agent n'a accès qu'aux messages qui mentionnent explicitement Autometa et au message sélectionné."
    )


def test_where_the_bot_is_not_the_request_is_answered_to_the_asker_alone_and_says_what_it_could_not_take(mocker, world):
    web = slack(mocker)
    web.conversations_replies.side_effect = refused(mocker, "not_in_channel")
    web.chat_postMessage.side_effect = [refused(mocker, "not_in_channel"), {"channel": "D0ASKER", "ts": "1700000600.0"}]

    conv_id, _, _ = slack_ask.begin(web, event(chosen=CHOSEN | {"cut": True}))

    kept = world.store.thread(conv_id)
    assert [m["text"] for m in kept["messages"]] == ["Le message choisi"]
    assert "Je ne suis pas dans ce canal" in kept["note"] and "repris qu'en partie" in kept["note"]
    direct = web.chat_postMessage.call_args.kwargs
    assert (direct["channel"], direct["thread_ts"]) == ("U1", None)
    assert "Je ne suis pas dans ce canal" in direct["blocks"][2]["elements"][0]["text"]
    conv = world.store.get_conversation(conv_id)
    assert (conv.slack_channel, conv.slack_thread_ts, conv.slack_message_ts) == ("D0ASKER", None, "1700000600.0")


def test_a_thread_that_already_has_its_conversation_keeps_it_when_the_bot_can_no_longer_write_there(mocker, world):
    web = slack(mocker)
    conv_id, _, _ = slack_ask.begin(web, event())
    world.store.end_turn(conv_id, False)
    web.chat_postMessage.side_effect = [refused(mocker, "not_in_channel"), {"channel": "D0ASKER", "ts": "1.0"}]

    with pytest.raises(slack_ask.SlackApiError):
        slack_ask.begin(web, event())

    conv = world.store.get_conversation(conv_id)
    assert (conv.slack_channel, conv.slack_thread_ts, conv.needs_response) == (CHANNEL, THREAD, False)
    assert "plus écrire dans ce fil" in web.chat_postEphemeral.call_args.kwargs["text"]


def test_a_message_chosen_from_a_guest_is_left_out_and_the_context_says_so(mocker, world):
    web = slack(mocker)

    conv_id, asked, _ = slack_ask.begin(web, event(channel_type="group", chosen=CHOSEN | {"user": "U3"}))

    kept = world.store.thread(conv_id)
    assert kept["messages"] == []
    assert kept["left_out"] == 1
    assert kept["note"] == "Canal privé : l'agent n'a accès qu'aux messages qui mentionnent explicitement Autometa."
    assert "> (1 message d'invités" in asked


def test_someone_not_admitted_is_refused_in_direct_where_the_bot_cannot_whisper(mocker, world):
    web = slack(mocker)
    web.chat_postEphemeral.side_effect = refused(mocker, "no_permission")

    assert slack_ask.begin(web, event(user="U2")) is None

    direct = web.chat_postMessage.call_args.kwargs
    assert direct["channel"] == "U2" and "ouvrez Autometa une première fois" in direct["text"]


def test_every_validation_of_the_window_is_a_request_even_about_the_same_message(mocker, world):
    web = slack(mocker)
    mocker.patch.object(slack_ask, "follow", mocker.AsyncMock())

    asyncio.run(slack_ask.asked(web, event()))
    asyncio.run(slack_ask.asked(web, event(text="Et encore ?")))

    conv_id = next(iter(world.store.convs))
    assert world.runner.submit.await_count == 1
    assert [e["content"] for e in world.store.pending_messages(conv_id)] == ["Et encore ?"]


def test_the_shortcut_may_be_used_on_a_message_from_an_application(mocker, world):
    alert = {"bot_id": "B9", "ts": CHOSEN["ts"], "text": "", "bot_profile": {"name": "Sentry"}}
    alert |= {"attachments": [{"fallback": "Erreur 500 sur /candidatures"}]}
    web = slack(mocker)

    kept = slack_ask.remembered(alert, {"id": CHANNEL, "name": "privategroup"})
    conv_id, asked, _ = slack_ask.begin(web, {**kept, "user": "U1", "text": "Que s'est-il passé ?", "ts": CHOSEN["ts"]})

    assert kept["chosen"] == {
        "user": None,
        "ts": CHOSEN["ts"],
        "text": "Erreur 500 sur /candidatures",
        "cut": False,
    } | {"app": "Sentry"}
    assert [(m["author"], m["text"]) for m in world.store.thread(conv_id)["messages"]] == [
        ("Application Sentry", "Erreur 500 sur /candidatures")
    ]
    assert "> Application Sentry, " in asked


def test_the_bot_message_says_who_asked_what_by_the_shortcut_while_it_works_and_above_its_answer(mocker, world):
    web = slack(mocker, [reply("U2", CHOSEN["text"], CHOSEN["ts"])])

    conv_id, _, _ = slack_ask.begin(web, event())

    first = web.chat_postMessage.call_args.kwargs["blocks"][0]
    assert first["type"] == "context" and first["elements"][0]["text"].endswith(" a demandé : Qu'en penser ?")
    world.store.add_message(conv_id, "assistant", "Du bien.")
    world.store.end_turn(conv_id, False)
    _, blocks = slack_ask.answer(conv_id, world.store.last_user_message_id(conv_id))
    assert [block["type"] for block in blocks] == ["context", "rich_text", "context"]
    assert blocks[0] == first


def test_the_agent_is_told_which_message_of_the_thread_was_selected_even_in_a_long_thread(mocker, world):
    replies = [reply("U2", CHOSEN["text"], CHOSEN["ts"])] + [
        reply("U2", "suite " * 400, f"17000003{n:02d}.000100") for n in range(12)
    ]

    slack_ask.uploads.upload_file.side_effect = slack_ask.uploads.UploadError("refusé")

    _, asked, _ = slack_ask.begin(slack(mocker, replies), event())

    lines = asked.split("\n")
    assert "La personne qui demande a sélectionné le message n° 1 des 6 ci-dessous." in lines
    assert sum("Le message choisi" in line for line in lines if line.startswith("> ")) == 1
