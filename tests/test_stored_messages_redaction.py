"""Les secrets sont masqués avant d'atteindre la table messages."""

import pytest

from web.database import store

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

HEX = "0123456789abcdef0123456789abcdef"  # gitleaks:allow
DSN = "postgresql://lecteur:motdepasse-factice-42@base.example:5432/prod"  # gitleaks:allow


def make_conversation():
    return store.create_conversation(user_id="u1").id


def stored_contents(conv_id):
    return [m.content for m in store.get_messages(conv_id)]


@pytest.mark.parametrize(
    ("type", "content", "secret"),
    [
        ("tool_result", f'{{"output": "connexion à {DSN}"}}', "motdepasse-factice-42"),
        ("tool_use", f'{{"command": "curl \\"https://matomo/?module=API&token_auth={HEX}\\""}}', HEX),
        ("assistant", f"La variable vaut MATOMO_TOKEN={HEX}", HEX),
    ],
)
def test_a_new_message_is_stored_without_its_secret(type, content, secret):
    conv_id = make_conversation()

    store.add_message(conv_id, type, content)

    assert [secret in stored for stored in stored_contents(conv_id)] == [False]


def test_an_updated_message_is_stored_without_its_secret():
    conv_id = make_conversation()
    msg = store.add_message(conv_id, "assistant", "Je regarde la base")

    store.update_message(msg.id, f"Je regarde la base : {DSN}")

    assert stored_contents(conv_id) == ["Je regarde la base : postgresql://***@base.example:5432/prod"]


def test_a_message_without_secret_is_stored_as_is():
    conv_id = make_conversation()

    store.add_message(conv_id, "user", "Combien de candidatures en octobre ?")

    assert stored_contents(conv_id) == ["Combien de candidatures en octobre ?"]


def test_a_question_that_starts_a_turn_is_stored_without_its_secret():
    conv_id = make_conversation()

    store.start_turn(conv_id, f"Pourquoi {DSN} refuse-t-elle la connexion ?")

    assert stored_contents(conv_id) == ["Pourquoi postgresql://***@base.example:5432/prod refuse-t-elle la connexion ?"]
