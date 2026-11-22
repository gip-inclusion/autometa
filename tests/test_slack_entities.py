"""Une conversation en Work Object de Slack : ce que l'objet porte, et que rien n'y est lu comme une mention."""

from datetime import datetime, timezone

import pytest

from web import slack_charts, slack_entities
from web.stores.records import Conversation

URL = "https://autometa.example/c/0a1b2c3d/2/table-1-9f3a0c"
TEXT = {"type": "section", "text": {"type": "plain_text", "text": "Titre\nLe début du texte.", "emoji": False}}
CHART = {"type": "chart", "source": "pie title Parts", "title": "Parts"}
TABLE = {
    "type": "table_excerpt",
    "native": [
        {
            "type": "table",
            "rows": [
                [{"type": "raw_text", "text": "Mois"}, {"type": "raw_text", "text": "Orientations"}],
                [{"type": "raw_text", "text": "2026-04"}, {"type": "raw_text", "text": "8 412"}],
            ],
        },
        {"type": "context", "elements": [{"type": "plain_text", "text": "… 4 lignes de plus"}]},
    ],
    "ascii": [],
}
CREATED = datetime(2026, 11, 20, 9, 5, tzinfo=timezone.utc)
UPDATED = datetime(2026, 11, 21, 15, 30, tzinfo=timezone.utc)
NOW = datetime(2026, 11, 22, 8, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def now(mocker, monkeypatch):
    monkeypatch.setattr(slack_charts, "files", {})
    mocker.patch.object(slack_entities, "utcnow", return_value=NOW)


def conversation(**fields):
    defaults = {
        "id": "0a1b2c3d",
        "user_id": "camille.martin@example.org",
        "title": "Candidatures par région",
        "created_at": CREATED,
        "updated_at": UPDATED,
    }
    return Conversation(**(defaults | fields))


def test_a_conversation_is_a_content_item_with_its_title_author_and_dates():
    assert slack_entities.entity(URL, conversation(), []) == {
        "app_unfurl_url": URL,
        "url": URL,
        "external_ref": {"id": "/c/0a1b2c3d/2/table-1-9f3a0c"},
        "entity_type": "slack#/entities/content_item",
        "entity_payload": {
            "attributes": {
                "title": {"text": "Candidatures par région"},
                "display_type": "Conversation",
                "product_name": "Autometa",
                "metadata_last_modified": int(NOW.timestamp()),
            },
            "fields": {
                "created_by": {
                    "type": "slack#/types/user",
                    "user": {"text": "camille.martin", "email": "camille.martin@example.org"},
                },
                "date_created": {"value": int(CREATED.timestamp())},
                "date_updated": {"value": int(UPDATED.timestamp())},
            },
            "custom_fields": [],
        },
    }


def payload(conv=None, excerpt=()):
    return slack_entities.entity(URL, conv or conversation(), list(excerpt))["entity_payload"]


def test_the_state_is_shown_only_while_a_turn_runs():
    assert payload(conversation(needs_response=True))["custom_fields"] == [
        {"key": "etat", "label": "État", "value": "En cours", "type": "string", "tag_color": "blue"}
    ]


def test_a_conversation_without_owner_or_title_still_makes_an_object():
    shown = payload(conversation(user_id=None, title=None))

    assert "created_by" not in shown["fields"]
    assert shown["attributes"]["title"] == {"text": "Conversation sans titre"}


@pytest.mark.parametrize(
    "excerpt,description",
    [
        ([TEXT], "Titre\nLe début du texte."),
        ([TEXT, TABLE], "Titre\nLe début du texte.\nMois | Orientations\n2026-04 | 8 412\n… 4 lignes de plus"),
        ([CHART], "Graphique : Parts"),
        ([CHART | {"title": ""}], "Graphique"),
    ],
    ids=["text", "text and table", "chart", "untitled chart"],
)
def test_the_excerpt_is_carried_as_the_description(excerpt, description):
    assert payload(excerpt=excerpt)["fields"]["description"] == {"value": description}


def test_an_address_without_excerpt_has_no_description():
    assert "description" not in payload()["fields"]


def test_a_chart_already_in_slack_is_the_preview_of_the_object(monkeypatch):
    assert "preview" not in payload(excerpt=[CHART])["fields"]

    monkeypatch.setitem(slack_charts.files, slack_charts.key("pie title Parts"), "F0TEST")

    assert payload(excerpt=[CHART])["fields"]["preview"] == {
        "type": "slack#/types/image",
        "slack_file": {"id": "F0TEST"},
        "alt_text": "Parts",
    }


def test_neither_title_nor_description_can_mention():
    hostile = {"type": "section", "text": {"type": "plain_text", "text": "<!channel> @here"}}

    shown = payload(conversation(title="<!here> @channel"), [hostile])

    assert shown["attributes"]["title"]["text"] == "<\u200b!here> @\u200bchannel"
    assert shown["fields"]["description"]["value"] == "<\u200b!channel> @\u200bhere"


def test_two_permalinks_of_a_conversation_are_two_objects():
    other = slack_entities.entity("https://autometa.example/c/0a1b2c3d/2", conversation(), [])

    assert other["external_ref"] != slack_entities.entity(URL, conversation(), [])["external_ref"]
