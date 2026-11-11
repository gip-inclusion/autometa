import argparse
import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import httpx
import pytest

from lib import backlog
from lib.figma import Frame
from skills.draft_ticket.scripts import common

SCRIPTS = Path(__file__).parent.parent / "skills/draft_ticket/scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(f"draft_ticket_{name}", SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTEXT = {
    "generated_at": "2026-10-30T02:00:00+00:00",
    "teams": [
        {
            "id": "e1",
            "name": "Emplois inclusifs et dispositifs réglementés",
            "epics": [{"id": "p1", "name": "RUN EMPLOIS"}],
            "recent_titles": [],
        },
    ],
}
AUTHOR = backlog.Author(name="Camille", roles=["Responsable d'équipe"], teams=["e1"], notion_id="u1")


def draft(tmp_path, **fields):
    values = {
        "title": "Masquer les candidatures anciennes",
        "body": ":autometa: Texte.",
        "teams": ["Emplois inclusifs et dispositifs réglementés"],
        "status": "Cadrage",
        "types": ["Fonctionnalité"],
        "epic": "RUN EMPLOIS",
    }
    values.update(fields)
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(values, ensure_ascii=False))
    return str(path)


def setup_create(mocker):
    create = load("create")
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(create.backlog_storage, "current_context", return_value=CONTEXT)
    mocker.patch.object(create.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch.object(create.backlog, "find_author", return_value=AUTHOR)
    mocker.patch.object(create.backlog_creation, "check_relations")
    mocker.patch.object(create.backlog_creation, "autometa_emoji", return_value="emoji-1")
    mocker.patch("lib.notion.query_database", return_value=[])
    creation = mocker.patch.object(create.backlog_creation, "create_ticket", return_value=("p", "https://notion/p"))
    return create, creation


def test_dod_5_create_without_go_creates_nothing(mocker, tmp_path):
    create, creation = setup_create(mocker)
    output = create.run(Namespace(draft=draft(tmp_path), go=False))
    creation.assert_not_called()
    create.backlog_creation.check_relations.assert_called_once()
    assert output.startswith("Vérification seulement")
    assert '"POM"' in output
    assert "Corps : 1 blocs" in output
    assert "Texte." in output


def test_dod_5_create_without_go_goes_through_prepare(mocker, tmp_path):
    create, creation = setup_create(mocker)
    prepare = mocker.spy(create.backlog_creation, "prepare")
    create.run(Namespace(draft=draft(tmp_path), go=False))
    prepare.assert_called_once()
    creation.assert_not_called()


def test_dod_5_create_with_go_resolves_names_and_author(mocker, tmp_path):
    create, creation = setup_create(mocker)
    assert create.run(Namespace(draft=draft(tmp_path), go=True)) == "Ticket créé : https://notion/p"
    ticket = creation.call_args.args[0]
    assert (ticket.teams, ticket.epic, ticket.author_field, ticket.author_notion_id) == (["e1"], "p1", "POM", "u1")
    assert ticket.names == {"e1": "Emplois inclusifs et dispositifs réglementés", "p1": "RUN EMPLOIS"}


def test_create_keeps_the_field_given_by_the_author(mocker, tmp_path):
    create, creation = setup_create(mocker)
    create.run(Namespace(draft=draft(tmp_path, author_field="UX"), go=True))
    assert creation.call_args.args[0].author_field == "UX"


@pytest.mark.parametrize(
    ("fields", "message"),
    [({"teams": ["Équipe fantôme"]}, "Équipe inconnue"), ({"epic": "Épic fantôme"}, "Épic inconnu")],
)
def test_create_refuses_an_unknown_name(mocker, tmp_path, fields, message):
    create, creation = setup_create(mocker)
    with pytest.raises(ValueError, match=message):
        create.run(Namespace(draft=draft(tmp_path, **fields), go=True))
    creation.assert_not_called()


@pytest.mark.parametrize(
    ("url", "prefix"),
    [
        ("https://exemple.fr/x", "Ce n'est pas un lien Figma"),
        ("https://www.figma.com/board/AAAAAAAAAAAAAAAAAAAAAA/x", "Lien Figma sans cadre précis"),
    ],
)
def test_dod_1_mockup_does_not_read_an_unusable_link(mocker, url, prefix):
    mockup = load("mockup")
    mocker.patch.object(mockup.config, "FIGMA_ACCESS_TOKEN", "jeton")
    read = mocker.patch.object(mockup.figma, "read_frames")
    assert mockup.run(Namespace(url=url)).startswith(prefix)
    read.assert_not_called()


def test_dod_1_mockup_lists_frames_texts_and_images(mocker, tmp_path):
    mockup = load("mockup")
    mocker.patch.object(mockup.config, "FIGMA_ACCESS_TOKEN", "jeton")
    mocker.patch.object(mockup, "images_folder", return_value=tmp_path)
    mocker.patch.object(
        mockup.figma, "read_frames", return_value=[Frame(id="2:2", name="Choix 1", texts=["Accepter"], width=100)]
    )
    mocker.patch.object(mockup.figma, "export_images", return_value={"2:2": tmp_path / "frame-1.png"})
    output = mockup.run(Namespace(url="https://www.figma.com/design/AAAAAAAAAAAAAAAAAAAAAA/x?node-id=1-2"))
    assert "## Cadre 1 : Choix 1" in output
    assert f"Image à regarder : {tmp_path / 'frame-1.png'}" in output
    assert "- Accepter" in output


FRAME_LINK = "https://www.figma.com/design/AAAAAAAAAAAAAAAAAAAAAA/x?node-id=1-2"
REQUEST = httpx.Request("GET", "https://api.figma.com")


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            httpx.HTTPStatusError("403", request=REQUEST, response=httpx.Response(403)),
            "Maquette non lue : Figma répond 403 (accès refusé ou fichier introuvable).",
        ),
        (
            httpx.HTTPStatusError("429", request=REQUEST, response=httpx.Response(429)),
            "Maquette non lue : Figma limite les appels (429), réessayer dans une minute.",
        ),
        (httpx.ConnectTimeout("lent", request=REQUEST), "Maquette non lue : Figma ne répond pas."),
    ],
)
def test_dod_1_mockup_says_why_it_is_not_read(mocker, error, expected):
    mockup = load("mockup")
    mocker.patch.object(mockup.config, "FIGMA_ACCESS_TOKEN", "jeton")
    mocker.patch.object(mockup.figma, "read_frames", side_effect=error)
    assert mockup.run(Namespace(url=FRAME_LINK)) == expected


