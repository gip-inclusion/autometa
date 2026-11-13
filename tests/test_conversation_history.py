"""Le script d'historique : il ne cherche que dans les conversations de l'utilisateur courant."""

import pytest

from skills import conversation_history as history
from web.database import store

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("app")]

ALICE = "alice@example.com"
BOB = "bob@example.com"


def conversation(user_id, content, title="Sujet"):
    conv = store.create_conversation(user_id=user_id)
    store.update_conversation(conv.id, title=title)
    store.add_message(conv.id, "user", content)
    return conv


def run(monkeypatch, *argv, user=ALICE, current=None):
    if user:
        monkeypatch.setenv("AUTOMETA_USER_EMAIL", user)
    else:
        monkeypatch.delenv("AUTOMETA_USER_EMAIL", raising=False)
    if current:
        monkeypatch.setenv("AUTOMETA_CONVERSATION_ID", current)
    monkeypatch.setattr("sys.argv", ["conversation_history.py", *argv])
    history.main()


def test_search_never_returns_another_users_conversation(monkeypatch, capsys):
    mine = conversation(ALICE, "Candidatures par département")
    theirs = conversation(BOB, "Candidatures par département")

    run(monkeypatch, "--search", "candidatures département")

    out = capsys.readouterr().out
    assert mine.id in out
    assert theirs.id not in out


def test_search_leaves_out_the_current_conversation(monkeypatch, capsys):
    earlier = conversation(ALICE, "Trafic de Dora")
    current = conversation(ALICE, "Trafic de Dora, suite")

    run(monkeypatch, "--search", "trafic dora", current=current.id)

    out = capsys.readouterr().out
    assert earlier.id in out
    assert current.id not in out


@pytest.mark.parametrize("argv", [("--search", "candidatures"), ("--show", "x")], ids=["search", "show"])
def test_without_a_current_user_nothing_is_read(monkeypatch, capsys, argv):
    conversation(BOB, "Candidatures")

    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, *argv, user=None)

    assert exc.value.code == 2
    assert capsys.readouterr().out == ""


def test_show_reads_a_conversation_cited_by_its_link(monkeypatch, capsys):
    cited = conversation(BOB, "Taux d'orientation", title="Orientations")

    run(monkeypatch, "--show", f"https://autometa.inclusion.gouv.fr/explorations/{cited.id}")

    out = capsys.readouterr().out
    assert "Orientations" in out
    assert "Taux d'orientation" in out


def test_show_refuses_an_id_prefix(monkeypatch, capsys):
    cited = conversation(BOB, "Taux d'orientation")

    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, "--show", cited.id[:8])

    assert exc.value.code == 1
    assert "Taux d'orientation" not in capsys.readouterr().out
