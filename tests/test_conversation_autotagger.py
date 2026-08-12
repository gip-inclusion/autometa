"""Tests du tagueur automatique de conversations — vocabulaire synchronisé, thread de fond."""

from datetime import datetime, timezone

import pytest

from web.database import store
from web.db import get_db
from web.db import test_transaction as _test_tx
from web.models import Conversation, Tag
from web.routes.conversations import generate_conversation_tags


@pytest.fixture
def db():
    with _test_tx():
        yield


@pytest.fixture
def run_inline(mocker):
    """Exécute la cible du thread en ligne : le tagueur tourne normalement en daemon."""

    def fake_thread(target, daemon=None):
        return mocker.MagicMock(start=target)

    mocker.patch("web.routes.conversations.threading.Thread", side_effect=fake_thread)


def _conversation(conv_id="conv-tag"):
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(Conversation(id=conv_id, user_id="a@b.c", created_at=now, updated_at=now))
        session.flush()
    return conv_id


def _vocab(*names, facet="usage"):
    with get_db() as session:
        for name in names:
            session.add(Tag(name=name, type=facet, label=name, active=True))
        session.flush()


def test_applies_tags_from_the_synced_vocabulary(db, mocker, run_inline):
    _vocab("territoire")
    conv_id = _conversation()
    mocker.patch("web.llm.generate_text", return_value="territoire")

    generate_conversation_tags("couverture Dora en Haute-Loire", conv_id)

    assert [t.name for t in store.get_conversation_tags(conv_id)] == ["territoire"]


def test_drops_terms_outside_the_vocabulary(db, mocker, run_inline):
    _vocab("territoire")
    conv_id = _conversation()
    mocker.patch("web.llm.generate_text", return_value="territoire, terme-invente")

    generate_conversation_tags("peu importe", conv_id)

    assert [t.name for t in store.get_conversation_tags(conv_id)] == ["territoire"]


def test_pending_terms_are_not_offered_to_the_model(db, mocker, run_inline):
    _vocab("territoire")
    with get_db() as session:
        session.add(Tag(name="propose", type="usage", label="Proposé", active=True, pending=True))
        session.flush()
    conv_id = _conversation()
    generate = mocker.patch("web.llm.generate_text", return_value="territoire")

    generate_conversation_tags("peu importe", conv_id)

    assert "propose" not in generate.call_args[0][0]


def test_does_nothing_when_the_vocabulary_is_empty(db, mocker, run_inline):
    conv_id = _conversation()
    generate = mocker.patch("web.llm.generate_text")

    generate_conversation_tags("peu importe", conv_id)

    generate.assert_not_called()
    assert store.get_conversation_tags(conv_id) == []


def test_llm_failure_leaves_the_conversation_untagged(db, mocker, run_inline):
    from web.llm_errors import LLMError

    _vocab("territoire")
    conv_id = _conversation()
    mocker.patch("web.llm.generate_text", side_effect=LLMError("boom"))

    generate_conversation_tags("peu importe", conv_id)

    assert store.get_conversation_tags(conv_id) == []
