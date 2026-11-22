"""Cartes Slack des liens de conversation : quels liens, quelle carte, quel appel à Slack, quelles pannes."""

import http.client
import json
from datetime import datetime, timezone

import pytest
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientNotConnectedError
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from sqlalchemy.exc import OperationalError

from web import config, slack_listener
from web.stores.records import Conversation

BASE = "https://autometa.example"
SHORT = "0a1b2c3d"
LEGACY = "21e937fb-0000-4000-8000-000000000001"


@pytest.fixture(autouse=True)
def instance(monkeypatch):
    monkeypatch.setattr(config, "BASE_URL", BASE)
    monkeypatch.setattr(slack_listener, "refreshed", {})
    monkeypatch.setattr(slack_listener.slack_charts, "files", {})


def conversation(**fields):
    defaults = {
        "id": SHORT,
        "user_id": "camille.martin@example.org",
        "title": "Candidatures par région",
        "created_at": datetime(2026, 11, 20, 9, 5, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 11, 21, 15, 30, tzinfo=timezone.utc),
    }
    return Conversation(**(defaults | fields))


def known(mocker, conv=None, messages=()):
    mocker.patch.object(slack_listener.store, "get_displayed_messages", return_value=list(messages))
    return mocker.patch.object(slack_listener.store, "get_conversation", return_value=conv or conversation())


POSTED = {
    "channel": "C0TEST",
    "message_ts": "1700000000.000100",
    "unfurl_id": "C0TEST.1700000000.000100.abc",
    "source": "conversations_history",
}
GRID = {"channel": "C0TEST", "message_ts": "1700000000.000100"}


def events_api(event):
    return SocketModeRequest(type="events_api", envelope_id="env-1", payload={"event": event})


def link_shared(urls, **target):
    links = [{"domain": "autometa.example", "url": u} for u in urls]
    return events_api({"type": "link_shared", "links": links, **(target or POSTED)})


def interactive(payload):
    return SocketModeRequest(type="interactive", envelope_id="env-2", payload=payload)


def refresh_click(url, action_id=slack_listener.REFRESH_ACTION):
    return SocketModeRequest(
        type="interactive",
        envelope_id="env-2",
        payload={
            "type": "block_actions",
            "actions": [{"action_id": action_id}],
            "container": {
                "type": "message_attachment",
                "channel_id": "C0TEST",
                "message_ts": "1700000000.000100",
                "is_app_unfurl": True,
                "app_unfurl_url": url,
            },
        },
    )


def card_text(card):
    return json.dumps(card, ensure_ascii=False)


@pytest.mark.parametrize(
    "url,expected",
    [
        (f"{BASE}/c/{SHORT}", SHORT),
        (f"{BASE}/c/{LEGACY}", LEGACY),
        (f"{BASE}/c/{SHORT}/412", SHORT),
        (f"{BASE}/c/{SHORT}/412/table-1-9f3a", SHORT),
        (f"{BASE}/c/{SHORT}?x=1#titre", SHORT),
        (f"{BASE}/explorations/{LEGACY}", LEGACY),
        (f"{BASE}/explorations/{LEGACY}/412", LEGACY),
        ("https://AUTOMETA.example/c/" + SHORT, SHORT),
        (f"https://autre.example/c/{SHORT}", None),
        (f"https://autometa.example.evil.test/c/{SHORT}", None),
        (f"https://evil.test/{BASE}/c/{SHORT}", None),
        (f"{BASE}/c/new", None),
        (f"{BASE}/c/{SHORT}x", None),
        (f"{BASE}/conversations", None),
        (f"{BASE}/interactive/c/{SHORT}", None),
        ("https://[bad/c/" + SHORT, None),
    ],
)
def test_only_a_conversation_address_of_this_instance_names_a_conversation(url, expected):
    assert (slack_listener.located(url) or [None])[0] == expected


@pytest.mark.parametrize(
    "path,expected",
    [
        (f"/c/{SHORT}", (SHORT, None, None)),
        (f"/c/{SHORT}/412", (SHORT, 412, None)),
        (f"/c/{SHORT}/412/table-1-9f3a0c", (SHORT, 412, "table-1-9f3a0c")),
        (f"/explorations/{LEGACY}/7/section-2-00ff00", (LEGACY, 7, "section-2-00ff00")),
        (f"/c/{SHORT}/12345678901", (SHORT, None, None)),
        (f"/c/{SHORT}/abc", (SHORT, None, None)),
        (f"/c/{SHORT}/412/%73ection-1-9f3a0c", (SHORT, 412, "section-1-9f3a0c")),
    ],
)
def test_a_permalink_names_its_message_and_its_element(path, expected):
    assert slack_listener.located(f"{BASE}{path}") == expected


def test_no_address_names_a_conversation_when_the_instance_has_no_public_address(monkeypatch):
    monkeypatch.setattr(config, "BASE_URL", "")

    assert slack_listener.located(f"/c/{SHORT}") is None
    assert slack_listener.located(f"{BASE}/c/{SHORT}") is None


def facts(conv):
    return slack_listener.card(conv)["blocks"][-2]["elements"][0]


@pytest.mark.parametrize(
    "fields,expected",
    [
        ({}, "camille.martin · créée le 20/11/2026 · dernière activité le 21/11/2026"),
        ({"updated_at": datetime(2026, 11, 20, 22, 0, tzinfo=timezone.utc)}, "camille.martin · 20/11/2026"),
        # 23:30 UTC le 20 est déjà le 21 à Paris : le jour compte à l'heure affichée.
        ({"created_at": datetime(2026, 11, 20, 23, 30, tzinfo=timezone.utc)}, "camille.martin · 21/11/2026"),
        ({"user_id": None}, "créée le 20/11/2026 · dernière activité le 21/11/2026"),
        (
            {"needs_response": True},
            "En cours à 09:00 · camille.martin · créée le 20/11/2026 · dernière activité le 21/11/2026",
        ),
    ],
    ids=["two days", "same day", "same local day", "no owner", "running"],
)
def test_the_card_names_author_and_days_and_the_state_only_while_a_turn_runs(mocker, fields, expected):
    mocker.patch.object(slack_listener, "utcnow", return_value=datetime(2026, 11, 22, 8, 0, tzinfo=timezone.utc))

    assert facts(conversation(**fields)) == {"type": "plain_text", "text": expected}


