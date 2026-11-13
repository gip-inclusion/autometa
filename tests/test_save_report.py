"""Le script du skill save_report : l'auteur et la conversation d'un rapport viennent de l'environnement de l'agent."""

import json

import pytest

from skills.save_report.scripts import save_report as cli
from web.database import store

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("app")]


def test_new_report_belongs_to_the_agent_user_and_its_conversation(monkeypatch):
    conversation = store.create_conversation(user_id="alice@x")
    monkeypatch.setenv("AUTOMETA_CONVERSATION_ID", conversation.id)
    monkeypatch.setenv("AUTOMETA_USER_EMAIL", "alice@x")

    result = cli.save_report(title="Trafic", content="# Trafic")

    report = store.get_report(result["report_id"])
    assert (report.user_id, report.source_conversation_id) == ("alice@x", conversation.id)
    messages = store.get_conversation(conversation.id, include_messages=True).messages
    assert [json.loads(m.content)["report_id"] for m in messages if m.type == "report"] == [report.id]
