"""Le message du bot dans Slack pendant et après un tour : verbes, réponse finale, tours suivants, pannes."""

import asyncio
import json

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.exc import ProgrammingError

from tests.slack_ask_fakes import BASE, BOT, CHANNEL, Signals, instance, refused, reply, slack
from tests.test_slack_ask_mention import EVENT, THREAD
from web import complexity, slack_ask, slack_excerpts

LIVE = "1700000901.0"


@pytest.fixture(autouse=True)
def world(mocker, monkeypatch):
    return instance(mocker, monkeypatch)


def started(mocker, world, event=EVENT, replies=()):
    """Une demande venue de Slack, son tour en cours, son message qui vit."""
    web = slack(mocker, replies)
    conv_id, _, _ = slack_ask.begin(web, event)
    return web, conv_id, world.store.last_user_message_id(conv_id)


def answered(world, conv_id, *messages, flush=False):
    """L'agent écrit ces messages, puis le tour se clôt."""
    for kind, content in messages:
        world.store.add_message(conv_id, kind, content)
    return world.store.end_turn(conv_id, flush)


def followed(world, web, conv_id, *heard):
    signals = Signals(*heard)
    world.runner.subscribe.return_value = signals
    asyncio.run(slack_ask.follow(web, conv_id))
    return signals


def written(block):
    return "".join(text["text"] for part in block["elements"] for text in slack_excerpts.texts(part))


def texts(web):
    return [call.kwargs["text"] for call in web.chat_update.call_args_list]


def test_at_the_end_of_the_turn_the_living_message_becomes_the_final_answer_alone(mocker, world):
    web, conv_id, _ = started(mocker, world)
    spoken = [
        ("assistant", "Je cherche."),
        ("tool_use", "{}"),
        ("tool_result", ""),
        ("assistant", "**42** candidatures.\n"),
    ]

    signals = followed(world, web, conv_id, lambda: answered(world, conv_id, *spoken) or "done:1")

    final = web.chat_update.call_args.kwargs
    assert (final["channel"], final["ts"]) == (CHANNEL, LIVE)
    assert (final["blocks"][0]["type"], written(final["blocks"][0])) == ("rich_text", "42 candidatures.")
    assert "Je cherche" not in json.dumps(final["blocks"], ensure_ascii=False)
    assert f"<{BASE}/c/{conv_id}|" in final["blocks"][-1]["elements"][0]["text"]
    assert world.store.get_conversation(conv_id).slack_message_ts is None
    assert signals.closed and slack_ask.following == {}
    assert world.redis.keys == {}


def test_updates_coming_at_once_do_not_change_the_verb(mocker, world):
    web, conv_id, _ = started(mocker, world)
    end = lambda: answered(world, conv_id, ("assistant", "Fini.")) or "done:1"  # noqa: E731

    followed(world, web, conv_id, "update", "update", "update", end)

    assert texts(web) == ["Fini."]


def test_the_verb_changes_when_the_agent_moves_and_keeps_what_the_bot_said_it_left_out(mocker, world):
    web, conv_id, _ = started(mocker, world, EVENT | {"channel_type": "group"})
    ticks = iter(range(0, 10_000, 10))
    mocker.patch.object(slack_ask, "time", mocker.MagicMock(monotonic=lambda: next(ticks)))
    end = lambda: answered(world, conv_id, ("assistant", "Fini.")) or "done:1"  # noqa: E731

    followed(world, web, conv_id, "update", "update", end)

    first, second, final = web.chat_update.call_args_list
    assert first.kwargs["text"].startswith("Autometa ") and first.kwargs["text"] != "Autometa regarde…"
    assert second.kwargs["text"] != first.kwargs["text"]
    assert all("Canal privé" in call.kwargs["blocks"][1]["elements"][0]["text"] for call in (first, second))
    assert [block["type"] for block in final.kwargs["blocks"]] == ["rich_text", "context", "context"]
    assert "Canal privé" in final.kwargs["blocks"][1]["elements"][0]["text"]