def test_dod_1_mockup_reports_a_missing_frame(mocker):
    mockup = load("mockup")
    mocker.patch.object(mockup.config, "FIGMA_ACCESS_TOKEN", "jeton")
    mocker.patch.object(mockup.figma, "read_frames", return_value=[])
    assert mockup.run(Namespace(url=FRAME_LINK)).startswith("Cadre introuvable dans ce fichier Figma")


def test_dod_1_mockup_keeps_the_texts_when_images_fail(mocker):
    mockup = load("mockup")
    mocker.patch.object(mockup.config, "FIGMA_ACCESS_TOKEN", "jeton")
    mocker.patch.object(
        mockup.figma, "read_frames", return_value=[Frame(id="2:2", name="Choix 1", texts=["Accepter"], width=100)]
    )
    mocker.patch.object(mockup.figma, "export_images", side_effect=httpx.ReadTimeout("lent", request=REQUEST))
    output = mockup.run(Namespace(url=FRAME_LINK))
    assert "Images non rendues (Maquette non lue : Figma ne répond pas.) : se fier aux textes." in output
    assert "- Accepter" in output
    assert "Image à regarder" not in output


def test_author_without_session_says_so(mocker):
    author = load("author")
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(common.config, "NOTION_ANNUAIRE_DB", "directory")
    mocker.patch.object(author.config, "agent_user_email", return_value=None)
    assert author.run(Namespace(team=[])) == "Personne connectée inconnue : l'auteur ne sera pas inscrit."


