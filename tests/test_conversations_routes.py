import uuid

import pytest

from web.database import store

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


def make_running_conversation(user_id):
    conv = store.create_conversation(user_id=user_id)
    store.update_conversation(conv.id, needs_response=True)
    return conv


def headers(email="alice@example.com"):
    return {"X-Forwarded-Email": email}


def test_running_returns_only_own_conversations(client):
    own = make_running_conversation("alice@example.com")
    other = make_running_conversation("bob@example.com")

    running = client.get("/api/conversations/running", headers=headers()).json()["running"]

    assert own.id in running
    assert other.id not in running


def test_running_excludes_idle_conversations(client):
    idle = store.create_conversation(user_id="alice@example.com")

    running = client.get("/api/conversations/running", headers=headers()).json()["running"]

    assert idle.id not in running


def test_running_includes_legacy_conversations_without_owner(client):
    legacy = make_running_conversation(None)

    running = client.get("/api/conversations/running", headers=headers()).json()["running"]

    assert legacy.id in running


@pytest.mark.parametrize("tail", ["", "/12", "/12/table-1-abcdef"], ids=["conversation", "réponse", "élément"])
def test_the_conversation_page_answers_at_its_address_and_at_its_permalinks(client, tail):
    conv = store.create_conversation(user_id="alice@example.com")

    page = client.get(f"/explorations/{conv.id}{tail}", headers=headers(), follow_redirects=False)

    assert page.status_code == 200
    assert f"loadConversation('{conv.id}')" in page.text


@pytest.mark.parametrize("conv_id", [str(uuid.uuid4()), "inconnue"], ids=["uuid-inconnu", "pas-un-uuid"])
def test_an_address_naming_no_conversation_leads_to_the_list(client, conv_id):
    page = client.get(f"/explorations/{conv_id}/12", headers=headers(), follow_redirects=False)

    assert (page.status_code, page.headers["location"]) == (302, "/conversations?show=convos")


@pytest.mark.parametrize("tail", ["/files", "/12/table-1-abcdef/x"], ids=["segment-non-numérique", "segment-de-trop"])
def test_other_addresses_under_a_conversation_match_nothing(client, tail):
    conv = store.create_conversation(user_id="alice@example.com")

    assert client.get(f"/explorations/{conv.id}{tail}", headers=headers()).status_code == 404


@pytest.mark.parametrize(
    ("tail", "kept"),
    [
        ("", ""),
        ("/table-1-abcdef", "/table-1-abcdef"),
        ("/x%3Fmessage%3Dhello", ""),
        ("/x%23frag", ""),
        ("/bonjour", ""),
        ("/table-1234567-abcdef", ""),
    ],
    ids=["réponse", "élément", "requête-glissée", "fragment-glissé", "mot-quelconque", "rang-démesuré"],
)
def test_a_short_permalink_leads_to_its_message_at_the_address_of_its_conversation(client, tail, kept):
    conv = store.create_conversation(user_id="alice@example.com")
    message = store.add_message(conv.id, "assistant", "Réponse").id

    page = client.get(f"/m/{message}{tail}", headers=headers("bob@example.com"), follow_redirects=False)

    assert page.status_code == 302
    assert page.headers["location"] == f"/explorations/{conv.id}/{message}{kept}"


@pytest.mark.parametrize("message", ["999999999", "9" * 30], ids=["inconnu", "démesuré"])
def test_a_short_permalink_to_no_message_leads_to_the_list(client, message):
    page = client.get(f"/m/{message}/table-1-abcdef", headers=headers(), follow_redirects=False)

    assert (page.status_code, page.headers["location"]) == (302, "/conversations?show=convos")
