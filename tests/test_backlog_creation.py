import pytest

from lib import backlog_creation as creation


def ticket(**fields):
    values = {
        "title": "Masquer les candidatures anciennes",
        "body": ":autometa: Les employeurs gardent l'accès.",
        "teams": ["e1"],
        "status": "Cadrage",
        "types": ["Fonctionnalité"],
    }
    values.update(fields)
    return creation.Ticket(**values)


FIGMA = "https://www.figma.com/design/AbCdEfGhIjKlMnOpQrStUv/Maquette"
STATUSES = ["Archivé", "Bac à sable 🏝️", "Métier", "Cadrage", "𝗗𝗘𝗩 Prêt à développer", "𝗗𝗘𝗩 Ce sprint", "𝗗𝗘𝗩 En prod"]
SCHEMA = {"teams": "te-ams", "epics": "e-pics", "statuses": STATUSES, "types": ["Fonctionnalité", "Bug"]}


def test_dod_4_build_properties_sets_only_allowed_fields():
    props = creation.build_properties(ticket(figma=FIGMA, epic="p1", author_field="UX", author_notion_id="u1"), SCHEMA)
    assert props == {
        "Nom": {"title": [{"text": {"content": "Masquer les candidatures anciennes"}}]},
        "Pizza team": {"relation": [{"id": "e1"}]},
        "Statut": {"select": {"name": "Cadrage"}},
        "Type": {"multi_select": [{"name": "Fonctionnalité"}]},
        "Figma": {"url": FIGMA},
        "Epic - feuille de route": {"relation": [{"id": "p1"}]},
        "UX": {"people": [{"id": "u1"}]},
    }


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"status": "𝗗𝗘𝗩 En prod"}, "Statut non proposable : .* Valeurs : Bac à sable 🏝️, Métier, Cadrage, 𝗗𝗘𝗩 Prêt"),
        ({"status": "𝗗𝗘𝗩 Ce sprint"}, "Statut non proposable"),
        ({"status": "stand-by"}, "Statut non proposable"),
        ({"types": ["Épopée"]}, "Type inconnu : .* Valeurs : Fonctionnalité, Bug"),
        ({"types": ["Tâche"]}, "Type inconnu"),
        ({"types": []}, "Type inconnu"),
        ({"teams": []}, "Au moins une équipe"),
        ({"author_field": "Responsable(s)", "author_notion_id": "u1"}, "Champ d'auteur inconnu"),
        ({"author_field": "Responsable(s)"}, "Champ d'auteur inconnu"),
    ],
)
def test_dod_4_build_properties_refuses(fields, message):
    with pytest.raises(ValueError, match=message):
        creation.build_properties(ticket(**fields), SCHEMA)


