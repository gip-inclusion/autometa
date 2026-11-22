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


@pytest.mark.parametrize(
    "needs_response,state,other",
    [(True, "En cours", "Terminée"), (False, "Terminée", "En cours")],
)
def test_the_card_gives_title_author_dates_and_state_in_french(mocker, needs_response, state, other):
    mocker.patch.object(slack_listener, "utcnow", return_value=datetime(2026, 11, 22, 8, 0, tzinfo=timezone.utc))

    text = card_text(slack_listener.card(conversation(needs_response=needs_response)))

    assert "Candidatures par région" in text
    assert "camille.martin" in text
    assert "@example.org" not in text
    assert "créée le 20/11/2026 à 10:05" in text
    assert "dernière activité le 21/11/2026 à 16:30" in text
    assert "état relevé le 22/11/2026 à 09:00" in text
    assert state in text
    assert other not in text


def test_the_card_carries_a_refresh_button():
    actions = [b for b in slack_listener.card(conversation())["blocks"] if b["type"] == "actions"]

    assert [e["action_id"] for e in actions[0]["elements"]] == [slack_listener.REFRESH_ACTION]
    assert actions[0]["elements"][0]["text"]["text"] == "Actualiser"


def texts(node):
    if isinstance(node, dict):
        return ([node] if "text" in node and isinstance(node["text"], str) else []) + texts(list(node.values()))
    return [found for child in node for found in texts(child)] if isinstance(node, list) else []


@pytest.mark.parametrize(
    "fields",
    [
        {"title": "@channel voir <!here> #general https://evil.test *gras* <https://evil.test|ici>"},
        {"user_id": "<!channel>@example.org"},
    ],
    ids=["title", "author"],
)
def test_nothing_taken_from_the_conversation_is_read_by_slack_as_markup(fields):
    conv = conversation(**fields)

    shown = texts(slack_listener.card(conv))

    assert {text["type"] for text in shown} == {"plain_text"}
    assert shown[0]["text"] == conv.title
    assert conv.user_id.split("@")[0] in shown[1]["text"]


def test_a_conversation_without_title_still_gets_one_on_its_card():
    assert slack_listener.card(conversation(title=None))["blocks"][0]["text"]["text"] == "Conversation sans titre"


def test_a_conversation_without_owner_gets_a_card_without_author():
    facts = slack_listener.card(conversation(user_id=None))["blocks"][1]["elements"][0]["text"]

    assert facts.startswith("✅ Terminée · créée le")


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
    assert shown[0]["text"]["text"] == "Candidatures par région"
    assert shown[1]["text"]["text"] == "La réponse tient en une ligne."


def test_refreshing_a_permalink_card_keeps_its_excerpt(mocker):
    known(mocker, messages=[(2, "assistant", "Toujours là.")])
    client = mocker.MagicMock()
    url = f"{BASE}/c/{SHORT}/2"

    slack_listener.handle(client, refresh_click(url))

    assert "Toujours là." in card_text(client.web_client.chat_unfurl.call_args.kwargs["unfurls"][url])


def test_a_long_or_direction_changing_title_is_cut_and_cleaned_on_the_card():
    shown = slack_listener.card(conversation(title=f"\u202e{'mot ' * 100}"))["blocks"][0]["text"]["text"]

    assert shown.startswith("mot mot")
    assert shown.endswith("mot …")
    assert len(shown) <= 152


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
