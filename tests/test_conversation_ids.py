"""Identifiants de conversation : un UUID pour les anciennes, 8 caractères pour les nouvelles, rien d'autre."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from web.database import store
from web.db import get_db
from web.helpers import CONV_ID_ALPHABET, UUID_CONV_ID, new_conv_id, validate_conv_id
from web.models import Conversation
from web.stores.conversations import insert_conversation

STREAM_JS = Path(__file__).parent.parent / "web" / "static" / "js" / "stream.js"

HARNESS = """
const fs = require('fs');
const vm = require('vm');
const [path, id] = process.argv.slice(2);
const sandbox = { window: {}, document: { addEventListener: () => {} } };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path, 'utf8'), sandbox);
console.log(JSON.stringify(sandbox.isValidConversationId(id)));
"""

IDS = {
    "uuid": ("21e937fb-0000-4000-8000-000000000001", True),
    "court": ("k3v9x2mq", True),
    "court-en-chiffres": ("01234567", True),
    "uuid-en-majuscules": ("21E937FB-0000-4000-8000-000000000001", False),
    "uuid-sans-tirets": ("21e937fb000040008000000000000001", False),
    "uuid-entre-accolades": ("{21e937fb-0000-4000-8000-000000000001}", False),
    "sept-caractères": ("k3v9x2m", False),
    "neuf-caractères": ("k3v9x2mqa", False),
    "lettre-i": ("k3v9x2mi", False),
    "lettre-l": ("k3v9x2ml", False),
    "lettre-o": ("k3v9x2mo", False),
    "lettre-u": ("k3v9x2mu", False),
    "majuscules": ("K3V9X2MQ", False),
    "remontée": ("../x", False),
    "remontée-de-huit": ("../k3v9x", False),
    "saut-de-ligne-final": ("k3v9x2mq\n", False),
    "chiffres-non-ascii": ("١٢٣٤٥٦٧٨", False),
    "vide": ("", False),
}


@pytest.mark.parametrize(("conv_id", "valid"), IDS.values(), ids=IDS.keys())
def test_only_a_uuid_or_eight_characters_of_the_alphabet_are_a_conversation_id(conv_id, valid):
    assert validate_conv_id(conv_id) is valid


@pytest.mark.skipif(shutil.which("node") is None, reason="node requis pour exécuter stream.js")
@pytest.mark.parametrize(("conv_id", "valid"), IDS.values(), ids=IDS.keys())
def test_the_page_accepts_the_same_conversation_ids_as_the_server(tmp_path, conv_id, valid):
    harness = tmp_path / "harness.js"
    harness.write_text(HARNESS)

    result = subprocess.run(
        ["node", str(harness), str(STREAM_JS), conv_id], capture_output=True, text=True, check=True, timeout=10
    )

    assert json.loads(result.stdout) is valid


def test_a_drawn_id_is_eight_characters_of_the_alphabet():
    drawn = {new_conv_id() for _ in range(200)}

    assert all(len(conv_id) == 8 and set(conv_id) <= set(CONV_ID_ALPHABET) for conv_id in drawn)
    assert len(drawn) == 200


@pytest.mark.integration
def test_a_new_conversation_gets_a_short_id(app):
    conv = store.create_conversation(user_id="alice@example.com")

    assert validate_conv_id(conv.id)
    assert not UUID_CONV_ID.fullmatch(conv.id)
    assert store.get_conversation(conv.id).user_id == "alice@example.com"


@pytest.mark.integration
@pytest.mark.parametrize(
    "make_second",
    [
        lambda first: store.create_conversation(user_id="bob@example.com"),
        lambda first: store.fork_conversation(first.id, "bob@example.com"),
    ],
    ids=["création", "duplication"],
)
def test_an_id_already_taken_is_drawn_again(app, mocker, make_second):
    draws = mocker.patch("web.stores.conversations.new_conv_id", side_effect=["aaaaaaaa", "aaaaaaaa", "bbbbbbbb"])
    first = store.create_conversation(user_id="alice@example.com")
    store.add_message(first.id, "user", "Question")

    second = make_second(first)

    assert (first.id, second.id) == ("aaaaaaaa", "bbbbbbbb")
    assert draws.call_count == 3
    assert store.get_conversation("aaaaaaaa").user_id == "alice@example.com"
    assert store.get_conversation("bbbbbbbb").user_id == "bob@example.com"


@pytest.mark.integration
def test_a_draw_stuck_on_a_taken_id_gives_up_after_a_few_tries(app, mocker):
    draws = mocker.patch("web.stores.conversations.new_conv_id", side_effect=["aaaaaaaa"] * 20)
    store.create_conversation(user_id="alice@example.com")

    with pytest.raises(RuntimeError):
        store.create_conversation(user_id="bob@example.com")

    assert draws.call_count == 1 + 5


@pytest.mark.integration
def test_an_integrity_error_other_than_a_taken_id_is_raised_without_drawing_again(app, mocker):
    draws = mocker.patch("web.stores.conversations.new_conv_id", side_effect=["aaaaaaaa", "bbbbbbbb"])

    with pytest.raises(IntegrityError), get_db() as session:
        insert_conversation(session, Conversation(user_id="alice@example.com"))

    assert draws.call_count == 1