def paragraph(text):
    return {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def notion_blocks(markdown):
    return creation.notion.markdown_to_blocks(markdown)


MENTION = {"type": "mention", "mention": {"type": "custom_emoji", "custom_emoji": {"id": "emoji-1"}}}


def test_dod_4_place_marker_inserts_the_emoji():
    blocks = creation.place_marker([paragraph(":autometa: Les employeurs gardent l'accès.")], "emoji-1")
    texts = blocks[0]["paragraph"]["rich_text"]
    assert texts[0] == MENTION
    assert texts[1]["text"]["content"] == " "
    assert texts[2]["text"]["content"] == "Les employeurs gardent l'accès."


def test_place_marker_without_emoji_keeps_the_text_once():
    blocks = creation.place_marker([paragraph(":autometa: Texte")], None)
    assert [t["text"]["content"] for t in blocks[0]["paragraph"]["rich_text"]] == [":autometa:", " ", "Texte"]


def test_place_marker_adds_a_missing_marker():
    blocks = creation.place_marker([paragraph("Texte")], "emoji-1")
    assert blocks[0]["paragraph"]["rich_text"][0] == MENTION
    assert [t["text"]["content"] for t in blocks[0]["paragraph"]["rich_text"][1:]] == [" ", "Texte"]


def test_place_marker_targets_the_first_paragraph_after_a_heading():
    title = {"type": "heading_2", "heading_2": {"rich_text": []}}
    blocks = creation.place_marker([title, paragraph("Texte")], "emoji-1")
    assert blocks[0] == title
    assert blocks[1]["paragraph"]["rich_text"][0] == MENTION


def test_place_marker_creates_a_paragraph_when_the_body_has_none():
    title = {"type": "heading_2", "heading_2": {"rich_text": []}}
    blocks = creation.place_marker([title], "emoji-1")
    assert blocks[0]["paragraph"]["rich_text"] == [MENTION]
    assert blocks[1] == title


def test_place_marker_leaves_a_later_paragraph_alone():
    blocks = creation.place_marker(
        notion_blocks("## Périmètre\n- x\n\n**Version A**"),
        "emoji-1",
    )
    assert blocks[0]["paragraph"]["rich_text"] == [MENTION]
    assert blocks[-1]["paragraph"]["rich_text"][0]["text"]["content"] == "Version A"
    assert len(blocks[-1]["paragraph"]["rich_text"]) == 1


def test_dod_4_check_body_refuses_a_title_in_the_body():
    with pytest.raises(ValueError, match="le titre ne va pas dans le corps"):
        creation.check_body(ticket(body="\n# Un titre\n\nTexte"))


def test_autometa_emoji_filters_by_name(mocker):
    call = mocker.patch("lib.notion.notion_request", return_value={"results": [{"id": "e", "name": "autometa"}]})
    assert creation.autometa_emoji() == "e"
    assert "name=autometa" in call.call_args.args[1]


def test_autometa_emoji_ignores_another_name_first(mocker):
    results = [{"id": "x", "name": "autometa-beta"}, {"id": "e", "name": "autometa"}]
    mocker.patch("lib.notion.notion_request", return_value={"results": results})
    assert creation.autometa_emoji() == "e"


def test_autometa_emoji_missing(mocker):
    mocker.patch("lib.notion.notion_request", return_value={"results": []})
    assert creation.autometa_emoji() is None


def notion_page(id_, title, teams=()):
    return {
        "id": id_,
        "properties": {
            "Nom": {"type": "title", "title": [{"plain_text": title}]},
            "Pizza team": {"relation": [{"id": e} for e in teams]},
        },
    }


EMPLOIS = notion_page("e1", "Emplois")
RUN = notion_page("p1", "RUN", teams=("e1",))


@pytest.mark.parametrize(
    ("teams", "epics", "fields", "message"),
    [
        ([], [], {"names": {"e1": "Emplois"}}, "e1 n'est pas une équipe produit active"),
        ([EMPLOIS], [], {"epic": "p1", "names": {"e1": "Emplois", "p1": "RUN"}}, "p1 n'est pas un épic actif"),
        ([notion_page("e1", "Prescription")], [], {"names": {"e1": "Emplois"}}, "ne s'appelle pas « Emplois »"),
        ([EMPLOIS], [], {}, "nom non fourni"),
        (
            [EMPLOIS],
            [notion_page("p1", "RUN", teams=("autre",))],
            {"epic": "p1", "names": {"e1": "Emplois", "p1": "RUN"}},
            "aucune des équipes",
        ),
    ],
)
def test_dod_4_check_relations_refuses(mocker, teams, epics, fields, message):
    mocker.patch.object(creation.backlog, "active_teams", return_value=teams)
    mocker.patch.object(creation.backlog, "active_epics", return_value=epics)
    with pytest.raises(ValueError, match=message):
        creation.check_relations(ticket(**fields), SCHEMA)


def test_dod_4_check_relations_accepts_active_pages_of_the_schema_databases(mocker):
    teams = mocker.patch.object(creation.backlog, "active_teams", return_value=[EMPLOIS])
    epics = mocker.patch.object(creation.backlog, "active_epics", return_value=[RUN])
    creation.check_relations(ticket(epic="p1", names={"e1": "Emplois", "p1": "RUN"}), SCHEMA)
    teams.assert_called_once_with("te-ams")
    epics.assert_called_once_with("e-pics")


def test_check_relations_without_epic_does_not_read_epics(mocker):
    mocker.patch.object(creation.backlog, "active_teams", return_value=[EMPLOIS])
    epics = mocker.patch.object(creation.backlog, "active_epics")
    creation.check_relations(ticket(names={"e1": "Emplois"}), SCHEMA)
    epics.assert_not_called()


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"body": "x" * 2000}, "2000 caractères ou plus"),
        ({"body": "| A | B |\n|---|---|\n| court | " + "c" * 2000 + " |"}, "cellule ou bloc de code de 2000"),
        ({"title": "t" * 2000}, "Titre refusé : 2000 caractères ou plus"),
        ({"body": "a" * 1500 + "\n" + "b" * 1500}, "2000 caractères ou plus"),
        ({"body": "```\n" + "\n".join("c" * 50 for _ in range(60)) + "\n```"}, "2000 caractères ou plus"),
        ({"body": "\n".join(f"- point {i}" for i in range(101))}, "Ticket trop long"),
        ({"body": "voir [lien](javascript:alert)"}, "Lien refusé"),
        ({"body": "voir [lien](/relatif)"}, "Lien refusé"),
        ({"body": "voir [x](javascript:x y)"}, "Lien refusé"),
        ({"body": "voir [x]( javascript:x)"}, "Lien refusé"),
        ({"figma": "https://exemple.fr/design"}, "lien Figma"),
        ({"figma": "https://evil.example/?u=figma.com/design/AbCdEfGhIjKlMnOpQrStUv"}, "lien Figma"),
    ],
)
def test_dod_4_check_body_refuses_before_any_request(mocker, fields, message):
    call = mocker.patch("lib.notion.notion_request")
    with pytest.raises(ValueError, match=message):
        creation.create_ticket(ticket(**fields))
    call.assert_not_called()