def test_dod_3_author_gives_the_field_for_the_target_team(mocker):
    author = load("author")
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(common.config, "NOTION_ANNUAIRE_DB", "directory")
    mocker.patch.object(author.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch.object(author.backlog, "find_author", return_value=AUTHOR)
    mocker.patch.object(author.backlog_storage, "current_context", return_value=CONTEXT)
    output = author.run(Namespace(team=["Emplois inclusifs et dispositifs réglementés"]))
    assert "Rôles : Responsable d'équipe" in output
    assert "Inscrit dans : POM" in output


def test_context_refresh_reads_notion_and_stores(mocker):
    script = load("context")
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(script.backlog, "load_context", return_value=CONTEXT)
    store = mocker.patch.object(script.backlog_storage, "save_context")
    output = script.run(Namespace(refresh=True))
    store.assert_called_once_with(CONTEXT)
    assert "## Emplois inclusifs et dispositifs réglementés" in output


def test_dod_3_duplicates_lists_similar_tickets(mocker):
    duplicates = load("duplicates")
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(
        duplicates.backlog,
        "find_duplicates",
        return_value=[{"title": "T", "url": "u", "status": "Cadrage", "shared": 3}],
    )
    assert duplicates.run(Namespace(title="Masquer les candidatures")) == "- T (Cadrage, 3 mots communs) u"


def call_main(mocker, script, *arguments):
    mocker.patch("sys.argv", [f"{script.__name__}.py", *arguments])
    script.main()


def test_create_without_argument_reads_and_consumes_the_conversation_draft(mocker, tmp_path):
    create, creation = setup_create(mocker)
    path = tmp_path / "draft.json"
    path.write_text(Path(draft(tmp_path)).read_text())
    mocker.patch.object(create, "draft_path", return_value=path)
    assert create.run(Namespace(draft=None, go=True)).startswith("Ticket créé")
    assert not path.exists()
    creation.assert_called_once()


def test_create_default_path_depends_on_the_conversation(mocker):
    create = load("create")
    mocker.patch.object(create.config, "agent_conversation_id", return_value="conv-1")
    assert create.draft_path() == Path("/tmp/draft_ticket/conv-1/draft.json")


def test_create_deletes_the_draft_after_creation(mocker, tmp_path):
    create, _ = setup_create(mocker)
    path = draft(tmp_path)
    create.run(Namespace(draft=path, go=True))
    assert not Path(path).exists()


@pytest.mark.parametrize("field", ["title", "body", "teams", "status", "types"])
def test_create_refuses_a_draft_without_a_required_field(mocker, tmp_path, field):
    create, creation = setup_create(mocker)
    with pytest.raises(ValueError, match=field):
        create.run(Namespace(draft=draft(tmp_path, **{field: None}), go=True))
    creation.assert_not_called()


def test_create_refuses_teams_that_are_not_a_list(mocker, tmp_path):
    create, _ = setup_create(mocker)
    with pytest.raises(ValueError, match="doit être une liste"):
        create.run(Namespace(draft=draft(tmp_path, teams="Emplois"), go=True))


def test_create_without_backlog_database_refuses(mocker, tmp_path):
    create, creation = setup_create(mocker)
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", None)
    with pytest.raises(ValueError, match="NOTION_BACKLOG_DB absent"):
        create.run(Namespace(draft=draft(tmp_path), go=True))
    creation.assert_not_called()


def test_create_goes_on_without_author_when_the_directory_is_unreadable(mocker, tmp_path):
    create, creation = setup_create(mocker)
    mocker.patch.object(create.backlog, "find_author", side_effect=httpx.ReadTimeout("lent", request=REQUEST))
    output = create.run(Namespace(draft=draft(tmp_path), go=True))
    assert "Ticket créé : https://notion/p" in output
    assert "Auteur non inscrit : annuaire ou comptes Notion illisibles." in output
    assert creation.call_args.args[0].author_field is None


def test_create_without_known_author_still_creates(mocker, tmp_path):
    create, creation = setup_create(mocker)
    mocker.patch.object(create.backlog, "find_author", return_value=None)
    create.run(Namespace(draft=draft(tmp_path), go=True))
    assert creation.call_args.args[0].author_notion_id is None


def test_dod_5_create_dry_run_shows_the_resolved_names(mocker, tmp_path):
    create, _ = setup_create(mocker)
    output = create.run(Namespace(draft=draft(tmp_path), go=False))
    assert '"p1": "RUN EMPLOIS"' in output


def test_dod_5_create_cli_without_go_creates_nothing(mocker, tmp_path, capsys):
    create, creation = setup_create(mocker)
    call_main(mocker, create, draft(tmp_path))
    creation.assert_not_called()
    assert capsys.readouterr().out.startswith("Vérification seulement")


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            httpx.HTTPStatusError("404", request=REQUEST, response=httpx.Response(404, text="object_not_found")),
            "Notion répond 404 : object_not_found",
        ),
        (httpx.ConnectTimeout("lent", request=REQUEST), "Notion ne répond pas : vérifier dans Notion"),
    ],
)
def test_create_cli_reports_the_notion_error(mocker, tmp_path, error, message):
    create, creation = setup_create(mocker)
    creation.side_effect = error
    path = draft(tmp_path)
    with pytest.raises(SystemExit, match=message):
        call_main(mocker, create, path, "--go")
    assert Path(path).exists()


