"""Une conversation en Work Object de Slack : ce que l'objet porte, et que rien n'y est lu comme une mention."""

from datetime import datetime, timezone

import pytest

from web import slack_entities
from web.stores.records import Conversation

URL = "https://autometa.example/c/0a1b2c3d"
CREATED = datetime(2026, 11, 20, 9, 5, tzinfo=timezone.utc)
UPDATED = datetime(2026, 11, 21, 15, 30, tzinfo=timezone.utc)
NOW = datetime(2026, 11, 22, 8, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def now(mocker):
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
    assert slack_entities.entity(URL, conversation()) == {
        "url": URL,
        "external_ref": {"id": "0a1b2c3d"},
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


def payload(conv):
    return slack_entities.entity(URL, conv)["entity_payload"]


def test_the_state_is_shown_only_while_a_turn_runs():
    assert payload(conversation(needs_response=True))["custom_fields"] == [
        {"key": "state", "label": "État", "value": "En cours", "type": "string", "tag_color": "blue"}
    ]


def test_a_conversation_without_owner_or_title_still_makes_an_object():
    shown = payload(conversation(user_id=None, title=None))

    assert "created_by" not in shown["fields"]
    assert shown["attributes"]["title"] == {"text": "Conversation sans titre"}


@pytest.mark.parametrize(
    "written,shown",
    [
        ("<!here> @channel", "<\u200b!here> @\u200bchannel"),
        ("Voir https://evil.example/x", "Voir https:\u200b//evil.example/x"),
        ("a\u202eb", "ab"),
        ("mot " * 60, ("mot " * 37).strip() + " …"),
    ],
    ids=["mention", "address", "writing direction", "long"],
)
def test_a_title_is_bounded_and_can_neither_mention_nor_link(written, shown):
    assert payload(conversation(title=written))["attributes"]["title"]["text"] == shown


def test_every_address_of_a_conversation_is_the_same_object():
    legacy = slack_entities.entity("https://autometa.example/explorations/0a1b2c3d", conversation())

    assert legacy["external_ref"] == slack_entities.entity(URL, conversation())["external_ref"]
