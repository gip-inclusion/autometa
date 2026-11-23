"""Le script du skill save_report : auteur et conversation tirés de l'environnement, lecture et recherche de rapports."""

import json
import runpy

import pytest

from skills.save_report.scripts import save_report as cli
from web.database import store

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("app")]


def make_report(title, content, **fields):
    return store.create_report(title=title, content=content, **fields)


def run(monkeypatch, capsys, *argv):
    monkeypatch.setattr("sys.argv", ["save_report.py", *argv])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(cli.__file__, run_name="__main__")
    assert exc.value.code == 0
    return capsys.readouterr().out


def report_ids_shown_in(conversation_id):
    messages = store.get_conversation(conversation_id, include_messages=True).messages
    return [json.loads(m.content)["report_id"] for m in messages if m.type == "report"]


def test_new_report_belongs_to_the_agent_user_and_its_conversation(monkeypatch):
    conversation = store.create_conversation(user_id="alice@x")
    other = store.create_conversation(user_id="bob@x")
    monkeypatch.setenv("AUTOMETA_CONVERSATION_ID", conversation.id)
    monkeypatch.setenv("AUTOMETA_USER_EMAIL", "alice@x")

    result = cli.save_report(title="Trafic", content="# Trafic")

    report = store.get_report(result["report_id"])
    assert (report.user_id, report.source_conversation_id) == ("alice@x", conversation.id)
    assert report_ids_shown_in(conversation.id) == [report.id]
    assert report_ids_shown_in(other.id) == []


def test_a_report_saved_outside_an_agent_has_no_author_nor_conversation(monkeypatch):
    monkeypatch.delenv("AUTOMETA_CONVERSATION_ID", raising=False)
    monkeypatch.delenv("AUTOMETA_USER_EMAIL", raising=False)

    result = cli.save_report(title="Trafic", content="# Trafic")

    report = store.get_report(result["report_id"])
    assert (report.user_id, report.source_conversation_id) == (None, None)


def test_show_prints_metadata_and_content(monkeypatch, capsys):
    report = make_report(
        "Orientations", "# Orientations\n\nTaux par prescripteur.", user_id="alice@x", source_conversation_id="c-1"
    )

    out = run(monkeypatch, capsys, "--show", str(report.id))

    assert "alice@x" in out
    assert "/c/c-1" in out
    assert "Taux par prescripteur." in out


@pytest.mark.parametrize(
    ("query", "found"),
    [
        ("trafic", {"Trafic mensuel"}),
        ("prescripteurs orientation", {"Orientations"}),
        ("trafic prescripteurs", set()),
    ],
    ids=["title", "every word in the content", "words split across reports"],
)
def test_search_matches_title_or_content_of_live_reports(monkeypatch, capsys, query, found):
    titles = {"Trafic mensuel", "Orientations", "Trafic archivé"}
    make_report("Trafic mensuel", "Visites de La plateforme")
    make_report("Orientations", "Taux d'orientation des prescripteurs")
    store.archive_report(make_report("Trafic archivé", "Visites").id)

    out = run(monkeypatch, capsys, "--search", query)

    assert {title for title in titles if f"] {title} (" in out} == found


@pytest.mark.parametrize("query", ["", "  "], ids=["empty", "blank"])
def test_search_refuses_a_query_without_words(monkeypatch, capsys, query):
    monkeypatch.setattr("sys.argv", ["save_report.py", "--search", query])

    with pytest.raises(SystemExit) as exc:
        runpy.run_path(cli.__file__, run_name="__main__")

    assert exc.value.code == 2
    assert "--search needs at least one word" in capsys.readouterr().err