def test_the_card_carries_a_refresh_button():
    actions = [b for b in slack_listener.card(conversation())["blocks"] if b["type"] == "actions"]

    assert [e["action_id"] for e in actions[0]["elements"]] == [slack_listener.REFRESH_ACTION]
    assert actions[0]["elements"][0]["text"]["text"] == "Actualiser"


def title(conv):
    return slack_listener.card(conv)["blocks"][0]["text"]


@pytest.mark.parametrize(
    "written,shown",
    [
        ("Candidatures par région", ":autometa: *Candidatures par région*"),
        (None, ":autometa: *Conversation sans titre*"),
        ("*** ~ `` _", ":autometa: *Conversation sans titre*"),
        ("fin* puis *gras* _penché_ ~barré~ `code`", ":autometa: *fin puis gras penché barré code*"),
        (
            "<!channel> <@U1> <https://evil.example|ici> & co",
            ":autometa: *&lt;!channel&gt; &lt;@U1&gt; &lt;https://evil.example|ici&gt; &amp; co*",
        ),
        ("deux\nlignes  et\ttab", ":autometa: *deux lignes et tab*"),
        ("taux_de_retour", ":autometa: *taux de retour*"),
    ],
)
def test_the_title_is_bold_and_nothing_in_it_is_read_by_slack(written, shown):
    assert title(conversation(title=written)) == {"type": "mrkdwn", "verbatim": True, "text": shown}


@pytest.mark.parametrize(
    "hostile", ["@channel @here #general https://evil.example", "*a* _b_ ~c~ `d` ```e```", "a*b*c"]
)
def test_a_title_cannot_leave_its_bold_nor_format_itself(hostile):
    shown = title(conversation(title=hostile))["text"]

    assert shown.startswith(":autometa: *")
    assert shown.endswith("*")
    assert not set("*_~`<>") & set(shown[12:-1])


def test_the_icon_comes_first_whatever_the_title_holds():
    shown = title(conversation(title=":tada: :autometa: fête"))["text"]

    assert shown == ":autometa: *:tada: :autometa: fête*"


def test_the_author_is_plain_text_slack_does_not_parse():
    assert facts(conversation(user_id="<!channel>@example.org")) == {
        "type": "plain_text",
        "text": "<!channel> · créée le 20/11/2026 · dernière activité le 21/11/2026",
    }


def test_a_shared_conversation_link_gets_its_card_on_the_message(mocker):
    get = known(mocker)
    client = mocker.MagicMock()
    url = f"{BASE}/c/{SHORT}/412"

    slack_listener.handle(client, link_shared([url, "https://autre.example/c/" + SHORT]))

    get.assert_called_once_with(SHORT, include_messages=False)
    client.web_client.chat_unfurl.assert_called_once()
    sent = client.web_client.chat_unfurl.call_args.kwargs
    assert list(sent["unfurls"]) == [url]
    assert "Candidatures par région" in card_text(sent["unfurls"][url])


COMPOSER = {"unfurl_id": "U1", "source": "composer", "channel": "COMPOSER", "message_ts": "U1"}


@pytest.mark.parametrize(
    "target,expected",
    [
        (POSTED, {"unfurl_id": POSTED["unfurl_id"], "source": "conversations_history"}),
        (COMPOSER, {"unfurl_id": "U1", "source": "composer"}),
        (GRID, {"channel": "C0TEST", "ts": "1700000000.000100"}),
    ],
    ids=["posted message", "composer preview", "Enterprise Grid, without unfurl_id"],
)
def test_the_card_is_addressed_by_unfurl_id_when_slack_gives_one_else_by_channel_and_message(mocker, target, expected):
    known(mocker)
    client = mocker.MagicMock()

    slack_listener.handle(client, link_shared([f"{BASE}/c/{SHORT}"], **target))

    sent = client.web_client.chat_unfurl.call_args.kwargs
    assert {key: value for key, value in sent.items() if key != "unfurls"} == expected


def test_every_request_is_acknowledged_before_anything_else(mocker):
    known(mocker)
    client = mocker.MagicMock()

    slack_listener.handle(client, link_shared([f"{BASE}/c/{SHORT}"]))

    assert [call[0] for call in client.mock_calls] == ["send_socket_mode_response", "web_client.chat_unfurl"]
    assert client.send_socket_mode_response.call_args.args[0].envelope_id == "env-1"


@pytest.mark.parametrize(
    "request_",
    [
        link_shared(["https://autre.example/c/" + SHORT, f"{BASE}/conversations"]),
        events_api({"type": "app_mention"}),
        SocketModeRequest(type="slash_commands", envelope_id="e", payload={}),
        refresh_click(f"{BASE}/c/{SHORT}", action_id="something_else"),
        refresh_click("https://autre.example/c/" + SHORT),
    ],
    ids=["foreign links", "other event", "other request", "other button", "refresh of a foreign link"],
)
def test_anything_else_is_acknowledged_and_ignored_without_reading_a_conversation(mocker, request_):
    get = known(mocker)
    client = mocker.MagicMock()

    slack_listener.handle(client, request_)

    client.send_socket_mode_response.assert_called_once()
    get.assert_not_called()
    client.web_client.chat_unfurl.assert_not_called()


def test_a_link_to_an_unknown_conversation_gets_no_card(mocker):
    mocker.patch.object(slack_listener.store, "get_conversation", return_value=None)
    client = mocker.MagicMock()

    slack_listener.handle(client, link_shared([f"{BASE}/c/{SHORT}"]))

    client.web_client.chat_unfurl.assert_not_called()


