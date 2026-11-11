import pytest

from lib import backlog


def notion_title(text):
    return {"type": "title", "title": [{"plain_text": text}]}


def relation(*ids):
    return {"type": "relation", "relation": [{"id": i} for i in ids]}


def page(id_, title, status=None, url="", **relations):
    props = {"Nom": notion_title(title)}
    if status:
        props["Statut"] = {"type": "select", "select": {"name": status}}
    for name, ids in relations.items():
        props[name.replace("_", " ")] = relation(*ids)
    return {"id": id_, "url": url, "properties": props}


def response(*pages, cursor=None):
    return {"results": list(pages), "has_more": cursor is not None, "next_cursor": cursor}


def test_recent_titles_reads_through_query_database_and_cuts_to_the_count(mocker):
    query = mocker.patch(
        "lib.notion.query_database", return_value=[page("a", "A"), page("b", ""), page("c", "C"), page("d", "D")]
    )
    assert backlog.recent_titles("e1", 2) == ["A", "C"]
    assert query.call_args.kwargs["sorts"] == [{"timestamp": "created_time", "direction": "descending"}]


def test_find_author_keeps_only_the_first_record(mocker):
    mocker.patch.object(backlog.config, "NOTION_ANNUAIRE_DB", "directory")
    records = [page("f1", "Premiere"), page("f2", "Seconde")]
    mocker.patch("lib.notion.query_database", return_value=records)
    mocker.patch.object(backlog, "notion_user", return_value=None)
    assert backlog.find_author("x@exemple.fr").name == "Premiere"


def test_dod_2_load_context_groups_epics_and_titles_by_team(mocker):
    mocker.patch.object(backlog.config, "NOTION_BACKLOG_DB", "backlog")
    schema = {
        "properties": {
            "Pizza team": {"relation": {"database_id": "teams"}},
            "Epic - feuille de route": {"relation": {"database_id": "epics"}},
        }
    }
    payloads = {}
    tickets = {
        "e1": response(page("t1", "Modale DORA")),
        "e2": response(page("t3", ""), page("t2", "Fiche salarié")),
    }

    def notion(method, path, payload=None):
        if method == "GET":
            return schema
        base = path.split("/")[1]
        payloads[base] = payload
        if base == "backlog":
            return tickets[payload["filter"]["and"][0]["relation"]["contains"]]
        return {
            "teams": response(page("e1", "Prescription "), page("e2", "Emplois")),
            "epics": response(
                page("p1", "DORA - RUN", Pizza_team=["e1"]), page("p2", "RUN EMPLOIS", Pizza_team=["e2"])
            ),
        }[base]

    mocker.patch("lib.notion.notion_request", side_effect=notion)
    context = backlog.load_context()
    assert context["teams"] == [
        {
            "id": "e1",
            "name": "Prescription",
            "epics": [{"id": "p1", "name": "DORA - RUN"}],
            "recent_titles": ["Modale DORA"],
        },
        {
            "id": "e2",
            "name": "Emplois",
            "epics": [{"id": "p2", "name": "RUN EMPLOIS"}],
            "recent_titles": ["Fiche salarié"],
        },
    ]
    assert payloads["teams"]["filter"] == {
        "and": [
            {"property": "Activité", "select": {"equals": "Actif"}},
            {"property": "Type", "select": {"equals": "Équipe produit"}},
        ]
    }
    assert payloads["epics"]["filter"] == {
        "and": [
            {"property": "Statut", "status": {"does_not_equal": "Archivé"}},
            {"property": "Statut", "status": {"does_not_equal": "𝗘𝗡 𝗣𝗥𝗢𝗗 ce trimestre"}},
        ]
    }
    assert payloads["backlog"]["sorts"] == [{"timestamp": "created_time", "direction": "descending"}]
    assert payloads["backlog"]["filter"]["and"][1] == {"property": "Statut", "select": {"does_not_equal": "Annulé"}}


def test_format_context_sorts_teams_and_lists_epics_and_tickets():
    context = {
        "generated_at": "2026-10-30T02:00:00+00:00",
        "teams": [
            {"id": "e2", "name": "Prescription", "epics": [], "recent_titles": ["Modale DORA"]},
            {"id": "e1", "name": "Emplois", "epics": [{"id": "p", "name": "RUN EMPLOIS"}], "recent_titles": []},
        ],
    }
    assert backlog.format_context(context) == (
        "# Équipes produit actives (au 2026-10-30)\n\n"
        "## Emplois\n- Épics actifs : RUN EMPLOIS\n- Tickets récents : aucun\n\n"
        "## Prescription\n- Tickets récents :\n  - Modale DORA\n"
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Masquer aux employeurs les candidatures non acceptées",
            ["Masquer", "employeurs", "candidatures", "acceptées"],
        ),
        ("Afficher une modale pour les prescripteurs", ["modale", "prescripteurs"]),
        ("le la de", []),
        ("Permettre à l’employeur d'exporter la liste", ["employeur", "exporter", "liste"]),
        ("[DATA] Exporter les candidatures", ["Exporter", "candidatures"]),
    ],
)
def test_keywords(text, expected):
    assert backlog.keywords(text) == expected


