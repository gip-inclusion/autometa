"""Parcours réel contre Ollama Cloud. Requiert OLLAMA_API_KEY. Aucune CI ne l'exécute."""

import asyncio
import uuid

import pytest

from web import config, session_sync
from web.agents import get_agent

pytestmark = pytest.mark.external


def _texts(msgs):
    return " ".join(str(m.content) for m in msgs if m.type == "assistant")


@pytest.mark.skipif(not config.OLLAMA_API_KEY, reason="OLLAMA_API_KEY absent")
def test_fallback_calls_tools_then_resumes(tmp_path, mocker):
    target = tmp_path / "secret.txt"
    target.write_text("Le mot secret est ANANAS-4712.\n")
    # Why: tmp_path est hors du dépôt — sans --add-dir le CLI refuserait le Read et l'échec
    # porterait sur les permissions, pas sur le comportement du modèle qu'on veut mesurer.
    mocker.patch.object(config, "ADDITIONAL_DIRS", [*config.ADDITIONAL_DIRS, str(tmp_path)])
    backend = get_agent("cli-ollama")
    conv_id, session_id = str(uuid.uuid4()), str(uuid.uuid4())

    async def _collect(prompt):
        return [m async for m in backend.send_message(conv_id, prompt, [], session_id=session_id)]

    first = asyncio.run(_collect(f"Lis {target} et dis-moi le mot secret."))
    assert any(m.type == "tool_use" for m in first)
    assert "ANANAS-4712" in _texts(first)

    assert session_sync.get_session_path(session_id).exists()

    second = asyncio.run(_collect("Répète le mot secret, sans relire le fichier."))
    assert "ANANAS-4712" in _texts(second)
