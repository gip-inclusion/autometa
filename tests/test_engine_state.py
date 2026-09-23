"""Tests de l'état par moteur porté par conversations.engine_state."""

import pytest

from web.database import store

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


def make_conversation():
    return store.create_conversation(user_id="u1").id


def test_engine_state_falls_back_to_session_id_for_primary(app, mocker):
    mocker.patch("web.stores.conversations.config.AGENT_BACKEND", "cli")
    conv_id = make_conversation()
    store.update_conversation(conv_id, session_id="sess-1")

    assert store.get_engine_state(conv_id, "cli") == {"session_id": "sess-1", "seen_through": None}
    assert store.get_engine_state(conv_id, "cli-ollama") == {"session_id": None, "seen_through": None}


def test_set_engine_state_merges_without_clobbering(app):
    conv_id = make_conversation()
    store.set_engine_state(conv_id, "cli-ollama", session_id="sess-2")
    store.set_engine_state(conv_id, "cli-ollama", seen_through=42)

    assert store.get_engine_state(conv_id, "cli-ollama") == {"session_id": "sess-2", "seen_through": 42}


def test_set_engine_state_preserves_falsy_seen_through(app):
    conv_id = make_conversation()
    store.set_engine_state(conv_id, "cli-ollama", session_id="sess-3", seen_through=0)

    assert store.get_engine_state(conv_id, "cli-ollama") == {"session_id": "sess-3", "seen_through": 0}


def test_engines_keep_independent_state(app):
    conv_id = make_conversation()
    store.set_engine_state(conv_id, "cli", session_id="a", seen_through=10)
    store.set_engine_state(conv_id, "cli-ollama", session_id="b", seen_through=7)

    assert store.get_engine_state(conv_id, "cli")["seen_through"] == 10
    assert store.get_engine_state(conv_id, "cli-ollama")["seen_through"] == 7


def test_get_engine_state_unknown_conversation_returns_default(app):
    assert store.get_engine_state("does-not-exist", "cli") == {"session_id": None, "seen_through": None}


def test_set_engine_state_unknown_conversation_returns_false(app):
    assert store.set_engine_state("does-not-exist", "cli", session_id="x") is False


def test_fork_remaps_seen_through_by_position(app, mocker):
    mocker.patch("web.stores.conversations.session_sync.copy_session", return_value=True)
    conv_id = make_conversation()
    store.add_message(conv_id, "user", "un")
    second = store.add_message(conv_id, "assistant", "deux")
    store.add_message(conv_id, "user", "trois")
    store.update_conversation(conv_id, session_id="sess-src")
    store.set_engine_state(conv_id, "cli", session_id="sess-src", seen_through=second.id)

    forked = store.fork_conversation(conv_id, "u2")

    remapped = store.get_engine_state(forked.id, "cli")["seen_through"]
    assert remapped == forked.messages[1].id
    assert remapped != second.id


def test_fork_copies_the_primary_session_once_and_keeps_both_pointers_aligned(app, mocker):
    """session_id porte la session du moteur primaire, qui est aussi dans engine_state : une seule
    copie (deux téléchargements S3 sinon) et deux pointeurs qui restent égaux."""
    copy = mocker.patch("web.stores.conversations.session_sync.copy_session", return_value=True)
    conv_id = make_conversation()
    store.update_conversation(conv_id, session_id="sess-src")
    store.set_engine_state(conv_id, "cli", session_id="sess-src")

    forked = store.fork_conversation(conv_id, "u2")

    assert copy.call_count == 1
    assert forked.session_id == store.get_engine_state(forked.id, "cli")["session_id"]
    assert forked.session_id != "sess-src"


@pytest.mark.parametrize("succeeding_backend", ["cli", "cli-ollama"])
def test_fork_keeps_only_the_engine_whose_session_copy_succeeds(app, mocker, succeeding_backend):
    sessions = {"cli": "sess-cli", "cli-ollama": "sess-cli-ollama"}
    mocker.patch(
        "web.stores.conversations.session_sync.copy_session",
        side_effect=lambda src, dst: src == sessions[succeeding_backend],
    )
    conv_id = make_conversation()
    store.set_engine_state(conv_id, "cli", session_id=sessions["cli"])
    store.set_engine_state(conv_id, "cli-ollama", session_id=sessions["cli-ollama"])

    forked = store.fork_conversation(conv_id, "u2")

    failing_backend = "cli-ollama" if succeeding_backend == "cli" else "cli"
    assert store.get_engine_state(forked.id, succeeding_backend)["session_id"] is not None
    assert store.get_engine_state(forked.id, failing_backend)["session_id"] is None