def test_the_refresh_button_redraws_the_card_from_the_current_state(mocker):
    known(mocker, conversation(needs_response=True))
    client = mocker.MagicMock()
    url = f"{BASE}/c/{SHORT}"

    slack_listener.handle(client, refresh_click(url))

    sent = client.web_client.chat_unfurl.call_args.kwargs
    assert (sent["channel"], sent["ts"]) == ("C0TEST", "1700000000.000100")
    assert "En cours" in card_text(sent["unfurls"][url])


def test_a_card_just_refreshed_is_not_redrawn_again_within_five_seconds(mocker):
    known(mocker)
    clock = mocker.patch.object(slack_listener.time, "monotonic", return_value=100.0)
    client = mocker.MagicMock()
    click = refresh_click(f"{BASE}/c/{SHORT}")

    slack_listener.handle(client, click)
    clock.return_value = 104.9
    slack_listener.handle(client, click)
    slack_listener.handle(client, refresh_click(f"{BASE}/c/{LEGACY}"))
    assert client.web_client.chat_unfurl.call_count == 2

    clock.return_value = 105.0
    slack_listener.handle(client, click)

    assert client.web_client.chat_unfurl.call_count == 3
    assert client.send_socket_mode_response.call_count == 4


def test_the_memory_of_refreshed_cards_stays_bounded(mocker):
    mocker.patch.object(slack_listener.time, "monotonic", return_value=100.0)

    for rank in range(2500):
        slack_listener.just_refreshed(f"{BASE}/c/{rank:08d}")

    assert len(slack_listener.refreshed) <= 1000


CLICK = {"actions": [{"action_id": slack_listener.REFRESH_ACTION}]}


@pytest.mark.parametrize(
    "request_",
    [
        events_api(None),
        SocketModeRequest(type="events_api", envelope_id="e", payload={}),
        events_api({"type": "link_shared", **POSTED}),
        events_api({"type": "link_shared", "links": None, **POSTED}),
        events_api({"type": "link_shared", "links": [{"domain": "autometa.example"}], **POSTED}),
        events_api({"type": "link_shared", "links": [{"url": f"{BASE}/c/{SHORT}"}]}),
        events_api({"type": "link_shared", "links": [{"url": f"{BASE}/c/{SHORT}"}], "message_ts": "1.2"}),
        events_api({"type": "link_shared", "links": [{"url": f"{BASE}/c/{SHORT}"}], "unfurl_id": "U1"}),
        interactive(CLICK),
        interactive(CLICK | {"container": None}),
        interactive(CLICK | {"container": {"app_unfurl_url": f"{BASE}/c/{SHORT}", "channel_id": "C0TEST"}}),
        interactive(CLICK | {"container": {"channel_id": "C0TEST", "message_ts": "1.2"}}),
        interactive({"actions": None}),
    ],
    ids=[
        "null event",
        "no event",
        "no links",
        "null links",
        "link without url",
        "no channel",
        "no channel id",
        "unfurl_id without source",
        "no container",
        "null container",
        "container without message",
        "container without url",
        "null actions",
    ],
)
def test_a_malformed_request_is_acknowledged_and_dropped_without_raising(mocker, request_):
    get = known(mocker)
    client = mocker.MagicMock()

    slack_listener.handle(client, request_)

    client.send_socket_mode_response.assert_called_once()
    get.assert_not_called()
    client.web_client.chat_unfurl.assert_not_called()


def test_an_incomplete_link_event_is_reported_in_our_own_log(mocker, caplog):
    slack_listener.handle(mocker.MagicMock(), events_api({"type": "link_shared", **POSTED}))

    assert "Événement Slack incomplet" in caplog.text


def slack_refusal(mocker):
    return SlackApiError("refused", mocker.MagicMock(get=lambda key: "cannot_unfurl_url"))


@pytest.mark.parametrize(
    "failing,error,logged",
    [
        ("slack", "refusal", "Carte Slack refusée : cannot_unfurl_url"),
        ("slack", TimeoutError("timed out"), "Slack injoignable"),
        ("db", OperationalError("select", {}, Exception("db down")), "conversation illisible"),
    ],
)
def test_a_failure_is_logged_and_leaves_the_listener_running(mocker, caplog, failing, error, logged):
    get = known(mocker)
    client = mocker.MagicMock()
    error = slack_refusal(mocker) if error == "refusal" else error
    (client.web_client.chat_unfurl if failing == "slack" else get).side_effect = error

    slack_listener.handle(client, link_shared([f"{BASE}/c/{SHORT}"]))

    assert logged in caplog.text


@pytest.mark.parametrize(
    "listen,bot,app,base,warned",
    [
        (False, "xoxb-test", "xapp-test", BASE, False),
        (True, "", "xapp-test", BASE, True),
        (True, "xoxb-test", "", BASE, True),
        (True, "xoxb-test", "xapp-test", "", True),
        (True, "xoxb-test", "xapp-test", "autometa.example", True),
        (True, "xoxb-test", "xapp-test", f"{BASE}/prefix", True),
    ],
)
def test_slack_is_not_listened_to_unless_asked_and_fully_configured(
    mocker, monkeypatch, caplog, listen, bot, app, base, warned
):
    monkeypatch.setattr(config, "SLACK_CHAT_LISTEN", listen)
    monkeypatch.setattr(config, "SLACK_CHAT_BOT_TOKEN", bot)
    monkeypatch.setattr(config, "SLACK_CHAT_APP_TOKEN", app)
    monkeypatch.setattr(config, "BASE_URL", base)
    socket = mocker.patch.object(slack_listener, "SocketModeClient")

    assert slack_listener.start() is None

    socket.assert_not_called()
    assert ("Slack non écouté" in caplog.text) is warned


