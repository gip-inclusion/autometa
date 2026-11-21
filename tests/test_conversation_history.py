"""Le script d'historique : il ne cherche que dans les conversations de l'utilisateur courant."""

from datetime import datetime, timezone

import pytest

from skills import conversation_history as history
from web.database import store
from web.db import get_db
from web.models import Conversation

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("app")]

ALICE = "alice@example.com"
BOB = "bob@example.com"
SHORT = "k3v9x2mq"
UUID = "21e937fb-0000-4000-8000-000000000001"
SITE = "https://autometa.inclusion.gouv.fr"


def conversation(user_id, content, title="Sujet", conv_id=None):
    """Une conversation créée par l'application, ou insérée sous l'identifiant donné."""
    if conv_id:
        now = datetime.now(timezone.utc)
        with get_db() as session:
            session.add(Conversation(id=conv_id, user_id=user_id, created_at=now, updated_at=now))
    else:
        conv_id = store.create_conversation(user_id=user_id).id
    store.update_conversation(conv_id, title=title)
    store.add_message(conv_id, "user", content)
    return store.get_conversation(conv_id, include_messages=False)


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
    assert f"  /c/{mine.id}  " in out
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


CITATIONS = {
    "adresse-courte": (SHORT, SITE + "/c/{id}"),
    "adresse-uuid": (UUID, SITE + "/c/{id}"),
    "ancienne-adresse-uuid": (UUID, SITE + "/explorations/{id}"),
    "ancienne-adresse-courte": (SHORT, SITE + "/explorations/{id}?message=Bonjour"),
    "permalien-dans-une-phrase": (SHORT, "Regarde " + SITE + "/c/{id}/12/table-1-abcdef#methode, la suite."),
    "ancien-permalien": (UUID, SITE + "/explorations/{id}/12/table-1-abcdef"),
    "lien-slack": (SHORT, "<" + SITE + "/c/{id}|Orientations>"),
    "lien-markdown": (UUID, "[la conversation](" + SITE + "/c/{id})"),
    "lien-de-l-ancienne-liste-court": (SHORT, SITE + "/explorations?conv={id}"),
    "lien-de-l-ancienne-liste-uuid": (UUID, "Vu sur " + SITE + "/explorations?conv={id}."),
    "identifiant-court": (SHORT, "{id}"),
    "identifiant-uuid": (UUID, "{id}"),
    "identifiant-entouré-de-blancs": (SHORT, "  {id}\n"),
}


@pytest.mark.parametrize(("conv_id", "cited"), CITATIONS.values(), ids=CITATIONS.keys())
def test_show_reads_a_conversation_cited_by_its_link_or_its_id(monkeypatch, capsys, conv_id, cited):
    conversation(BOB, "Taux d'orientation", title="Orientations", conv_id=conv_id)

    run(monkeypatch, "--show", cited.format(id=conv_id))

    out = capsys.readouterr().out
    assert "Orientations" in out
    assert "Taux d'orientation" in out


def test_show_reads_the_first_cited_address_that_names_a_conversation(monkeypatch, capsys):
    conversation(BOB, "Première citée", title="Première", conv_id=UUID)
    conversation(BOB, "Seconde citée", title="Seconde", conv_id=SHORT)

    run(monkeypatch, "--show", f"Pas https://example.org/c/zzzzzzzz mais {SITE}/c/{UUID}, puis {SITE}/c/{SHORT}")

    out = capsys.readouterr().out
    assert "Première citée" in out
    assert "Seconde citée" not in out


def test_show_does_not_read_a_conversation_from_the_number_of_one_of_its_messages(monkeypatch, capsys):
    cited = conversation(BOB, "Taux d'orientation")
    message = store.add_message(cited.id, "assistant", "Réponse").id

    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, "--show", f"{SITE}/m/{message}")

    assert exc.value.code == 1
    assert "Taux d'orientation" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "cited",
    [
        "Regarde les datasets du mois",
        f"Voir la conversation {UUID} d'hier",
        "datasets2",
        f"{SITE}/c/datasets2",
        f"{SITE}/c/{UUID}0",
        "https://example.org/datasets",
    ],
    ids=[
        "mot-de-huit-lettres",
        "uuid-dans-une-phrase",
        "neuf-caractères",
        "adresse-à-neuf-caractères",
        "adresse-à-uuid-prolongé",
        "autre-adresse",
    ],
)
def test_show_finds_no_conversation_in_a_text_that_does_not_cite_one(monkeypatch, capsys, cited):
    conversation(BOB, "Jeux de données", conv_id="datasets")
    conversation(BOB, "Jeux de données", conv_id=UUID)

    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, "--show", cited)

    assert exc.value.code == 1
    assert "Jeux de données" not in capsys.readouterr().out


def test_show_leaves_out_tool_calls_and_their_output(monkeypatch, capsys):
    cited = conversation(BOB, "Combien de candidatures ?")
    store.add_message(cited.id, "tool_result", '{"output": "1 024 lignes brutes"}')
    store.add_message(cited.id, "assistant", "12 000 candidatures.")

    run(monkeypatch, "--show", cited.id)

    out = capsys.readouterr().out
    assert "12 000 candidatures." in out
    assert "lignes brutes" not in out


@pytest.mark.parametrize("cited", ["{prefix}", SITE + "/c/{prefix}"], ids=["seul", "dans-une-adresse"])
@pytest.mark.parametrize(
    ("conv_id", "prefix"),
    [(UUID, UUID[:8]), (UUID, UUID[:-1]), (SHORT, SHORT[:-1])],
    ids=["premier-groupe-d-un-uuid", "uuid-moins-un-caractère", "court-moins-un-caractère"],
)
def test_show_refuses_an_id_prefix(monkeypatch, capsys, conv_id, prefix, cited):
    # Why: le premier groupe d'un UUID a la forme d'un identifiant court ; seule une lecture à l'identifiant exact,
    # jamais au préfixe, le refuse.
    conversation(BOB, "Taux d'orientation", conv_id=conv_id)

    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, "--show", cited.format(prefix=prefix))

    assert exc.value.code == 1
    assert "Taux d'orientation" not in capsys.readouterr().out


@pytest.mark.parametrize("query", ["", "  "], ids=["empty", "blank"])
def test_search_refuses_a_query_without_words(monkeypatch, capsys, query):
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, "--search", query)

    assert exc.value.code == 2
    assert "--search needs at least one word" in capsys.readouterr().err
