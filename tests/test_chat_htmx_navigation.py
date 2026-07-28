# Régression : htmx émet htmx:afterSettle pour le swap principal ET pour chaque bloc
# out-of-band (les conversations récentes de la sidebar, desktop et mobile). Quand le handler
# de navigation s'exécutait sur les trois, initChat() empilait trois écouteurs sur le bouton
# d'envoi : un seul clic créait trois conversations.

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
CHAT_JS = REPO / "web" / "static" / "js" / "chat.js"

HARNESS = """
const fs = require('fs');
const vm = require('vm');

const [chatJsPath, ...swappedIds] = process.argv.slice(2);
const noop = () => {};
const navHandlers = [];

const sandbox = {
  console,
  document: {
    addEventListener: noop,
    getElementById: () => null,
    body: {
      addEventListener: (type, fn) => {
        if (type === 'htmx:afterSettle') navHandlers.push(fn);
      },
    },
  },
  window: {
    location: { pathname: '/explorations/new', search: '' },
    addEventListener: noop,
    scrollTo: noop,
    scrollY: 0,
  },
  history: { replaceState: noop, state: {} },
  localStorage: { getItem: () => null },
};
sandbox.window.window = sandbox.window;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(chatJsPath, 'utf8'), sandbox);

let initChatCalls = 0;
let authChecks = 0;
sandbox.initChat = () => { initChatCalls++; };
sandbox.checkAuthStatus = () => { authChecks++; };
sandbox.initKnowledge = noop;
sandbox.closeEventSource = noop;
sandbox.loadConversation = noop;

for (const id of swappedIds) {
  navHandlers.forEach(handler => handler({ target: { id }, detail: { target: { id: 'main' } } }));
}

console.log(JSON.stringify({ initChatCalls, authChecks }));
"""


def run_navigation(tmp_path, *swapped_ids):
    """Rejoue des htmx:afterSettle sur les handlers de chat.js et compte les initialisations."""
    harness = tmp_path / "harness.js"
    harness.write_text(HARNESS)
    result = subprocess.run(
        ["node", str(harness), str(CHAT_JS), *swapped_ids],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node requis pour exécuter chat.js")
@pytest.mark.parametrize(
    ("swapped_ids", "expected"),
    [
        (["main"], 1),
        (["main", "sidebar-recents", "mobile-recents"], 1),
        (["sidebar-recents", "mobile-recents"], 0),
    ],
    ids=["swap principal seul", "navigation complète avec blocs OOB", "blocs OOB seuls"],
)
def test_navigation_initialises_chat_once(tmp_path, swapped_ids, expected):
    counts = run_navigation(tmp_path, *swapped_ids)

    assert counts["initChatCalls"] == expected
    assert counts["authChecks"] == expected