def test_an_instance_that_asks_listens_with_the_chat_app_tokens(mocker, monkeypatch):
    monkeypatch.setattr(config, "SLACK_CHAT_LISTEN", True)
    monkeypatch.setattr(config, "SLACK_CHAT_BOT_TOKEN", "xoxb-test")
    monkeypatch.setattr(config, "SLACK_CHAT_APP_TOKEN", "xapp-test")
    socket = mocker.patch.object(slack_listener, "SocketModeClient")
    socket.return_value.socket_mode_request_listeners = []
    web = mocker.patch.object(slack_listener, "WebClient")
    thread = mocker.patch.object(slack_listener.threading, "Thread")

    client = slack_listener.start()

    assert client is socket.return_value
    assert socket.call_args.kwargs == {"app_token": "xapp-test", "web_client": web.return_value}
    assert web.call_args.kwargs["token"] == "xoxb-test"
    assert client.socket_mode_request_listeners == [slack_listener.handle]
    assert thread.call_args.kwargs["target"] is slack_listener.connect
    assert thread.call_args.kwargs["daemon"] is True
    thread.return_value.start.assert_called_once()


def test_the_first_connection_is_tried_again_until_slack_answers(mocker, caplog):
    sleep = mocker.patch.object(slack_listener.time, "sleep")
    client = mocker.MagicMock(closed=False)
    client.connect.side_effect = [
        OSError("unreachable"),
        slack_refusal(mocker),
        SlackClientNotConnectedError("not connected"),
        http.client.IncompleteRead(b""),
        None,
    ]

    slack_listener.connect(client)

    assert client.connect.call_count == 5
    assert sleep.call_count == 4
    assert "Connexion à Slack impossible" in caplog.text
    client.close.assert_not_called()


def test_a_listener_closed_while_it_connects_is_closed_again_once_connected(mocker):
    client = mocker.MagicMock(closed=False)
    client.connect.side_effect = lambda: setattr(client, "closed", True)

    slack_listener.connect(client)

    client.close.assert_called_once()


def test_a_closed_listener_stops_trying_to_connect(mocker):
    client = mocker.MagicMock(closed=True)

    slack_listener.connect(client)

    client.connect.assert_not_called()


def test_a_raw_slack_envelope_goes_through_the_real_client_to_a_card(mocker):
    known(mocker)
    web = mocker.MagicMock(spec=WebClient)
    client = SocketModeClient(app_token="xapp-test", web_client=web)
    client.socket_mode_request_listeners.append(slack_listener.handle)
    acknowledged = mocker.patch.object(client, "send_message")
    url = f"{BASE}/c/{SHORT}"
    envelope = {
        "type": "events_api",
        "envelope_id": "env-9",
        "accepts_response_payload": False,
        "payload": {
            "type": "event_callback",
            "event": {
                "type": "link_shared",
                **POSTED,
                "links": [{"domain": "autometa.example", "url": url}],
            },
        },
    }

    try:
        client.run_message_listeners(envelope, json.dumps(envelope))
    finally:
        client.close()

    assert json.loads(acknowledged.call_args.args[0]) == {"envelope_id": "env-9"}
    assert list(web.chat_unfurl.call_args.kwargs["unfurls"]) == [url]


def test_a_permalink_gets_the_card_with_the_excerpt_between_title_and_facts(mocker):
    known(mocker, messages=[(1, "user", "Question"), (2, "assistant", "La réponse **tient** en une ligne.")])
    client = mocker.MagicMock()
    url = f"{BASE}/c/{SHORT}/2"

    slack_listener.handle(client, link_shared([url]))

    shown = [block for block in client.web_client.chat_unfurl.call_args.kwargs["unfurls"][url]["blocks"]]
    assert [block["type"] for block in shown] == ["section", "section", "context", "actions"]
    assert shown[0]["text"]["text"] == ":autometa: *Candidatures par région*"
    assert shown[1]["text"]["text"] == "La réponse tient en une ligne."


def test_refreshing_a_permalink_card_keeps_its_excerpt(mocker):
    known(mocker, messages=[(2, "assistant", "Toujours là.")])
    client = mocker.MagicMock()
    url = f"{BASE}/c/{SHORT}/2"

    slack_listener.handle(client, refresh_click(url))

    assert "Toujours là." in card_text(client.web_client.chat_unfurl.call_args.kwargs["unfurls"][url])


def test_a_long_or_direction_changing_title_is_cut_and_cleaned_on_the_card():
    shown = title(conversation(title=f"\u202e{'mot ' * 100}"))["text"]

    assert shown.startswith(":autometa: *mot mot")
    assert shown.endswith("mot …*")
    assert len(shown) <= 165


@pytest.mark.parametrize("error", [IndexError("x"), ValueError("x"), TypeError("x"), RecursionError("x")])
def test_an_excerpt_that_cannot_be_built_leaves_its_card_and_the_other_links_theirs(mocker, caplog, error):
    known(mocker, messages=[(2, "assistant", "Lisible.")])
    real = slack_listener.slack_excerpts.excerpt
    mocker.patch.object(
        slack_listener.slack_excerpts,
        "excerpt",
        side_effect=lambda conv, message_id, anchor: (
            real(conv, message_id, anchor) if message_id == 2 else raise_(error)
        ),
    )
    client = mocker.MagicMock()
    broken, fine = f"{BASE}/c/{SHORT}/1", f"{BASE}/c/{SHORT}/2"

    slack_listener.handle(client, link_shared([broken, fine]))

    unfurls = client.web_client.chat_unfurl.call_args.kwargs["unfurls"]
    assert [block["type"] for block in unfurls[broken]["blocks"]] == ["section", "context", "actions"]
    assert "Lisible." in card_text(unfurls[fine])
    assert "Extrait Slack impossible" in caplog.text


def raise_(error):
    raise error


CHART_ANSWER = "```mermaid\npie title Parts\n```\n"