def test_a_verb_slack_rate_limits_tells_how_long_to_stay_quiet(mocker, world):
    web, conv_id, _ = started(mocker, world)
    web.chat_update.side_effect = refused(mocker, "ratelimited", retry_after="30")

    assert slack_ask.say(web, world.store.get_conversation(conv_id), "explore", "") == 30


@pytest.mark.parametrize(
    "spoken",
    [
        [],
        [("assistant", "*Interrompu.*")],
        [("assistant", "Du texte déjà écrit."), ("assistant", "*Interrompu.*")],
        [("assistant", "Du texte."), ("assistant", "*Interrompu (redémarrage serveur).*")],
        [("assistant", "Du texte."), ("assistant", "*Une erreur est survenue côté agent : boom*")],
        [("assistant", "Du texte."), ("assistant", "*Une erreur s'est produite, merci de réessayer.*")],
        [("assistant", "Du texte."), ("assistant", "*Budget de 100 appels d'outils dépassé pour ce tour.*")],
        [("assistant", "Début."), ("limit", "Limite atteinte")],
    ],
    ids=["no answer", "stopped", "stopped after text", "restart", "agent error", "error", "budget", "limit"],
)
def test_a_turn_that_failed_or_was_stopped_says_so_whatever_the_agent_had_written(mocker, world, spoken):
    web, conv_id, question = started(mocker, world)
    answered(world, conv_id, *spoken)

    asyncio.run(slack_ask.finish(web, conv_id, question, LIVE))

    final = web.chat_update.call_args.kwargs
    assert final["text"] == "La demande n'a pas abouti."
    assert [block["type"] for block in final["blocks"]] == ["section", "context"]


def test_the_complexity_alert_is_neither_the_answer_nor_glued_to_it(mocker, world):
    web, conv_id, question = started(mocker, world)
    answered(world, conv_id, ("assistant", "La vraie réponse."), ("assistant", complexity.ALERT_MESSAGE))

    asyncio.run(slack_ask.finish(web, conv_id, question, LIVE))

    assert written(web.chat_update.call_args.kwargs["blocks"][0]) == "La vraie réponse."


def test_an_answer_that_merely_starts_with_italics_is_an_answer(mocker, world):
    web, conv_id, question = started(mocker, world)
    answered(world, conv_id, ("assistant", "*Interrompu* n'est pas le mot : voici la réponse."))

    asyncio.run(slack_ask.finish(web, conv_id, question, LIVE))

    assert web.chat_update.call_args.kwargs["text"].startswith("Interrompu n'est pas le mot")


def test_nothing_the_agent_wrote_is_read_by_slack(mocker, world):
    web, conv_id, question = started(mocker, world)
    answered(world, conv_id, ("assistant", "<!channel> @here <https://evil.example|ici> *gras* `code`\n"))

    asyncio.run(slack_ask.finish(web, conv_id, question, LIVE))

    final = web.chat_update.call_args.kwargs
    said = slack_excerpts.texts(final["blocks"][0]["elements"][0])
    assert {part["type"] for part in said} == {"text"}
    assert [part["text"] for part in said if part.get("style")] == ["gras", "code"]
    assert final["text"] == "@​here https://evil.example|ici gras code"


def test_an_answer_too_long_for_a_message_is_cut_and_says_where_the_rest_is(mocker, world):
    web, conv_id, question = started(mocker, world)
    answered(world, conv_id, ("assistant", "phrase assez longue. " * 2000))

    asyncio.run(slack_ask.finish(web, conv_id, question, LIVE))

    blocks = web.chat_update.call_args.kwargs["blocks"]
    assert blocks[-2]["text"]["text"] == "… suite dans Autometa"
    assert len(written(blocks[0])) <= 9100 and len(blocks) == 3


