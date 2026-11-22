"""Demander à Autometa depuis Slack : la conversation, son fil, son contexte."""

import json
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from web import conversation_html, slack_ask
from web.stores.records import Conversation

CONV = "0a1b2c3d"
TEMPLATES = Environment(
    loader=FileSystemLoader(Path(__file__).parent.parent / "web" / "templates"), autoescape=select_autoescape()
)


@pytest.mark.parametrize(
    ("workspace", "expected"),
    [
        ("", "https://slack.com/app_redirect?channel=C0TEST"),
        (
            "https://equipe.slack.com/",
            "https://equipe.slack.com/archives/C0TEST/p1700000000000100?thread_ts=1700000000.000100&cid=C0TEST",
        ),
    ],
    ids=["workspace unknown", "workspace known"],
)
def test_the_thread_of_a_conversation_has_an_address_computed_from_its_channel_and_thread(
    monkeypatch, workspace, expected
):
    monkeypatch.setitem(slack_ask.workspace, "url", workspace)
    conv = Conversation(id=CONV, origin="slack", slack_channel="C0TEST", slack_thread_ts="1700000000.000100")

    assert slack_ask.thread_url(conv) == expected


def context(*messages, note=""):
    return json.dumps({"messages": [dict(zip(("author", "at", "text"), m)) for m in messages], "note": note})


def test_the_slack_context_is_a_block_of_its_own_folded_under_the_question():
    thread = context(("Camille Martin", "22/11 14:05", "Bonjour\n<b>à tous</b>"), ("Louis", "22/11 14:06", "Oui."))
    messages = [(1, "user", "Une question ?"), (2, "slack_context", thread), (3, "assistant", "Une réponse.")]

    found = conversation_html.thread(CONV, messages)["blocks"]

    assert [(b["kind"], b["ids"]) for b in found] == [("user", [1]), ("slack_context", [2]), ("assistant", [3])]
    html = str(found[1]["html"])
    assert html.startswith("<details><summary>") and "Contexte du fil Slack · 2 messages" in html
    assert "<strong>Camille Martin</strong> <span>22/11 14:05</span><br>Bonjour<br>&lt;b&gt;à tous&lt;/b&gt;" in html
    assert found[2].get("final") is True


def test_a_slack_context_ends_the_answer_before_it_and_starts_no_turn():
    messages = [
        (1, "user", "Q"),
        (2, "assistant", "a"),
        (3, "slack_context", context(("A", "x", "y"))),
        (4, "assistant", "b"),
    ]

    found = conversation_html.thread(CONV, messages)["blocks"]

    assert [b["ids"] for b in found if b["kind"] == "assistant"] == [[2], [4]]
    assert [b.get("final") for b in found if b["kind"] == "assistant"] == [None, True]


@pytest.mark.parametrize(
    "content", ["pas du JSON", "[]", json.dumps({"messages": "x"}), context(), json.dumps({"through": "1.0"})]
)
def test_a_slack_context_without_messages_or_that_cannot_be_read_shows_nothing(content):
    found = conversation_html.thread(CONV, [(1, "user", "Q"), (2, "slack_context", content)])["blocks"]

    assert found[1]["html"] == ""
    html = TEMPLATES.get_template("_conversation_blocks.html").render(blocks=found)
    assert '<div class="event-block event-slack_context" data-msg-id="2"></div>' in html


def test_a_slack_context_says_what_it_did_not_take():
    content = json.dumps({"messages": [], "note": "Canal privé.", "left_out": 1})

    html = str(conversation_html.thread(CONV, [(1, "user", "Q"), (2, "slack_context", content)])["blocks"][1]["html"])

    assert "Contexte du fil Slack · 0 message<" in html
    assert "<em>Canal privé. 1 message d&#39;invités ou de personnes extérieures non repris</em>" in html
