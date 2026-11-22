"""Une conversation en Work Object de Slack : ce que l'objet porte, et que rien n'y est lu comme une mention."""

import re
from datetime import datetime, timezone

import pytest

from web import slack_entities
from web.stores.records import Conversation, Tag

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
                "metadata_last_modified": int(UPDATED.timestamp()),
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


def thread(mocker, *messages, running=False, tags=()):
    mocker.patch.object(slack_entities.store, "get_conversation_tags", return_value=list(tags))
    mocker.patch.object(slack_entities.conversation_html.store, "get_displayed_messages", return_value=list(messages))
    return {field["key"]: field for field in slack_entities.details(conversation(needs_response=running))}


ANSWER = (
    "---\ntitle: x\n---\n# Bilan\n\nLes **candidatures** [montent](https://lien.example/a).\n\n## Par région\n\nVoir.\n"
)


def test_the_details_give_the_first_question_the_last_answer_and_its_sections(mocker):
    shown = thread(
        mocker,
        (1, "user", "Combien de\ncandidatures ?"),
        (2, "assistant", "Une première réponse."),
        (3, "user", "Et par région ?"),
        (4, "tool_use", ""),
        (5, "assistant", ANSWER),
    )

    assert shown == {
        "question": {
            "key": "question",
            "label": "Première question",
            "value": "Combien de candidatures ?",
            "type": "string",
            "long": True,
        },
        "answer": {
            "key": "answer",
            "label": "Dernière réponse",
            "value": "Bilan\nLes candidatures montent.\nPar région\nVoir.",
            "type": "string",
            "long": True,
        },
        "sections": {
            "key": "sections",
            "label": "Sections de la réponse",
            "value": "• Bilan\n• Par région",
            "type": "string",
            "long": True,
        },
    }


def test_the_details_leave_out_the_turn_still_running(mocker):
    messages = [(1, "user", "Un ?"), (2, "assistant", "Fini."), (3, "user", "Deux ?"), (4, "assistant", "En cours")]

    assert thread(mocker, *messages, running=True)["answer"]["value"] == "Fini."


@pytest.mark.parametrize(
    "messages,keys",
    [
        ([], []),
        ([(1, "user", "Une question ?")], ["question"]),
        ([(1, "user", "Une question ?"), (2, "assistant", "Sans titre.")], ["question", "answer"]),
    ],
    ids=["empty", "question alone", "answer without section"],
)
def test_the_details_only_hold_what_the_conversation_has(mocker, messages, keys):
    assert list(thread(mocker, *messages)) == keys


def test_the_details_are_bounded(mocker):
    titles = "".join(f"## Titre {rank} {'long ' * 40}\n\ntexte\n\n" for rank in range(15))

    shown = thread(mocker, (1, "user", "mot " * 200), (2, "assistant", titles))

    assert len(shown["question"]["value"]) <= 302
    assert len(shown["answer"]["value"]) <= 502
    assert len(shown["sections"]["value"].split("\n")) == 10
    assert all(len(line) <= 104 for line in shown["sections"]["value"].split("\n"))


def test_nothing_in_the_details_can_mention_link_or_change_writing_direction(mocker):
    hostile = "<!channel> @here <https://evil.example|ici> http://evil.example \u202egauche"

    shown = thread(mocker, (1, "user", hostile), (2, "assistant", f"## {hostile}\n\n{hostile}\n"))

    for field in shown.values():
        assert not re.search("<[!@h]|@[a-z]|://|[\u202a-\u202e]", field["value"]), field
        assert "format" not in field


def test_the_details_join_the_state_in_the_object(mocker):
    more = [{"key": "question", "label": "Première question", "value": "Une ?", "type": "string", "long": True}]

    fields = slack_entities.entity(URL, conversation(needs_response=True), more)["entity_payload"]["custom_fields"]

    assert [field["key"] for field in fields] == ["state", "question"]


def test_the_details_list_the_tags_by_facet_as_the_search_page_does(mocker):
    assigned = [
        Tag(name="insertion", type="theme", label="Insertion"),
        Tag(name="siae", type="audience", label="SIAE"),
        Tag(name="candidatures", type="feature", label="Candidatures"),
        Tag(name="diagnostic", type="feature", label="Diagnostic"),
        Tag(name="perdu", type="facette-inconnue", label="Perdu"),
    ]

    assert list(thread(mocker, tags=assigned).values()) == [
        {
            "key": "tags_feature",
            "label": "Bloc fonctionnel",
            "type": "array",
            "item_type": "string",
            "value": [{"value": "Candidatures"}, {"value": "Diagnostic"}],
        },
        {
            "key": "tags_audience",
            "label": "Réseau",
            "type": "array",
            "item_type": "string",
            "value": [{"value": "SIAE"}],
        },
        {
            "key": "tags_theme",
            "label": "Thème",
            "type": "array",
            "item_type": "string",
            "value": [{"value": "Insertion"}],
        },
    ]


def test_a_tag_label_can_neither_mention_nor_link(mocker):
    shown = thread(mocker, tags=[Tag(name="x", type="theme", label="<!channel> http://evil.example")])

    assert shown["tags_theme"]["value"] == [{"value": "<\u200b!channel> http:\u200b//evil.example"}]


def test_section_titles_are_shown_without_their_markdown(mocker):
    answer = "## Les **candidatures** [par région](https://lien.example/a) `SIAE`\n\ntexte\n\n## 1. _Bilan_\n\nfin\n"

    shown = thread(mocker, (1, "user", "Une ?"), (2, "assistant", answer))

    assert shown["sections"]["value"] == "• Les candidatures par région SIAE\n• 1. Bilan"


@pytest.mark.parametrize("mark", ["\u061c", "\u200e", "\u200f", "\u202e", "\u2067"])
def test_no_writing_direction_mark_reaches_slack(mark):
    shown = payload(conversation(title=f"a{mark}b", user_id=f"c{mark}d<!here>@example.org"))

    assert shown["attributes"]["title"]["text"] == "ab"
    assert shown["fields"]["created_by"]["user"]["text"] == "cd<\u200b!here>"


def test_the_object_is_dated_by_its_last_activity_and_by_now_only_while_a_turn_runs():
    assert payload(conversation())["attributes"]["metadata_last_modified"] == int(UPDATED.timestamp())
    running = payload(conversation(needs_response=True))["attributes"]

    assert running["metadata_last_modified"] == int(NOW.timestamp())