def test_a_table_slack_refuses_is_posted_again_in_monospace(mocker, world):
    web, conv_id, question = started(mocker, world)
    answered(world, conv_id, ("assistant", "Voici.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"))
    web.chat_update.side_effect = [refused(mocker, "invalid_blocks"), None]

    asyncio.run(slack_ask.finish(web, conv_id, question, LIVE))

    first, second = web.chat_update.call_args_list
    assert [block["type"] for block in first.kwargs["blocks"]] == ["rich_text", "table", "context"]
    assert "```" in second.kwargs["blocks"][1]["text"]["text"]


def test_a_rate_limited_final_answer_waits_as_slack_asks_then_goes_in_the_same_form(mocker, world):
    web, conv_id, question = started(mocker, world)
    answered(world, conv_id, ("assistant", "Voici.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"))
    web.chat_update.side_effect = [refused(mocker, "ratelimited", "7"), refused(mocker, "ratelimited"), None]

    asyncio.run(slack_ask.finish(web, conv_id, question, LIVE))

    assert [call.args[0] for call in slack_ask.asyncio.sleep.await_args_list] == [7, 5]
    kinds = [[block["type"] for block in call.kwargs["blocks"]] for call in web.chat_update.call_args_list]
    assert kinds == [["rich_text", "table", "context"]] * 3
    assert world.store.get_conversation(conv_id).slack_message_ts is None


def test_a_final_answer_slack_keeps_rate_limiting_is_never_dropped_and_stays_to_complete(mocker, world, caplog):
    web, conv_id, question = started(mocker, world)
    answered(world, conv_id, ("assistant", "Réponse."))
    web.chat_update.side_effect = refused(mocker, "ratelimited", "60")

    asyncio.run(slack_ask.finish(web, conv_id, question, LIVE))

    assert world.store.get_conversation(conv_id).slack_message_ts == LIVE
    assert conv_id in world.store.slack_live_conversations()
    assert "Slack limite le débit" in caplog.text


def test_slack_unreachable_at_the_end_is_tried_again_then_given_up_with_a_log_line(mocker, world, caplog):
    web, conv_id, question = started(mocker, world)
    answered(world, conv_id, ("assistant", "Réponse."))
    web.chat_update.side_effect = OSError("réseau")

    asyncio.run(slack_ask.finish(web, conv_id, question, LIVE))

    assert web.chat_update.call_count == 2
    assert f"Réponse de la conversation {conv_id} abandonnée dans Slack" in caplog.text
    assert world.store.get_conversation(conv_id).slack_message_ts is None


def test_a_message_typed_on_the_page_during_a_slack_turn_is_answered_on_the_page_only(mocker, world):
    web, conv_id, _ = started(mocker, world)
    world.store.queue_message(conv_id, "écrit sur la page")
    left = lambda: answered(world, conv_id, ("assistant", "Réponse à Slack."), flush=True) and "queue"  # noqa: E731
    end = lambda: answered(world, conv_id, ("assistant", "Réponse à la page.")) or "done:9"  # noqa: E731

    followed(world, web, conv_id, left, end)

    assert texts(web) == ["Réponse à Slack."]
    web.chat_postMessage.assert_called_once()
    assert world.store.get_conversation(conv_id).slack_message_ts is None


def test_when_queued_mentions_leave_the_finished_turn_gets_its_answer_and_the_next_its_own_message(mocker, world):
    web, conv_id, _ = started(mocker, world)
    slack_ask.begin(web, EVENT | {"ts": "1700000401.000100", "text": f"<@{BOT}> et par région ?", "channel_type": "im"})
    left = lambda: answered(world, conv_id, ("assistant", "Première réponse."), flush=True) and "queue"  # noqa: E731
    end = lambda: answered(world, conv_id, ("assistant", "Seconde réponse.")) or "done:9"  # noqa: E731

    followed(world, web, conv_id, left, end)

    assert [(call.kwargs["ts"], call.kwargs["text"]) for call in web.chat_update.call_args_list] == [
        (LIVE, "Première réponse."),
        ("1700000902.0", "Seconde réponse."),
    ]
    second = web.chat_postMessage.call_args.kwargs
    assert second["thread_ts"] == THREAD and "Message direct" in second["blocks"][1]["elements"][0]["text"]


