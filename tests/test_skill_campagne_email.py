import json
import re
from argparse import Namespace
from pathlib import Path

import pytest

from skills.campagne_email.scripts import deposit

ROOT = Path(__file__).parent.parent
PUBLIC_TEXTS = [
    ROOT / "skills" / "campagne_email" / "SKILL.md",
    ROOT / "knowledge" / "growth" / "ecrire-aux-professionnels.md",
]
SCHEMA = {
    "Campagne": {"type": "title"},
    "Statut": {"type": "status", "status": {"options": [{"name": "À valider"}, {"name": "Validée"}]}},
    "Outil": {"type": "select", "select": {"options": [{"name": "La Growth Machine"}, {"name": "Brevo"}]}},
    "Genre": {"type": "select", "select": {"options": [{"name": "Relation"}, {"name": "Activation"}]}},
    "Cible": {"type": "rich_text"},
    "Départements": {"type": "rich_text"},
    "Structures": {"type": "number"},
    "Contacts": {"type": "number"},
    "Expéditeur": {"type": "rich_text"},
    "Carte PDI": {"type": "url"},
    "Envoi souhaité": {"type": "date"},
    "Demandée par": {"type": "people"},
    "Conversation Autometa": {"type": "url"},
}
PAGE_ID = "0123456789abcdef0123456789abcdef"
PAGE_URL = f"https://www.notion.so/Campagne-{PAGE_ID}"


@pytest.mark.parametrize("path", PUBLIC_TEXTS, ids=lambda p: p.name)
def test_public_texts_carry_no_personal_data(path):
    text = path.read_text(encoding="utf-8")
    assert set(re.findall(r"Bonjour ([A-ZÉ][a-zé]+)", text)) <= {"Madame", "Prénom"}
    assert set(re.findall(r"^\[?([A-ZÉ][a-zé]+)\]? de La plateforme", text, re.M)) <= {"Prénom"}
    assert re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", text) == []
    assert re.findall(r"(?:\+33\s?|\b0)[1-9](?:[\s.-]?\d{2}){4}\b", text) == []


def write_draft(tmp_path, **fields):
    values = {
        "campagne": "Délégataires RSA, orientation",
        "outil": "lgm",
        "genre": "relation",
        "cible": "Délégataires du RSA, départements transmis",
        "departements": ["13", "59"],
        "structures": 120,
        "contacts": 310,
        "expediteur": "Prénom, bizdev",
        "carte_pdi": "https://www.notion.so/carte",
        "envoi_souhaite": "2026-12-01",
        "corps": "# Délégataires RSA\n\nBonjour,",
    } | fields
    path = tmp_path / "campagne.json"
    path.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def notion_calls(mocker):
    calls = []

    def answer(method, endpoint, payload=None):
        calls.append((method, endpoint, payload))
        if method == "GET":
            return {"properties": SCHEMA}
        return {"id": PAGE_ID, "url": PAGE_URL}

    mocker.patch.object(deposit.config, "NOTION_CAMPAIGNS_DB", "base-campagnes")
    mocker.patch.object(deposit.config, "BASE_URL", "https://autometa.exemple")
    mocker.patch.object(deposit.config, "agent_conversation_id", return_value="conv-1")
    mocker.patch.object(deposit.config, "agent_user_email", return_value="bizdev@exemple.fr")
    mocker.patch.object(deposit.backlog, "notion_user", return_value=("u1", "Bizdev"))
    mocker.patch.object(deposit.notion, "notion_request", side_effect=answer)
    mocker.patch.object(deposit.notion, "append_markdown")
    mocker.patch.object(deposit.notion, "replace_content")
    return calls


def test_dod_4_refuses_without_the_campaigns_base(mocker, tmp_path):
    mocker.patch.object(deposit.config, "NOTION_CAMPAIGNS_DB", None)
    request = mocker.patch.object(deposit.notion, "notion_request")
    with pytest.raises(ValueError, match="NOTION_CAMPAIGNS_DB absent"):
        deposit.run(Namespace(draft=str(write_draft(tmp_path)), go=True))
    request.assert_not_called()