@pytest.mark.parametrize("url", [FIGMA, "https://figma.com/design/AbCdEfGhIjKlMnOpQrStUv/Maquette?node-id=1-2"])
def test_check_body_accepts_figma_links_with_or_without_www(url):
    assert creation.check_body(ticket(figma=url)) is None


def test_dod_4_check_body_accepts_http_links_and_short_lines():
    assert (
        creation.check_body(ticket(body="voir [a](https://x.fr/a) et [b](http://x.fr)\n\n" + "y" * 1999, figma=FIGMA))
        is None
    )


@pytest.mark.parametrize(("count", "refused"), [(99, False), (100, True)])
def test_dod_4_check_body_keeps_room_for_the_marker_under_100_blocks(count, refused):
    body = "\n\n".join(f"Paragraphe {i}" for i in range(count))
    if refused:
        with pytest.raises(ValueError, match="Ticket trop long : 100 blocs, 99 au plus"):
            creation.check_body(ticket(body=body))
    else:
        creation.check_body(ticket(body=body))


def test_dod_4_create_ticket_sends_a_single_creation(mocker):
    mocker.patch.object(creation.backlog, "backlog_schema", return_value=SCHEMA)
    mocker.patch.object(creation.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch.object(creation, "autometa_emoji", return_value=None)
    verification = mocker.patch.object(creation, "check_relations")
    mocker.patch("lib.notion.query_database", return_value=[])
    mocker.patch("lib.notion.markdown_to_blocks", return_value=[paragraph(str(i)) for i in range(3)])
    call = mocker.patch("lib.notion.notion_request", return_value={"id": "p", "url": "https://notion/p"})
    assert creation.create_ticket(ticket()) == ("p", "https://notion/p")
    call.assert_called_once()
    assert call.call_args.args[:2] == ("POST", "pages")
    assert call.call_args.args[2]["parent"] == {"database_id": "backlog"}
    assert len(call.call_args.args[2]["children"]) == 3
    verification.assert_called_once()


def test_dod_4_create_ticket_writes_nothing_when_checks_fail(mocker):
    mocker.patch.object(creation.backlog, "backlog_schema", return_value=SCHEMA)
    mocker.patch.object(creation, "check_relations", side_effect=ValueError("Relation refusée"))
    call = mocker.patch("lib.notion.notion_request")
    with pytest.raises(ValueError, match="Relation refusée"):
        creation.create_ticket(ticket())
    call.assert_not_called()


def test_prepare_returns_the_real_payload_with_the_marker_without_writing(mocker):
    mocker.patch.object(creation.backlog, "backlog_schema", return_value=SCHEMA)
    mocker.patch.object(creation.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch.object(creation, "autometa_emoji", return_value="emoji-1")
    mocker.patch.object(creation, "check_relations")
    mocker.patch("lib.notion.query_database", return_value=[])
    call = mocker.patch("lib.notion.notion_request")
    payload = creation.prepare(ticket(body="Texte."))
    call.assert_not_called()
    assert payload["parent"] == {"database_id": "backlog"}
    assert payload["properties"]["Nom"]["title"][0]["text"]["content"] == "Masquer les candidatures anciennes"
    assert payload["children"][0]["paragraph"]["rich_text"][0] == MENTION


def test_prepare_refuses_a_recent_ticket_with_the_same_title(mocker):
    mocker.patch.object(creation.backlog, "backlog_schema", return_value=SCHEMA)
    mocker.patch.object(creation.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch.object(creation, "autometa_emoji", return_value=None)
    mocker.patch.object(creation, "check_relations")
    query = mocker.patch("lib.notion.query_database", return_value=[{"url": "https://notion/deja"}])
    call = mocker.patch("lib.notion.notion_request")
    with pytest.raises(ValueError, match="vient d'être créé : https://notion/deja"):
        creation.prepare(ticket())
    call.assert_not_called()
    assert query.call_args.args[0] == "backlog"
    filters = query.call_args.kwargs["filter"]["and"]
    assert {"property": "Nom", "title": {"equals": "Masquer les candidatures anciennes"}} in filters
    assert {"property": "Statut", "select": {"does_not_equal": "Annulé"}} in filters
    recent = next(f for f in filters if f.get("timestamp") == "created_time")
    assert len(recent["created_time"]["on_or_after"]) == len("2026-10-30T10:00:00+00:00")