def test_a_missed_signal_changes_nothing_the_state_of_the_conversation_decides(mocker, world):
    web, conv_id, _ = started(mocker, world)
    slack_ask.begin(web, EVENT | {"ts": "1700000401.000100", "text": f"<@{BOT}> suite"})
    silent = lambda: answered(world, conv_id, ("assistant", "Première."), flush=True) and None  # noqa: E731
    end = lambda: answered(world, conv_id, ("assistant", "Seconde.")) and None  # noqa: E731

    followed(world, web, conv_id, silent, end)

    assert texts(web) == ["Première.", "Seconde."]


def test_a_mention_arriving_while_the_answer_leaves_keeps_its_own_living_message_and_is_followed(mocker, world):
    web, conv_id, question = started(mocker, world)
    answered(world, conv_id, ("assistant", "Première réponse."))
    late = EVENT | {"ts": "1700000401.000100", "text": f"<@{BOT}> encore"}

    def update(**given):
        if given["text"] == "Première réponse.":
            slack_ask.begin(web, late)
            world.store.add_message(conv_id, "assistant", "Seconde réponse.")
            world.store.end_turn(conv_id, False)

    web.chat_update.side_effect = update

    followed(world, web, conv_id)

    assert [(call.kwargs["ts"], call.kwargs["text"]) for call in web.chat_update.call_args_list] == [
        (LIVE, "Première réponse."),
        ("1700000902.0", "Seconde réponse."),
    ]
    assert world.store.get_conversation(conv_id).slack_message_ts is None
    assert slack_ask.following == {}


def test_a_mention_arriving_between_the_end_of_a_turn_and_its_answer_leaves_each_message_its_own_answer(mocker, world):
    web, conv_id, _ = started(mocker, world)
    late = EVENT | {"ts": "1700000401.000100", "text": f"<@{BOT}> encore"}

    def ended_then_mentioned():
        answered(world, conv_id, ("assistant", "Première réponse."))
        slack_ask.begin(web, late)
        return "done:1"

    end = lambda: answered(world, conv_id, ("assistant", "Seconde réponse.")) or "done:2"  # noqa: E731

    followed(world, web, conv_id, ended_then_mentioned, end)

    assert [(call.kwargs["ts"], call.kwargs["text"]) for call in web.chat_update.call_args_list] == [
        (LIVE, "Première réponse."),
        ("1700000902.0", "Seconde réponse."),
    ]
    assert web.chat_postMessage.call_count == 2
    assert world.store.get_conversation(conv_id).slack_message_ts is None


def test_a_follower_that_cannot_subscribe_follows_by_polling_and_leaves_nothing_behind(mocker, world):
    web, conv_id, _ = started(mocker, world)
    world.runner.subscribe.side_effect = RedisConnectionError("redis")
    waits = iter([lambda: None, lambda: answered(world, conv_id, ("assistant", "Réponse."))])
    mocker.patch.object(slack_ask.asyncio, "sleep", mocker.AsyncMock(side_effect=lambda seconds: next(waits)()))

    asyncio.run(slack_ask.follow(web, conv_id))

    assert texts(web) == ["Réponse."]
    assert slack_ask.following == {}


def test_a_follower_that_fails_at_once_does_not_stay_registered(mocker, world):
    web, conv_id, _ = started(mocker, world)
    mocker.patch.object(world.store, "last_user_message_id", side_effect=RuntimeError("base"))

    with pytest.raises(RuntimeError):
        asyncio.run(slack_ask.follow(web, conv_id))

    assert slack_ask.following == {}
    assert world.redis.keys == {}


def test_a_signal_lost_in_the_middle_of_a_turn_is_followed_by_polling(mocker, world):
    web, conv_id, _ = started(mocker, world)

    def broken():
        raise RedisConnectionError("redis")

    mocker.patch.object(
        slack_ask.asyncio,
        "sleep",
        mocker.AsyncMock(side_effect=lambda seconds: answered(world, conv_id, ("assistant", "Réponse."))),
    )

    followed(world, web, conv_id, broken)

    assert texts(web) == ["Réponse."]