def chart_link(mocker, monkeypatch, images=True):
    """Un lien vers une réponse faite d'un graphique, sur une instance qui montre ou non les graphiques en image."""
    monkeypatch.setattr(config, "SLACK_CHART_IMAGES", images)
    known(mocker, messages=[(2, "assistant", CHART_ANSWER)])
    mocker.patch.object(slack_listener.time, "sleep")
    mocker.patch.object(slack_listener.slack_charts.mermaid_png, "render", return_value=b"\x89PNG")
    client = mocker.MagicMock()
    client.web_client.files_upload_v2.return_value = {"files": [{"id": "F0TEST"}]}
    return client, f"{BASE}/c/{SHORT}/2"


def sent_kinds(client, url):
    return [
        [block["type"] for block in call.kwargs["unfurls"][url]["blocks"]]
        for call in client.web_client.chat_unfurl.call_args_list
    ]


def test_a_chart_link_gets_its_card_at_once_then_again_with_the_image(mocker, monkeypatch):
    client, url = chart_link(mocker, monkeypatch)

    slack_listener.handle(client, link_shared([url]))

    assert sent_kinds(client, url) == [
        ["section", "section", "context", "actions"],
        ["section", "image", "context", "actions"],
    ]
    first, second = client.web_client.chat_unfurl.call_args_list
    assert first.kwargs["unfurls"][url]["blocks"][1]["text"]["text"] == "Graphique : Parts"
    assert second.kwargs["unfurls"][url]["blocks"][1]["slack_file"] == {"id": "F0TEST"}
    assert {k: v for k, v in first.kwargs.items() if k != "unfurls"} == {
        k: v for k, v in second.kwargs.items() if k != "unfurls"
    }


def test_refreshing_a_chart_card_shows_the_image_at_once_without_drawing_or_sending_it_again(mocker, monkeypatch):
    client, url = chart_link(mocker, monkeypatch)
    slack_listener.handle(client, link_shared([url]))
    client.web_client.chat_unfurl.reset_mock()

    slack_listener.handle(client, refresh_click(url))

    assert sent_kinds(client, url) == [["section", "image", "context", "actions"]]
    assert slack_listener.slack_charts.mermaid_png.render.call_count == 1
    assert client.web_client.files_upload_v2.call_count == 1


def test_without_the_opt_in_a_chart_is_named_and_never_drawn(mocker, monkeypatch):
    client, url = chart_link(mocker, monkeypatch, images=False)

    slack_listener.handle(client, link_shared([url]))

    assert sent_kinds(client, url) == [["section", "section", "context", "actions"]]
    slack_listener.slack_charts.mermaid_png.render.assert_not_called()
    client.web_client.files_upload_v2.assert_not_called()


def test_a_chart_that_cannot_be_drawn_leaves_the_card_posted_without_image(mocker, monkeypatch):
    client, url = chart_link(mocker, monkeypatch)
    slack_listener.slack_charts.mermaid_png.render.return_value = None

    slack_listener.handle(client, link_shared([url]))

    assert sent_kinds(client, url) == [["section", "section", "context", "actions"]]


def test_the_image_is_tried_from_three_seconds_on_every_two_seconds_then_given_up(mocker, monkeypatch, caplog):
    caplog.set_level("INFO")
    client, url = chart_link(mocker, monkeypatch)
    not_ready = SlackApiError("refused", mocker.MagicMock(get={"error": "cannot_parse_attachment"}.get))
    client.web_client.chat_unfurl.side_effect = [None] + [not_ready] * 7

    slack_listener.handle(client, link_shared([url]))

    assert (
        sent_kinds(client, url)
        == [["section", "section", "context", "actions"]] + [["section", "image", "context", "actions"]] * 7
    )
    assert [call.args[0] for call in slack_listener.time.sleep.call_args_list] == [3, 2, 2, 2, 2, 2, 2]
    early = [r for r in caplog.records if "pas encore acceptée" in r.getMessage()]
    assert [r.levelname for r in early] == ["INFO"] * 7
    assert [r.levelname for r in caplog.records if "laissée sans son image" in r.getMessage()] == ["WARNING"]


def test_the_image_joins_the_card_as_soon_as_slack_accepts_it(mocker, monkeypatch, caplog):
    caplog.set_level("INFO")
    client, url = chart_link(mocker, monkeypatch)
    not_ready = SlackApiError("refused", mocker.MagicMock(get={"error": "cannot_parse_attachment"}.get))
    client.web_client.chat_unfurl.side_effect = [None, not_ready, not_ready, None]

    slack_listener.handle(client, link_shared([url]))

    assert client.web_client.chat_unfurl.call_count == 4
    assert [call.args[0] for call in slack_listener.time.sleep.call_args_list] == [3, 2, 2]
    assert "reposée avec son image" in caplog.text
    assert not [r for r in caplog.records if r.levelname == "WARNING"]


def test_an_unexpected_refusal_of_the_image_is_a_warning_naming_slack_error(mocker, monkeypatch, caplog):
    client, url = chart_link(mocker, monkeypatch)
    client.web_client.chat_unfurl.side_effect = [None, refused(mocker, "invalid_blocks"), None]

    slack_listener.handle(client, link_shared([url]))

    assert [r.levelname for r in caplog.records if "invalid_blocks" in r.getMessage()] == ["WARNING"]


def test_a_card_slack_refuses_with_its_known_image_is_posted_without_it(mocker, monkeypatch, caplog):
    client, url = chart_link(mocker, monkeypatch)
    slack_listener.handle(client, link_shared([url]))
    client.web_client.chat_unfurl.reset_mock()
    refused = SlackApiError("refused", mocker.MagicMock(get={"error": "invalid_blocks"}.get))
    client.web_client.chat_unfurl.side_effect = [refused, None]

    slack_listener.handle(client, refresh_click(url))

    assert sent_kinds(client, url) == [
        ["section", "image", "context", "actions"],
        ["section", "section", "context", "actions"],
    ]
    assert "(tableau Slack : True, image : True), reposée autrement : invalid_blocks" in caplog.text


