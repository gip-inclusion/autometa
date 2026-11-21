"""Aperçu d'une fiche de connaissance en cours d'édition : l'agent en écrit le texte, la page n'en garde rien d'actif."""

import pytest

from web.database import store

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


def test_a_staged_file_preview_keeps_none_of_its_active_html(client, mocker, tmp_path):
    conversation = store.create_conversation(user_id="test@example.com", conv_type="knowledge")
    (tmp_path / "fiche.md").write_text("# Fiche\n\n**gras** <img src=x onerror=alert(1)>\n")
    mocker.patch("web.routes.knowledge.get_staging_dir", return_value=tmp_path)

    body = client.get(f"/api/knowledge/conversations/{conversation.id}/preview/fiche.md").text
    assert "<strong>gras</strong>" in body
    assert "onerror=alert(1)" not in body