def test_dod_4_without_go_writes_nothing(notion_calls, tmp_path):
    output = deposit.run(Namespace(draft=str(write_draft(tmp_path)), go=False))
    assert output.startswith("Vérification seulement")
    assert [method for method, _, _ in notion_calls] == ["GET"]
    deposit.notion.append_markdown.assert_not_called()


def test_dod_4_creates_the_page_with_the_base_values(notion_calls, tmp_path):
    path = write_draft(tmp_path)
    assert deposit.run(Namespace(draft=str(path), go=True)) == f"Page créée : {PAGE_URL}"
    method, endpoint, payload = notion_calls[-1]
    assert (method, endpoint, payload["parent"]) == ("POST", "pages", {"database_id": "base-campagnes"})
    assert payload["properties"] == {
        "Campagne": {"title": [{"text": {"content": "Délégataires RSA, orientation"}}]},
        "Cible": {"rich_text": [{"text": {"content": "Délégataires du RSA, départements transmis"}}]},
        "Départements": {"rich_text": [{"text": {"content": "13, 59"}}]},
        "Structures": {"number": 120},
        "Contacts": {"number": 310},
        "Expéditeur": {"rich_text": [{"text": {"content": "Prénom, bizdev"}}]},
        "Carte PDI": {"url": "https://www.notion.so/carte"},
        "Envoi souhaité": {"date": {"start": "2026-12-01"}},
        "Statut": {"status": {"name": "À valider"}},
        "Outil": {"select": {"name": "La Growth Machine"}},
        "Genre": {"select": {"name": "Relation"}},
        "Conversation Autometa": {"url": "https://autometa.exemple/explorations/conv-1"},
        "Demandée par": {"people": [{"id": "u1"}]},
    }
    deposit.notion.append_markdown.assert_called_once_with(PAGE_ID, "# Délégataires RSA\n\nBonjour,")
    assert json.loads(path.read_text(encoding="utf-8"))["page"] == PAGE_URL


def test_dod_4_a_correction_updates_the_same_page(notion_calls, tmp_path):
    path = write_draft(tmp_path, outil="brevo", genre="activation")
    deposit.run(Namespace(draft=str(path), go=True))
    draft = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(draft | {"corps": "Bonjour, corrigé"}, ensure_ascii=False), encoding="utf-8")
    assert deposit.run(Namespace(draft=str(path), go=True)) == f"Page mise à jour : {PAGE_URL}"
    page = "01234567-89ab-cdef-0123-456789abcdef"
    assert [(m, e) for m, e, _ in notion_calls if m != "GET"] == [("POST", "pages"), ("PATCH", f"pages/{page}")]
    properties = notion_calls[-1][2]["properties"]
    assert properties["Outil"] == {"select": {"name": "Brevo"}}
    assert properties["Genre"] == {"select": {"name": "Activation"}}
    deposit.notion.replace_content.assert_called_once_with(page, "Bonjour, corrigé")


@pytest.mark.parametrize(
    ("fields", "message"),
    [({"outil": "LGM"}, "Outil inconnu"), ({"genre": "Relance"}, "Genre inconnu"), ({"cible": ""}, "cible")],
)
def test_dod_4_refuses_a_value_outside_the_base(notion_calls, tmp_path, fields, message):
    with pytest.raises(ValueError, match=message):
        deposit.run(Namespace(draft=str(write_draft(tmp_path, **fields)), go=True))
    assert notion_calls == []


def test_dod_4_refuses_a_status_the_base_does_not_offer(notion_calls, mocker, tmp_path):
    mocker.patch.object(deposit, "STATUT", "En attente")
    with pytest.raises(ValueError, match="n'est pas une option de « Statut »"):
        deposit.run(Namespace(draft=str(write_draft(tmp_path)), go=True))
    assert [method for method, _, _ in notion_calls] == ["GET"]


def test_unknown_requester_and_address_leave_their_properties_empty(notion_calls, mocker, tmp_path):
    mocker.patch.object(deposit.config, "BASE_URL", "")
    deposit.backlog.notion_user.return_value = None
    output = deposit.run(Namespace(draft=str(write_draft(tmp_path)), go=True))
    properties = notion_calls[-1][2]["properties"]
    assert "Conversation Autometa" not in properties
    assert "Demandée par" not in properties
    assert "Conversation Autometa : adresse de l'application inconnue" in output
    assert "pas de compte Notion" in output