def test_a_card_without_image_that_slack_refuses_is_not_sent_twice(mocker, monkeypatch, caplog):
    client, url = chart_link(mocker, monkeypatch, images=False)
    client.web_client.chat_unfurl.side_effect = SlackApiError(
        "refused", mocker.MagicMock(get={"error": "cannot_unfurl_url"}.get)
    )

    slack_listener.handle(client, link_shared([url]))

    assert client.web_client.chat_unfurl.call_count == 1
    assert "Carte Slack refusée : cannot_unfurl_url" in caplog.text


TABLE_ANSWER = "| Mois | Orientations |\n|---|---|\n| 2026-04 | 8 412 |\n"


def refused(mocker, error="invalid_blocks"):
    return SlackApiError("refused", mocker.MagicMock(get={"error": error}.get))


def test_a_table_is_posted_as_a_slack_table_block(mocker):
    known(mocker, messages=[(2, "assistant", TABLE_ANSWER)])
    client = mocker.MagicMock()
    url = f"{BASE}/c/{SHORT}/2"

    slack_listener.handle(client, link_shared([url]))

    assert sent_kinds(client, url) == [["section", "table", "context", "actions"]]


def test_a_card_slack_refuses_with_a_table_block_is_posted_again_at_once_in_monospace(mocker, caplog):
    known(mocker, messages=[(2, "assistant", TABLE_ANSWER)])
    client = mocker.MagicMock()
    client.web_client.chat_unfurl.side_effect = [refused(mocker), None]
    url = f"{BASE}/c/{SHORT}/2"

    slack_listener.handle(client, link_shared([url]))

    assert sent_kinds(client, url) == [
        ["section", "table", "context", "actions"],
        ["section"] * 2 + ["context", "actions"],
    ]
    fallback = client.web_client.chat_unfurl.call_args.kwargs["unfurls"][url]["blocks"][1]["text"]
    assert fallback["text"].startswith("```\nMois")
    assert "(tableau Slack : True, image : True), reposée autrement : invalid_blocks" in caplog.text


def test_when_one_card_of_a_message_is_refused_all_its_cards_fall_back_together(mocker):
    known(mocker, messages=[(2, "assistant", TABLE_ANSWER), (3, "user", "Q"), (4, "assistant", "Du texte.")])
    client = mocker.MagicMock()
    client.web_client.chat_unfurl.side_effect = [refused(mocker), None]
    table, text = f"{BASE}/c/{SHORT}/2", f"{BASE}/c/{SHORT}/4"

    slack_listener.handle(client, link_shared([table, text]))

    last = client.web_client.chat_unfurl.call_args.kwargs["unfurls"]
    assert set(last) == {table, text}
    assert "table" not in [block["type"] for block in last[table]["blocks"]]
    assert "Du texte." in card_text(last[text])


def test_refreshing_a_table_card_tries_the_table_block_again_then_falls_back(mocker):
    known(mocker, messages=[(2, "assistant", TABLE_ANSWER)])
    client = mocker.MagicMock()
    client.web_client.chat_unfurl.side_effect = [refused(mocker), None]
    url = f"{BASE}/c/{SHORT}/2"

    slack_listener.handle(client, refresh_click(url))

    assert [kinds[1] for kinds in sent_kinds(client, url)] == ["table", "section"]


def test_a_card_refused_in_every_form_is_given_up_and_logged(mocker, caplog):
    known(mocker, messages=[(2, "assistant", TABLE_ANSWER)])
    client = mocker.MagicMock()
    client.web_client.chat_unfurl.side_effect = refused(mocker, "cannot_unfurl_url")

    slack_listener.handle(client, link_shared([f"{BASE}/c/{SHORT}/2"]))

    assert client.web_client.chat_unfurl.call_count == 2
    assert "Carte Slack refusée : cannot_unfurl_url" in caplog.text


def test_a_card_with_a_table_and_an_image_drops_the_table_block_first_then_the_image(mocker, monkeypatch):
    monkeypatch.setattr(config, "SLACK_CHART_IMAGES", False)
    known(
        mocker,
        messages=[(2, "assistant", TABLE_ANSWER), (3, "user", "Q"), (4, "assistant", CHART_ANSWER)],
    )
    monkeypatch.setitem(slack_listener.slack_charts.files, slack_listener.slack_charts.key("pie title Parts"), "F0TEST")
    client = mocker.MagicMock()
    client.web_client.chat_unfurl.side_effect = [refused(mocker), refused(mocker), None]
    table, chart = f"{BASE}/c/{SHORT}/2", f"{BASE}/c/{SHORT}/4"

    slack_listener.handle(client, link_shared([table, chart]))

    tried = [
        (call.kwargs["unfurls"][table]["blocks"][1]["type"], call.kwargs["unfurls"][chart]["blocks"][1]["type"])
        for call in client.web_client.chat_unfurl.call_args_list
    ]
    assert tried == [("table", "image"), ("section", "image"), ("table", "section")]


def test_the_image_joins_a_card_in_the_table_form_slack_accepted(mocker, monkeypatch):
    client, chart = chart_link(mocker, monkeypatch)
    slack_listener.store.get_displayed_messages.return_value = [
        (2, "assistant", CHART_ANSWER),
        (3, "user", "Q"),
        (4, "assistant", TABLE_ANSWER),
    ]
    client.web_client.chat_unfurl.side_effect = [refused(mocker), None, None]
    table = f"{BASE}/c/{SHORT}/4"

    slack_listener.handle(client, link_shared([chart, table]))

    last = client.web_client.chat_unfurl.call_args.kwargs["unfurls"]
    assert last[chart]["blocks"][1]["type"] == "image"
    assert last[table]["blocks"][1]["type"] == "section"