def test_a_conversation_already_followed_by_another_process_is_left_to_it(mocker, world):
    web, conv_id, _ = started(mocker, world)
    world.redis.keys[f"autometa:slack:follow:{conv_id}"] = "autre processus"

    followed(world, web, conv_id)

    web.chat_update.assert_not_called()
    assert world.redis.keys == {f"autometa:slack:follow:{conv_id}": "autre processus"}
    assert slack_ask.following == {}


def test_a_conversation_deleted_while_its_message_lives_has_it_say_so(mocker, world):
    web, conv_id, _ = started(mocker, world)

    followed(world, web, conv_id, lambda: world.store.delete_conversation(conv_id) or "update")

    final = web.chat_update.call_args.kwargs
    assert (final["channel"], final["ts"]) == (CHANNEL, LIVE)
    assert "supprimée" in final["text"]


def test_mentions_left_waiting_by_a_turn_that_failed_are_said_not_to_have_left_and_only_they(mocker, world):
    web, conv_id, _ = started(mocker, world)
    slack_ask.begin(web, EVENT | {"ts": "1700000401.000100"})
    world.store.queue_message(conv_id, "depuis la page")
    answered(world, conv_id, ("assistant", "*Interrompu.*"))

    slack_ask.give_back(web, conv_id)

    assert [e["content"] for e in world.store.pending_messages(conv_id)] == ["depuis la page"]
    said = web.chat_postMessage.call_args.kwargs
    assert said["thread_ts"] == THREAD and "Redemandez-moi" in said["text"]


def test_after_a_restart_the_workspace_is_learnt_and_messages_left_on_a_verb_are_completed(mocker, world, monkeypatch):
    web, conv_id, _ = started(mocker, world)
    answered(world, conv_id, ("assistant", "Réponse."))
    monkeypatch.setattr(slack_ask, "workspace", {"url": "", "bot": "", "loop": None})
    web.auth_test.return_value = {"url": "https://equipe.slack.com/", "user_id": BOT}

    async def restart():
        await slack_ask.resume(web)
        await asyncio.gather(*slack_ask.following.values())

    asyncio.run(restart())

    assert slack_ask.workspace["url"] == "https://equipe.slack.com/"
    assert texts(web) == ["Réponse."]
    assert world.store.slack_live_conversations() == []


def test_a_restart_without_slack_still_follows_what_it_can(mocker, world, caplog, monkeypatch):
    web, conv_id, _ = started(mocker, world, replies=[reply("U2", "avant", "1700000000.000100")])
    monkeypatch.setattr(slack_ask, "workspace", {"url": "", "bot": "", "bot_id": "", "loop": None})
    web.auth_test.side_effect = OSError("réseau")

    async def restart():
        await slack_ask.resume(web)
        return list(slack_ask.following)

    assert asyncio.run(restart()) == [conv_id]
    assert "Espace Slack non lu" in caplog.text


def test_a_mention_queued_by_someone_else_gets_its_own_turn_under_their_identity_and_its_own_message(mocker, world):
    world.store.owners = {"louis@ailleurs.example"}
    web, conv_id, _ = started(mocker, world)
    slack_ask.begin(web, EVENT | {"user": "U2", "ts": "1700000401.000100", "text": f"<@{BOT}> et par région ?"})
    first = lambda: answered(world, conv_id, ("assistant", "Réponse à Camille."), flush=True) or "done:1"  # noqa: E731
    second = lambda: answered(world, conv_id, ("assistant", "Réponse à Louis.")) or "done:9"  # noqa: E731

    followed(world, web, conv_id, first, second)

    world.runner.submit.assert_awaited_once()
    submitted = world.runner.submit.await_args.args
    assert (submitted[0], submitted[3]) == (conv_id, "louis@ailleurs.example")
    assert submitted[1] == "Louis D. (louis@ailleurs.example) : et par région ?"
    assert [(call.kwargs["ts"], call.kwargs["text"]) for call in web.chat_update.call_args_list] == [
        (LIVE, "Réponse à Camille."),
        ("1700000902.0", "Réponse à Louis."),
    ]
    assert world.store.pending_messages(conv_id) == []
    assert world.store.get_conversation(conv_id).turn_user == "louis@ailleurs.example"


