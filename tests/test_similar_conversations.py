"""Test recommendations from the first user message before it is indexed."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from web import config
from web.routes import conversations
from web.stores.records import Conversation, Message


@pytest.fixture
def similar_client(mocker):
    mocker.patch.object(conversations, "is_embedding_model_ready", return_value=True)
    app = FastAPI()
    app.include_router(conversations.router)
    return TestClient(app)


def test_similar_uses_first_user_message_and_configured_threshold(similar_client, mocker):
    conv = Conversation(
        id="current",
        messages=[
            Message(type="assistant", content="Bonjour"),
            Message(type="user", content="Les visites du portail"),
            Message(type="user", content="Une précision"),
        ],
    )
    mocker.patch.object(conversations.store, "get_conversation", return_value=conv)
    embed = mocker.patch.object(conversations, "embed_query", return_value=[1.0, 0.0])
    search = mocker.patch.object(
        conversations.store, "search_conversation_ids_by_embedding", return_value=["closest", "other"]
    )
    mocker.patch.object(
        conversations.store,
        "get_conversations_by_ids",
        return_value={
            "other": Conversation(id="other", title="Parcours"),
            "closest": Conversation(id="closest", title="Fréquentation"),
        },
    )
    mocker.patch.object(config, "SIMILAR_CONVERSATIONS_MAX_DISTANCE", 0.4)

    response = similar_client.get("/api/conversations/current/similar")

    assert response.status_code == 200
    assert response.json() == {
        "conversations": [{"id": "closest", "title": "Fréquentation"}, {"id": "other", "title": "Parcours"}]
    }
    embed.assert_called_once_with("Les visites du portail")
    search.assert_called_once_with([1.0, 0.0], max_distance=0.4, limit=3)


def test_similar_skips_embedding_and_search_when_model_is_not_ready(similar_client, mocker):
    conv = Conversation(id="current", messages=[Message(type="user", content="Les visites du portail")])
    mocker.patch.object(conversations.store, "get_conversation", return_value=conv)
    mocker.patch.object(conversations, "is_embedding_model_ready", return_value=False)
    embed = mocker.patch.object(conversations, "embed_query")
    search = mocker.patch.object(conversations.store, "search_conversation_ids_by_embedding")

    response = similar_client.get("/api/conversations/current/similar")

    assert response.status_code == 200
    assert response.json() == {"conversations": []}
    embed.assert_not_called()
    search.assert_not_called()


@pytest.mark.parametrize(
    "messages", [[], [Message(type="assistant", content="Bonjour")], [Message(type="user", content=" ")]]
)
def test_similar_without_user_text_skips_embedding(similar_client, mocker, messages):
    mocker.patch.object(conversations.store, "get_conversation", return_value=Conversation(messages=messages))
    embed = mocker.patch.object(conversations, "embed_query")

    response = similar_client.get("/api/conversations/current/similar")

    assert response.status_code == 200
    assert response.json() == {"conversations": []}
    embed.assert_not_called()


def test_similar_missing_conversation(similar_client, mocker):
    mocker.patch.object(conversations.store, "get_conversation", return_value=None)

    response = similar_client.get("/api/conversations/missing/similar")

    assert response.status_code == 404
    assert response.json() == {"error": "Conversation not found"}