def test_create_cli_refuses_a_missing_file(mocker, tmp_path):
    create, _ = setup_create(mocker)
    with pytest.raises(SystemExit, match="Refusé, rien n'est créé"):
        call_main(mocker, create, str(tmp_path / "absent.json"))


def test_create_cli_refuses_invalid_json(mocker, tmp_path):
    create, _ = setup_create(mocker)
    invalid_file = tmp_path / "mauvais.json"
    invalid_file.write_text("{pas du json")
    with pytest.raises(SystemExit, match="Refusé, rien n'est créé"):
        call_main(mocker, create, str(invalid_file))


def test_create_cli_refuses_an_unknown_team(mocker, tmp_path):
    create, _ = setup_create(mocker)
    with pytest.raises(SystemExit, match="Équipe inconnue"):
        call_main(mocker, create, draft(tmp_path, teams=["Équipe fantôme"]))


@pytest.mark.parametrize("name", ["context", "duplicates", "author"])
def test_read_scripts_without_backlog_database_say_so(mocker, name):
    script = load(name)
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", None)
    output = script.run(Namespace(refresh=False, title="x", team=[]))
    assert output.startswith("NOTION_BACKLOG_DB absent")


def test_duplicates_without_result(mocker):
    duplicates = load("duplicates")
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(duplicates.backlog, "find_duplicates", return_value=[])
    assert duplicates.run(Namespace(title="x")) == "Aucun ticket proche."


def test_context_without_refresh_reads_the_stored_context(mocker):
    script = load("context")
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(script.backlog_storage, "current_context", return_value=CONTEXT)
    payload = mocker.patch.object(script.backlog, "load_context")
    assert "## Emplois inclusifs et dispositifs réglementés" in script.run(Namespace(refresh=False))
    payload.assert_not_called()


def test_author_not_found_says_so(mocker):
    author = load("author")
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(common.config, "NOTION_ANNUAIRE_DB", "directory")
    mocker.patch.object(author.config, "agent_user_email", return_value="x@exemple.fr")
    mocker.patch.object(author.backlog, "find_author", return_value=None)
    assert author.run(Namespace(team=[])).startswith("Absent de l'Annuaire")


