"""Identifiants de conversation : un UUID pour les anciennes, 8 caractères pour les nouvelles, rien d'autre."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from web.helpers import validate_conv_id

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
