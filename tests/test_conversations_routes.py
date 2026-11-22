import uuid
from urllib.parse import parse_qs, urlsplit

import pytest
from starlette.requests import Request

from web.database import store
from web.routes import html

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


@pytest.mark.parametrize(
    "tail",
    ["", "/12", "/12/table-1-abcdef", f"/{2**31 - 1}"],
    ids=["conversation", "réponse", "élément", "plus-grand-numéro-de-message"],
)
def test_the_conversation_page_answers_at_its_address_and_at_its_permalinks(client, tail):
    conv = store.create_conversation(user_id="alice@example.com")

    page = client.get(f"/c/{conv.id}{tail}", headers=headers(), follow_redirects=False)

    assert page.status_code == 200
    assert f"installConversation('{conv.id}')" in page.text


@pytest.mark.parametrize("running", [False, True], ids=["terminée", "tour-en-cours"])
def test_the_conversation_page_is_served_with_its_finished_turns_drawn(client, running):
    conv = store.create_conversation(user_id="alice@example.com")
    store.add_message(conv.id, "user", "Première question")
    answer = store.add_message(conv.id, "assistant", "## Titre\n\n<script>alert(1)</script>Réponse")
    if running:
        store.start_turn(conv.id, "Question en cours")
        store.add_message(conv.id, "assistant", "Réponse en cours")

    page = client.get(f"/c/{conv.id}", headers=headers()).text

    output = page[page.index('id="chatOutput"') : page.index('id="chatQueue"')]
    assert output.startswith(f'id="chatOutput" hx-disable data-last-id="{answer.id}">')
    assert output.count('class="event-block') == 2
    assert f'class="event-block event-assistant event-final-answer" data-msg-id="{answer.id}"' in output
    assert f'<h2 data-anchor="{answer.id}-section-1"' in output
    assert "<script" not in output and "en cours" not in output
    assert "loadingConversation" not in page


@pytest.mark.parametrize("tail", ["", "/12"], ids=["conversation", "réponse"])
@pytest.mark.parametrize(
    "conv_id",
    [str(uuid.uuid4()), "inconnue", "abc%00", f"{SHORT}%00", f"{UUID}%00"],
    ids=["uuid-inconnu", "pas-un-identifiant", "octet-nul", "court-et-octet-nul", "uuid-et-octet-nul"],
)
def test_an_address_naming_no_conversation_leads_to_the_list(client, conv_id, tail):
    page = client.get(f"/c/{conv_id}{tail}", headers=headers(), follow_redirects=False)

    assert (page.status_code, page.headers["location"]) == (302, "/conversations?show=convos")


@pytest.mark.parametrize("prefix", ["/c", "/explorations"], ids=["adresse", "ancienne-adresse"])
@pytest.mark.parametrize(
    "tail",
    ["/files", "/12/table-1-abcdef/x", f"/{10**10}", f"/{'9' * 5000}", f"/{'9' * 5000}/table-1-abcdef"],
    ids=[
        "segment-non-numérique",
        "segment-de-trop",
        "numéro-hors-borne",
        "numéro-démesuré",
        "élément-de-numéro-démesuré",
    ],
)
def test_other_addresses_under_a_conversation_match_nothing(client, prefix, tail):
    conv = store.create_conversation(user_id="alice@example.com")

    assert client.get(f"{prefix}/{conv.id}{tail}", headers=headers(), follow_redirects=False).status_code == 404


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
        (f"/{2**31 - 1}", f"/{2**31 - 1}"),
    ],
    ids=[
        "conversation",
        "message-à-envoyer",
        "réponse",
        "élément",
        "paramètres",
        "requête-glissée",
        "fragment-glissé",
        "plus-grand-numéro-de-message",
    ],
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
    ("query", "kept"),
    [
        (b"prefill=Cr\xc3\xa9e", "prefill=Cr%C3%A9e"),
        (b"message=Caf\xc3\xa9%20%26%20th\xc3\xa9&x=1", "message=Caf%C3%A9%20%26%20th%C3%A9&x=1"),
        (b"prefill=Cr%C3%A9e%20un%20tableau", "prefill=Cr%C3%A9e%20un%20tableau"),
    ],
    ids=["octets-utf8", "octets-et-encodage-mêlés", "déjà-encodée"],
)
def test_an_old_address_keeps_the_meaning_of_a_query_sent_as_raw_bytes(query, kept):
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/explorations/new",
        "query_string": query,
        "headers": [],
    })

    location = html.explorations_redirect("new", request, "alice@example.com").headers["location"]

    assert location == f"/c/new?{kept}"
    assert parse_qs(urlsplit(location).query) == parse_qs(query.decode())


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