def test_author_reports_an_unknown_team(mocker):
    author = load("author")
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(common.config, "NOTION_ANNUAIRE_DB", "directory")
    mocker.patch.object(author.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch.object(author.backlog, "find_author", return_value=AUTHOR)
    mocker.patch.object(author.backlog_storage, "current_context", return_value=CONTEXT)
    field = mocker.patch.object(author.backlog, "author_field", return_value="POM")
    output = author.run(Namespace(team=["Équipe fantôme", "Emplois inclusifs et dispositifs réglementés"]))
    assert "Équipe inconnue : Équipe fantôme (nom exact : voir context.py)" in output
    field.assert_called_once_with(AUTHOR, ["e1"])


def test_dod_1_mockup_without_figma_token_says_so(mocker):
    mockup = load("mockup")
    mocker.patch.object(mockup.config, "FIGMA_ACCESS_TOKEN", None)
    read = mocker.patch.object(mockup.figma, "read_frames")
    assert mockup.run(Namespace(url=FRAME_LINK)).startswith("FIGMA_ACCESS_TOKEN absent")
    read.assert_not_called()


def test_dod_1_mockup_does_not_claim_access_denied_on_a_500(mocker):
    mockup = load("mockup")
    mocker.patch.object(mockup.config, "FIGMA_ACCESS_TOKEN", "jeton")
    error = httpx.HTTPStatusError("500", request=REQUEST, response=httpx.Response(500))
    mocker.patch.object(mockup.figma, "read_frames", side_effect=error)
    assert mockup.run(Namespace(url=FRAME_LINK)) == "Maquette non lue : Figma répond 500."


def test_dod_1_mockup_reports_frames_without_text_or_image(mocker, tmp_path):
    mockup = load("mockup")
    mocker.patch.object(mockup.config, "FIGMA_ACCESS_TOKEN", "jeton")
    mocker.patch.object(mockup, "images_folder", return_value=tmp_path)
    frames = [
        Frame(id="2:2", name="Vide", texts=[], width=100),
        Frame(id="2:3", name="Autre", texts=["Ok"], width=100),
    ]
    mocker.patch.object(mockup.figma, "read_frames", return_value=frames)
    mocker.patch.object(mockup.figma, "export_images", return_value={"2:3": tmp_path / "c.png"})
    output = mockup.run(Namespace(url=FRAME_LINK))
    assert "Textes visibles : aucun" in output
    assert "Image non rendue" in output


def test_create_does_not_fail_when_the_draft_is_already_gone(mocker, tmp_path):
    create, creation = setup_create(mocker)
    path = Path(draft(tmp_path))
    creation.side_effect = lambda ticket: (path.unlink(), ("p", "https://notion/p"))[1]
    assert create.run(Namespace(draft=str(path), go=True)).startswith("Ticket créé")


def test_create_cli_treats_a_5xx_as_no_answer(mocker, tmp_path):
    create, creation = setup_create(mocker)
    creation.side_effect = httpx.HTTPStatusError(
        "502", request=REQUEST, response=httpx.Response(502, text="bad gateway")
    )
    with pytest.raises(SystemExit, match="Notion ne répond pas correctement : vérifier dans Notion"):
        call_main(mocker, create, draft(tmp_path), "--go")


def test_create_refuses_a_draft_that_is_not_an_object(mocker, tmp_path):
    create, _ = setup_create(mocker)
    array_file = tmp_path / "liste.json"
    array_file.write_text("[1, 2]")
    with pytest.raises(ValueError, match="objet JSON"):
        create.run(Namespace(draft=str(array_file), go=False))


def test_create_goes_on_without_author_after_429_retries(mocker, tmp_path):
    create, _ = setup_create(mocker)
    mocker.patch.object(create.backlog, "find_author", side_effect=RuntimeError("429"))
    assert "Auteur non inscrit" in create.run(Namespace(draft=draft(tmp_path), go=True))


@pytest.mark.parametrize("error", [httpx.ReadTimeout("lent", request=REQUEST), RuntimeError("429")])
def test_author_unreadable_does_not_exit_with_an_error(mocker, error):
    author = load("author")
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(common.config, "NOTION_ANNUAIRE_DB", "directory")
    mocker.patch.object(author.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch.object(author.backlog, "find_author", side_effect=error)
    assert author.run(Namespace(team=[])) == "Auteur non inscrit : annuaire ou comptes Notion illisibles."


@pytest.mark.parametrize(
    ("name", "arguments", "expected"),
    [
        ("context", [], "## Emplois inclusifs"),
        ("duplicates", ["Titre test"], "- T (Cadrage, 1 mots communs) u"),
        ("author", [], "Auteur : Camille"),
        ("mockup", ["https://www.figma.com/board/AAAAAAAAAAAAAAAAAAAAAA/x"], "Lien Figma sans cadre précis"),
    ],
)
def test_read_scripts_cli_print_their_result(mocker, capsys, name, arguments, expected):
    script = load(name)
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(common.config, "NOTION_ANNUAIRE_DB", "directory")
    mocker.patch.object(common.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch("lib.backlog_storage.current_context", return_value=CONTEXT)
    mocker.patch("lib.backlog.find_author", return_value=AUTHOR)
    mocker.patch(
        "lib.backlog.find_duplicates",
        return_value=[{"title": "T", "url": "u", "status": "Cadrage", "shared": 1}],
    )
    call_main(mocker, script, *arguments)
    assert expected in capsys.readouterr().out


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            httpx.HTTPStatusError("401", request=REQUEST, response=httpx.Response(401, text="unauthorized")),
            "Notion répond 401 : unauthorized",
        ),
        (httpx.ConnectTimeout("lent", request=REQUEST), "Notion ne répond pas."),
        (RuntimeError("429"), "Notion limite les appels : réessayer dans une minute."),
    ],
)
def test_run_cli_turns_notion_errors_into_one_line(mocker, error, message):
    parser = argparse.ArgumentParser()
    mocker.patch("sys.argv", ["script.py"])
    with pytest.raises(SystemExit, match=message):
        common.run_cli(mocker.Mock(side_effect=error), parser)