def work_object_links(mocker, monkeypatch, on=True, answer="Du texte."):
    """Une instance aux Work Objects, l'adresse d'une conversation et un permalien vers sa réponse."""
    monkeypatch.setattr(config, "SLACK_WORK_OBJECTS", on)
    known(mocker, messages=[(1, "user", "Une question ?"), (2, "assistant", answer)])
    return mocker.MagicMock(), f"{BASE}/c/{SHORT}", f"{BASE}/c/{SHORT}/2"


def entity_urls(call):
    return [entity["app_unfurl_url"] for entity in call.kwargs["metadata"]["entities"]]


@pytest.mark.parametrize("path", [f"/c/{SHORT}", f"/explorations/{LEGACY}", f"/c/{SHORT}?x=1#titre"])
def test_a_conversation_link_is_posted_as_a_work_object_alone(mocker, monkeypatch, path):
    client, _, _ = work_object_links(mocker, monkeypatch)

    slack_listener.handle(client, link_shared([BASE + path, "https://autre.example/c/" + SHORT]))

    sent = client.web_client.chat_unfurl.call_args.kwargs
    assert "unfurls" not in sent
    assert (sent["unfurl_id"], sent["source"]) == (POSTED["unfurl_id"], "conversations_history")
    assert entity_urls(client.web_client.chat_unfurl.call_args) == [BASE + path]
    payload = sent["metadata"]["entities"][0]["entity_payload"]
    assert payload["attributes"]["title"] == {"text": "Candidatures par région"}
    assert set(payload["fields"]) == {"created_by", "date_created", "date_updated"}
    client.web_client.chat_unfurl.assert_called_once()


def test_a_permalink_keeps_its_block_card_and_is_no_work_object(mocker, monkeypatch):
    client, _, permalink = work_object_links(mocker, monkeypatch)

    slack_listener.handle(client, link_shared([permalink]))

    sent = client.web_client.chat_unfurl.call_args.kwargs
    assert "metadata" not in sent
    assert [block["type"] for block in sent["unfurls"][permalink]["blocks"]] == [
        "section",
        "section",
        "context",
        "actions",
    ]
    client.web_client.chat_unfurl.assert_called_once()


def test_a_message_with_both_kinds_gets_objects_and_cards_in_one_call(mocker, monkeypatch, caplog):
    caplog.set_level("INFO")
    client, conv, permalink = work_object_links(mocker, monkeypatch)

    slack_listener.handle(client, link_shared([permalink, conv]))

    client.web_client.chat_unfurl.assert_called_once()
    assert entity_urls(client.web_client.chat_unfurl.call_args) == [conv]
    assert list(client.web_client.chat_unfurl.call_args.kwargs["unfurls"]) == [permalink]
    assert "Work Objects et cartes Slack posés en un appel : 1 et 1" in caplog.text


def test_objects_and_cards_refused_together_are_posted_in_two_calls(mocker, monkeypatch, caplog):
    caplog.set_level("INFO")
    client, conv, permalink = work_object_links(mocker, monkeypatch)
    client.web_client.chat_unfurl.side_effect = [refused(mocker, "invalid_arguments"), None, None]

    slack_listener.handle(client, link_shared([permalink, conv]))

    _, objects, cards = client.web_client.chat_unfurl.call_args_list
    assert entity_urls(objects) == [conv]
    assert "unfurls" not in objects.kwargs
    assert list(cards.kwargs["unfurls"]) == [permalink]
    assert "metadata" not in cards.kwargs
    assert "Work Objects et cartes Slack refusés en un appel, posés en deux : invalid_arguments" in caplog.text
    assert "Work Objects Slack posés : 1" in caplog.text


@pytest.mark.parametrize("with_permalink", [True, False], ids=["both kinds", "conversation alone"])
def test_refused_work_objects_give_way_to_block_cards_for_every_link(mocker, monkeypatch, caplog, with_permalink):
    client, conv, permalink = work_object_links(mocker, monkeypatch)
    urls = [permalink, conv] if with_permalink else [conv]
    refusals = [refused(mocker, "invalid_metadata_format")] * (2 if with_permalink else 1)
    client.web_client.chat_unfurl.side_effect = [*refusals, None]

    slack_listener.handle(client, link_shared(urls))

    last = client.web_client.chat_unfurl.call_args.kwargs
    assert "metadata" not in last
    assert list(last["unfurls"]) == urls
    assert "Candidatures par région" in card_text(last["unfurls"][conv])
    assert "Work Objects Slack refusés, cartes posées à la place : invalid_metadata_format" in caplog.text


def test_without_the_opt_in_a_conversation_link_gets_its_block_card(mocker, monkeypatch):
    client, conv, _ = work_object_links(mocker, monkeypatch, on=False)

    slack_listener.handle(client, link_shared([conv]))

    sent = client.web_client.chat_unfurl.call_args.kwargs
    assert "metadata" not in sent
    assert list(sent["unfurls"]) == [conv]


def test_slack_native_refresh_posts_again_the_objects_and_cards_it_names(mocker, monkeypatch):
    client, conv, permalink = work_object_links(mocker, monkeypatch)

    slack_listener.handle(client, link_shared([conv, permalink], **POSTED, is_unfurl_refresh=True))

    assert entity_urls(client.web_client.chat_unfurl.call_args) == [conv]
    assert list(client.web_client.chat_unfurl.call_args.kwargs["unfurls"]) == [permalink]


def test_our_refresh_button_redraws_its_card_and_leaves_the_object_alone(mocker, monkeypatch):
    client, _, permalink = work_object_links(mocker, monkeypatch)

    slack_listener.handle(client, refresh_click(permalink))

    sent = client.web_client.chat_unfurl.call_args.kwargs
    assert "metadata" not in sent
    assert list(sent["unfurls"]) == [permalink]