def test_queued_requests_leave_one_person_at_a_time_in_order_of_arrival(mocker, world):
    world.store.owners = {"louis@ailleurs.example"}
    web, conv_id, _ = started(mocker, world)
    for user, ts, text in (("U2", "401", "Louis 1"), ("U5", "402", "Noa"), ("U2", "403", "Louis 2")):
        slack_ask.begin(web, EVENT | {"user": user, "ts": f"1700000{ts}.000100", "text": text})
    ends = [lambda: answered(world, conv_id, ("assistant", "ok"), flush=True) and None for _ in range(3)]  # noqa: E731

    followed(world, web, conv_id, *ends)

    assert [(call.args[1], call.args[3]) for call in world.runner.submit.await_args_list] == [
        ("Louis D. (louis@ailleurs.example) : Louis 2", "louis@ailleurs.example"),
        ("Noa (noa@inclusion.gouv.fr) : Noa", "noa@inclusion.gouv.fr"),
    ]
    asked = [content for _, kind, content in world.store.messages[conv_id] if kind == "user"]
    assert [text.rsplit(" : ", 1)[-1] for text in asked[1:]] == ["Louis 1", "Louis 2", "Noa"]


def test_once_the_owner_writes_from_the_site_the_mentions_others_had_waiting_are_turned_away(mocker, world):
    world.store.owners = {"louis@ailleurs.example"}
    web, conv_id, _ = started(mocker, world)
    slack_ask.begin(web, EVENT | {"user": "U2", "ts": "1700000401.000100", "text": "de Louis"})
    slack_ask.begin(web, EVENT | {"ts": "1700000402.000100", "text": "de Camille, par Slack"})
    world.store.update_conversation(conv_id, slack_locked=True)
    world.store.queue_message(conv_id, "de Camille, sur le site")
    web.chat_postEphemeral.reset_mock()
    ends = [lambda: answered(world, conv_id, ("assistant", "ok"), flush=True) and None for _ in range(2)]  # noqa: E731

    followed(world, web, conv_id, *ends)

    told = [call.kwargs for call in web.chat_postEphemeral.call_args_list]
    assert [(said["user"], said["text"]) for said in told] == [
        ("U2", f"Cette conversation se poursuit dans Autometa : {BASE}/c/{conv_id}")
    ]
    asked = [content for _, kind, content in world.store.messages[conv_id] if kind == "user"]
    assert asked[1:] == ["de Camille, par Slack", "de Camille, sur le site"]
    world.runner.submit.assert_not_awaited()


def test_a_request_whose_turn_cannot_be_submitted_gives_its_turn_back_and_is_said_not_to_have_left(mocker, world):
    world.store.owners = {"louis@ailleurs.example"}
    web, conv_id, _ = started(mocker, world)
    slack_ask.begin(web, EVENT | {"user": "U2", "ts": "1700000401.000100"})
    world.runner.submit.side_effect = ConnectionError("redis")

    followed(world, web, conv_id, lambda: answered(world, conv_id, ("assistant", "ok"), flush=True) and None)

    assert world.store.get_conversation(conv_id).needs_response is False
    assert slack_ask.following == {}
    assert any("Redemandez-moi" in call.kwargs["text"] for call in web.chat_postMessage.call_args_list)
    assert texts(web)[-1] == "La demande n'a pas abouti."