def test_run_cli_prints_the_result(mocker, capsys):
    mocker.patch("sys.argv", ["script.py"])
    common.run_cli(lambda args: "résultat", argparse.ArgumentParser())
    assert capsys.readouterr().out == "résultat\n"


@pytest.mark.parametrize(
    ("base", "directory", "requested", "expected"),
    [
        (None, None, False, "NOTION_BACKLOG_DB absent"),
        ("db", None, False, None),
        ("db", None, True, "NOTION_ANNUAIRE_DB absent"),
        ("db", "directory", True, None),
    ],
)
def test_check_config_names_the_missing_variable(mocker, base, directory, requested, expected):
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", base)
    mocker.patch.object(common.config, "NOTION_ANNUAIRE_DB", directory)
    message = common.check_config(directory=requested)
    assert (message is None) if expected is None else message.startswith(expected)


def test_create_cli_reports_notion_rate_limiting(mocker, tmp_path):
    create, creation = setup_create(mocker)
    creation.side_effect = RuntimeError("429")
    with pytest.raises(SystemExit, match="Notion limite les appels"):
        call_main(mocker, create, draft(tmp_path), "--go")


def test_author_without_notion_account_says_they_will_not_be_set(mocker):
    author = load("author")
    mocker.patch.object(common.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(common.config, "NOTION_ANNUAIRE_DB", "directory")
    mocker.patch.object(common.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch.object(
        author.backlog, "find_author", return_value=backlog.Author("Camille", ["Designer"], ["e1"], None)
    )
    mocker.patch.object(author.backlog_storage, "current_context", return_value=CONTEXT)
    output = author.run(Namespace(team=["Emplois inclusifs et dispositifs réglementés"]))
    assert "Inscrit dans : personne (pas de compte Notion)" in output
    assert "Inscrit dans : UX" not in output


def test_create_without_go_reports_an_author_without_notion_account(mocker, tmp_path):
    create, _ = setup_create(mocker)
    mocker.patch.object(create.backlog, "find_author", return_value=backlog.Author("Camille", [], ["e1"], None))
    output = create.run(Namespace(draft=draft(tmp_path), go=False))
    assert "Auteur non inscrit : pas de compte Notion." in output


def test_create_without_go_refuses_when_the_ticket_was_just_created(mocker, tmp_path):
    create, creation = setup_create(mocker)
    mocker.patch("lib.notion.query_database", return_value=[{"url": "https://notion/deja"}])
    with pytest.raises(ValueError, match="https://notion/deja"):
        create.run(Namespace(draft=draft(tmp_path), go=False))
    creation.assert_not_called()