def test_dod_3_find_duplicates_ranks_and_drops_weak_matches(mocker):
    mocker.patch.object(backlog.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch(
        "lib.notion.notion_request",
        return_value=response(
            page("a", "Masquer les candidatures des employeurs", status="Cadrage", url="u-a"),
            page("b", "Candidatures : export CSV", status="Métier", url="u-b"),
            page("c", "Masquer candidatures employeurs non acceptées", status="Bac à sable 🏝️", url="u-c"),
        ),
    )
    found = backlog.find_duplicates("Masquer aux employeurs les candidatures non acceptées")
    assert [t["url"] for t in found] == ["u-c", "u-a"]
    assert found[0] == {
        "title": "Masquer candidatures employeurs non acceptées",
        "url": "u-c",
        "status": "Bac à sable 🏝️",
        "shared": 4,
    }


def test_dod_3_find_duplicates_requires_half_of_the_keywords(mocker):
    mocker.patch.object(backlog.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch(
        "lib.notion.notion_request",
        return_value=response(
            page("a", "Export des candidatures employeurs", url="u-a"),
            page("b", "Export candidatures employeurs prescripteurs DDETS", url="u-b"),
        ),
    )
    found = backlog.find_duplicates("Export mensuel des candidatures employeurs prescripteurs DDETS GEIQ")
    assert [t["url"] for t in found] == ["u-b"]


def test_dod_3_find_duplicates_compares_word_starts(mocker):
    mocker.patch.object(backlog.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch(
        "lib.notion.notion_request",
        return_value=response(
            page("a", "Afficher le salarié", url="u-a"),
            page("b", "Modifier la fiche du salarié", url="u-b"),
        ),
    )
    found = backlog.find_duplicates("Modifier la fiche salarié")
    assert [t["url"] for t in found] == ["u-b"]


def test_dod_3_find_duplicates_keeps_word_starts_after_a_typographic_apostrophe(mocker):
    mocker.patch.object(backlog.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch(
        "lib.notion.notion_request",
        return_value=response(page("a", "Permettre à l’employeur d’exporter la fiche", url="u-a")),
    )
    found = backlog.find_duplicates("Exporter la fiche employeur")
    assert [t["url"] for t in found] == ["u-a"]


def test_dod_3_find_duplicates_ignores_a_single_keyword_title(mocker):
    mocker.patch("lib.notion.notion_request", side_effect=AssertionError("aucune requête attendue"))
    assert backlog.find_duplicates("Export") == []


@pytest.mark.parametrize(
    ("roles", "author_teams", "targets", "field"),
    [
        (["Responsable d'équipe"], ["e1"], ["e1"], "POM"),
        (["Responsable d'équipe"], ["e1"], ["e2"], "Contributeurs"),
        (["Designer"], ["e1"], ["e2"], "UX"),
        (["Dev"], [], ["e1"], "Développeurs"),
        (["Data analyst"], [], ["e1"], "Développeurs"),
        (["Chargé.e de déploiement"], ["e1"], ["e1"], "Contributeurs"),
        ([], [], ["e1"], "Contributeurs"),
    ],
)
def test_dod_3_author_field(roles, author_teams, targets, field):
    author = backlog.Author(name="x", roles=roles, teams=author_teams, notion_id="u")
    assert backlog.author_field(author, targets) == field


@pytest.mark.parametrize(
    ("records", "accounts", "expected"),
    [
        (True, True, backlog.Author(name="Camille", roles=["Designer"], teams=["e1"], notion_id="u1")),
        (True, False, backlog.Author(name="Fiche Camille", roles=["Designer"], teams=["e1"], notion_id=None)),
        (False, True, backlog.Author(name="Camille", roles=[], teams=[], notion_id="u1")),
        (False, False, None),
    ],
)
def test_dod_3_find_author_from_what_exists(mocker, records, accounts, expected):
    mocker.patch.object(backlog.config, "NOTION_ANNUAIRE_DB", "directory")
    record = {
        "id": "f",
        "properties": {
            "Nom": notion_title("Fiche Camille"),
            "Rôle": {"type": "multi_select", "multi_select": [{"name": "Designer"}]},
            "🍕 Équipes": relation("e1"),
        },
    }
    people = [
        {"id": "u1", "type": "person", "name": "Camille", "person": {"email": "camille@exemple.fr"}},
        {"id": "b1", "type": "bot", "name": "Robot"},
    ]
    mocker.patch(
        "lib.notion.notion_request",
        side_effect=[
            response(record) if records else response(),
            {"results": people if accounts else [], "has_more": False},
        ],
    )
    assert backlog.find_author("Camille@exemple.fr") == expected


def test_notion_user_paginates(mocker):
    call = mocker.patch(
        "lib.notion.notion_request",
        side_effect=[
            {
                "results": [{"id": "u0", "type": "person", "person": {"email": "autre@exemple.fr"}}],
                "has_more": True,
                "next_cursor": "c1",
            },
            {
                "results": [
                    {"id": "u1", "type": "person", "name": "Camille", "person": {"email": "camille@exemple.fr"}}
                ],
                "has_more": False,
            },
        ],
    )
    assert backlog.notion_user("camille@exemple.fr") == ("u1", "Camille")
    assert "start_cursor=c1" in call.call_args_list[1].args[1]
