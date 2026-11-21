import uuid

import pytest

from web.database import store

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

SHORT = "k3v9x2mq"
UUID = "21e937fb-0000-4000-8000-000000000001"


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

    page = client.get(f"/c/{conv.id}{tail}", headers=headers(), follow_redirects=False)

    assert page.status_code == 200
    assert f"loadConversation('{conv.id}')" in page.text


@pytest.mark.parametrize("conv_id", [str(uuid.uuid4()), "inconnue"], ids=["uuid-inconnu", "pas-un-uuid"])
def test_an_address_naming_no_conversation_leads_to_the_list(client, conv_id):
    page = client.get(f"/c/{conv_id}/12", headers=headers(), follow_redirects=False)

    assert (page.status_code, page.headers["location"]) == (302, "/conversations?show=convos")


@pytest.mark.parametrize("tail", ["/files", "/12/table-1-abcdef/x"], ids=["segment-non-numérique", "segment-de-trop"])
def test_other_addresses_under_a_conversation_match_nothing(client, tail):
    conv = store.create_conversation(user_id="alice@example.com")

    assert client.get(f"/c/{conv.id}{tail}", headers=headers()).status_code == 404


@pytest.mark.parametrize("conv_id", [SHORT, UUID], ids=["court", "uuid"])
@pytest.mark.parametrize(
    ("tail", "kept"),
    [
        ("", ""),
        ("?message=Bonjour%20%26%20merci", "?message=Bonjour%20%26%20merci"),
        ("/12", "/12"),
        ("/12/table-1-abcdef", "/12/table-1-abcdef"),
        ("/12/table-1-abcdef?utm_source=slack&x=%2F%2Fa", "/12/table-1-abcdef?utm_source=slack&x=%2F%2Fa"),
        ("/12/x%3Fmessage%3Dhello", "/12"),
        ("/12/x%23frag", "/12"),
    ],
    ids=["conversation", "message-à-envoyer", "réponse", "élément", "paramètres", "requête-glissée", "fragment-glissé"],
)
def test_an_old_conversation_address_leads_to_its_new_one(client, conv_id, tail, kept):
    page = client.get(f"/explorations/{conv_id}{tail}", headers=headers(), follow_redirects=False)

    assert (page.status_code, page.headers["location"]) == (302, f"/c/{conv_id}{kept}")


@pytest.mark.parametrize(
    "query", ["", "?prefill=Cr%C3%A9e%20un%20tableau%20de%20bord%20qui%20"], ids=["vide", "préremplie"]
)
def test_the_old_new_conversation_address_leads_to_the_new_one(client, query):
    page = client.get(f"/explorations/new{query}", headers=headers(), follow_redirects=False)

    assert (page.status_code, page.headers["location"]) == (302, f"/c/new{query}")


@pytest.mark.parametrize(
    "conv_id",
    ["k3v9x2m", "k3v9x2mqa", "K3V9X2MQ", "k3v9x2mi", "evil.com", "@evil.com", "%5C%5Cevil.com"],
    ids=["sept-caractères", "neuf-caractères", "majuscules", "hors-alphabet", "domaine", "arobase", "antislash"],
)
def test_an_old_address_naming_no_possible_conversation_leads_to_the_list(client, conv_id):
    page = client.get(f"/explorations/{conv_id}/12?message=x", headers=headers(), follow_redirects=False)

    assert (page.status_code, page.headers["location"]) == (302, "/conversations?show=convos")


@pytest.mark.parametrize("path", ["%2F%2Fevil.com", "..%2Fx", "/evil.com"], ids=["double-barre", "remontée", "vide"])
def test_an_old_address_with_a_slash_for_an_id_matches_nothing(client, path):
    assert client.get(f"/explorations/{path}", headers=headers(), follow_redirects=False).status_code == 404


@pytest.mark.parametrize(
    ("query", "status", "location"),
    [
        (f"?conv={SHORT}", 302, f"/c/{SHORT}"),
        (f"?conv={UUID}", 302, f"/c/{UUID}"),
        ("?conv=//evil.com", 301, "/conversations?show=convos"),
        ("", 301, "/conversations?show=convos"),
        ("?mine=1", 301, "/conversations?show=mine"),
    ],
    ids=["court", "uuid", "pas-un-identifiant", "liste", "mes-conversations"],
)
def test_the_old_explorations_list_leads_to_a_conversation_or_the_list(client, query, status, location):
    page = client.get(f"/explorations{query}", headers=headers(), follow_redirects=False)

    assert (page.status_code, page.headers["location"]) == (status, location)


def test_a_new_conversation_page_answers_at_its_address(client):
    page = client.get("/c/new", headers=headers(), follow_redirects=False)

    assert page.status_code == 200
    assert 'id="chatInput"' in page.text