def test_a_failure_while_opening_the_next_turn_does_not_stop_the_follower(mocker, world, caplog):
    world.store.owners = {"louis@ailleurs.example"}
    web, conv_id, _ = started(mocker, world)
    slack_ask.begin(web, EVENT | {"user": "U2", "ts": "1700000401.000100", "text": "de Louis"})
    real, calls = world.store.next_turn, []

    def flaky(conv):
        calls.append(conv)
        if len(calls) == 1:
            raise slack_ask.SQLAlchemyError("base")
        return real(conv)

    mocker.patch.object(world.store, "next_turn", side_effect=flaky)
    first = lambda: answered(world, conv_id, ("assistant", "ok"), flush=True) and None  # noqa: E731
    second = lambda: answered(world, conv_id, ("assistant", "Réponse à Louis.")) and None  # noqa: E731

    followed(world, web, conv_id, first, second)

    assert "panne, nouvel essai dans 10 s" in caplog.text
    assert texts(web)[-1] == "Réponse à Louis."
    world.runner.submit.assert_awaited_once()


def test_the_final_answer_waits_in_the_coroutine_and_keeps_the_followers_lock_alive(mocker, world):
    web, conv_id, question = started(mocker, world)
    answered(world, conv_id, ("assistant", "Réponse."))
    web.chat_update.side_effect = [refused(mocker, "ratelimited", "30"), refused(mocker, "ratelimited", "30"), None]
    renew = mocker.AsyncMock()

    asyncio.run(slack_ask.finish(web, conv_id, question, LIVE, renew))

    assert renew.await_count == 3
    assert [call.args[0] for call in slack_ask.asyncio.sleep.await_args_list] == [30, 30]
    slack_ask.time.sleep.assert_not_called()


class Stop(BaseException):
    """Arrête la ronde, que rien d'autre ne termine."""


def swept(web, rounds: int) -> list[str]:
    async def rounds_then_stop():
        slack_ask.asyncio.sleep.side_effect = [*[None] * (rounds - 1), Stop()]
        try:
            await slack_ask.sweep(web)
        except Stop:
            return list(slack_ask.following)

    return asyncio.run(rounds_then_stop())


def test_conversations_waiting_without_a_follower_get_one_from_the_first_round(mocker, world):
    world.store.owners = {"louis@ailleurs.example"}
    web, conv_id, _ = started(mocker, world)
    slack_ask.begin(web, EVENT | {"user": "U2", "ts": "1700000401.000100", "text": "de Louis"})
    answered(world, conv_id, ("assistant", "Réponse à Camille."), flush=True)

    assert swept(web, 1) == [conv_id]


def test_a_server_started_before_its_migrations_says_so_once_and_follows_on_the_next_round(mocker, world, caplog):
    web, conv_id, _ = started(mocker, world)
    missing = ProgrammingError("SELECT", {}, Exception("column conversations.slack_message_ts does not exist"))
    mocker.patch.object(world.store, "slack_live_conversations", side_effect=[missing, [conv_id]])

    assert swept(web, 2) == [conv_id]

    assert caplog.text.count("nouvel essai à la prochaine ronde") == 1
    assert [call.args[0] for call in slack_ask.asyncio.sleep.await_args_list][:2] == [60, 60]


def test_a_workspace_not_read_at_startup_is_read_on_a_later_round(mocker, world, monkeypatch):
    web = slack(mocker)
    monkeypatch.setattr(slack_ask, "workspace", {"url": "", "bot": "", "bot_id": "", "loop": None})
    web.auth_test.side_effect = [OSError("réseau"), {"url": "https://equipe.slack.com/", "user_id": BOT}]

    swept(web, 3)

    assert (slack_ask.workspace["bot"], web.auth_test.call_count) == (BOT, 2)


def test_the_living_message_has_its_verb_in_italics_and_what_it_left_out_in_small_text():
    blocks = slack_ask.live("abcd1234", "mouline", "Canal privé.")["blocks"]

    assert [block["type"] for block in blocks] == ["rich_text", "context", "context"]
    assert blocks[0]["elements"][0]["elements"] == [
        {"type": "text", "text": "Autometa mouline…", "style": {"italic": True}}
    ]
    assert blocks[1]["elements"][0]["text"] == "Canal privé."
