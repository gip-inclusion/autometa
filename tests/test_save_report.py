"""Le script du skill save_report : l'auteur et la conversation d'un rapport viennent de l'environnement de l'agent."""

import json

import pytest

from skills.save_report.scripts import save_report as cli
from web.database import store

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("app")]


def report_ids_shown_in(conversation_id):
    messages = store.get_conversation(conversation_id, include_messages=True).messages
    return [json.loads(m.content)["report_id"] for m in messages if m.type == "report"]


def test_new_report_belongs_to_the_agent_user_and_its_conversation(monkeypatch):
    conversation = store.create_conversation(user_id="alice@x")
    other = store.create_conversation(user_id="bob@x")
    monkeypatch.setenv("AUTOMETA_CONVERSATION_ID", conversation.id)
    monkeypatch.setenv("AUTOMETA_USER_EMAIL", "alice@x")

    result = cli.save_report(title="Trafic", content="# Trafic")

    report = store.get_report(result["report_id"])
    assert (report.user_id, report.source_conversation_id) == ("alice@x", conversation.id)
    assert report_ids_shown_in(conversation.id) == [report.id]
    assert report_ids_shown_in(other.id) == []


def test_a_report_saved_outside_an_agent_has_no_author_nor_conversation(monkeypatch):
    monkeypatch.delenv("AUTOMETA_CONVERSATION_ID", raising=False)
    monkeypatch.delenv("AUTOMETA_USER_EMAIL", raising=False)

    result = cli.save_report(title="Trafic", content="# Trafic")

    report = store.get_report(result["report_id"])
    assert (report.user_id, report.source_conversation_id) == (None, None)