def test_the_chart_image_joins_its_card_in_the_call_that_carried_the_object(mocker, monkeypatch):
    client, permalink = chart_link(mocker, monkeypatch)
    monkeypatch.setattr(config, "SLACK_WORK_OBJECTS", True)
    conv = f"{BASE}/c/{SHORT}"

    slack_listener.handle(client, link_shared([conv, permalink]))

    first, second = client.web_client.chat_unfurl.call_args_list
    assert first.kwargs["unfurls"][permalink]["blocks"][1]["type"] == "section"
    assert second.kwargs["unfurls"][permalink]["blocks"][1]["type"] == "image"
    assert entity_urls(first) == entity_urls(second) == [conv]


def test_the_chart_image_joins_its_card_alone_when_the_object_went_in_its_own_call(mocker, monkeypatch):
    client, permalink = chart_link(mocker, monkeypatch)
    monkeypatch.setattr(config, "SLACK_WORK_OBJECTS", True)
    client.web_client.chat_unfurl.side_effect = [refused(mocker, "invalid_arguments"), None, None, None]

    slack_listener.handle(client, link_shared([f"{BASE}/c/{SHORT}", permalink]))

    last = client.web_client.chat_unfurl.call_args
    assert last.kwargs["unfurls"][permalink]["blocks"][1]["type"] == "image"
    assert "metadata" not in last.kwargs


def details_requested(**event):
    return events_api({"type": "entity_details_requested", **event})


def test_opening_a_work_object_fills_its_details_pane_with_the_conversation(mocker, monkeypatch):
    client, url, _ = work_object_links(mocker, monkeypatch)

    slack_listener.handle(client, details_requested(app_unfurl_url=url, entity_url=url, trigger_id="T1"))

    client.send_socket_mode_response.assert_called_once()
    sent = client.web_client.entity_presentDetails.call_args.kwargs
    assert sent["trigger_id"] == "T1"
    assert sent["metadata"]["url"] == url
    assert "app_unfurl_url" not in sent["metadata"]
    assert sent["metadata"]["entity_payload"]["attributes"]["title"] == {"text": "Candidatures par région"}
    assert {field["key"]: field["value"] for field in sent["metadata"]["entity_payload"]["custom_fields"]} == {
        "question": "Une question ?",
        "answer": "Du texte.",
    }
    client.web_client.chat_unfurl.assert_not_called()


def test_the_link_itself_carries_none_of_the_details(mocker, monkeypatch):
    client, url, _ = work_object_links(mocker, monkeypatch)

    slack_listener.handle(client, link_shared([url]))

    sent = client.web_client.chat_unfurl.call_args.kwargs["metadata"]["entities"][0]
    assert sent["entity_payload"]["custom_fields"] == []


def test_a_details_pane_refused_with_its_fields_is_filled_without_them(mocker, monkeypatch, caplog):
    client, url, _ = work_object_links(mocker, monkeypatch)
    client.web_client.entity_presentDetails.side_effect = [refused(mocker, "invalid_metadata"), None]

    slack_listener.handle(client, details_requested(app_unfurl_url=url, trigger_id="T1"))

    first, second = client.web_client.entity_presentDetails.call_args_list
    assert first.kwargs["metadata"]["entity_payload"]["custom_fields"]
    assert second.kwargs["metadata"]["entity_payload"]["custom_fields"] == []
    assert "Volet de détails Slack refusé avec ses champs, rempli sans eux : invalid_metadata" in caplog.text


def test_details_that_cannot_be_read_leave_the_pane_with_the_object_alone(mocker, monkeypatch, caplog):
    client, url, _ = work_object_links(mocker, monkeypatch)
    mocker.patch.object(slack_listener.slack_entities, "details", side_effect=ValueError("x"))

    slack_listener.handle(client, details_requested(app_unfurl_url=url, trigger_id="T1"))

    sent = client.web_client.entity_presentDetails.call_args.kwargs["metadata"]
    assert sent["entity_payload"]["custom_fields"] == []
    assert "Détails Slack impossibles pour la conversation" in caplog.text


def test_details_of_an_unknown_conversation_are_answered_not_found(mocker, monkeypatch):
    client, url, _ = work_object_links(mocker, monkeypatch)
    slack_listener.store.get_conversation.return_value = None

    slack_listener.handle(client, details_requested(entity_url=url, trigger_id="T1"))

    client.web_client.entity_presentDetails.assert_called_once_with(trigger_id="T1", error={"status": "not_found"})


@pytest.mark.parametrize(
    "event",
    [
        {"trigger_id": "T1"},
        {"app_unfurl_url": f"{BASE}/c/{SHORT}"},
        {"app_unfurl_url": "https://autre.example/c/" + SHORT, "trigger_id": "T1"},
    ],
    ids=["no address", "no trigger", "foreign address"],
)
def test_details_asked_for_nothing_this_instance_can_answer_are_acknowledged_and_dropped(mocker, monkeypatch, event):
    client, _, _ = work_object_links(mocker, monkeypatch)

    slack_listener.handle(client, details_requested(**event))

    client.send_socket_mode_response.assert_called_once()
    client.web_client.entity_presentDetails.assert_not_called()


def test_details_are_not_answered_when_work_objects_are_off(mocker, monkeypatch):
    client, url, _ = work_object_links(mocker, monkeypatch, on=False)

    slack_listener.handle(client, details_requested(app_unfurl_url=url, trigger_id="T1"))

    client.web_client.entity_presentDetails.assert_not_called()


def test_a_refused_details_pane_is_logged_and_leaves_the_listener_running(mocker, monkeypatch, caplog):
    client, url, _ = work_object_links(mocker, monkeypatch)
    client.web_client.entity_presentDetails.side_effect = refused(mocker, "invalid_metadata")

    slack_listener.handle(client, details_requested(app_unfurl_url=url, trigger_id="T1"))

    assert "invalid_metadata" in caplog.text
