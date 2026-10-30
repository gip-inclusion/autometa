import pytest

from lib import backlog


def titre_notion(texte):
    return {"type": "title", "title": [{"plain_text": texte}]}


def relation(*ids):
    return {"type": "relation", "relation": [{"id": i} for i in ids]}


def page(id_, titre, statut=None, url="", **relations):
    proprietes = {"Nom": titre_notion(titre)}
    if statut:
        proprietes["Statut"] = {"type": "select", "select": {"name": statut}}
    for nom, ids in relations.items():
        proprietes[nom.replace("_", " ")] = relation(*ids)
    return {"id": id_, "url": url, "properties": proprietes}


def reponse(*pages, suite=None):
    return {"results": list(pages), "has_more": suite is not None, "next_cursor": suite}


def test_requeter_pagine_et_s_arrete_a_la_limite(mocker):
    appel = mocker.patch(
        "lib.notion.notion_request",
        side_effect=[reponse(page("a", "A"), page("b", "B"), suite="c1"), reponse(page("c", "C"), suite="c2")],
    )
    lignes = backlog.requeter("base", {"property": "x"}, limite=3)
    assert [p["id"] for p in lignes] == ["a", "b", "c"]
    assert appel.call_args_list[1].args[2]["start_cursor"] == "c1"
    assert appel.call_count == 2


def test_dod_2_charger_contexte_regroupe_epics_et_titres_par_equipe(mocker):
    mocker.patch.object(backlog.config, "NOTION_BACKLOG_DB", "backlog")
    schema = {
        "properties": {
            "Pizza team": {"relation": {"database_id": "equipes"}},
            "Epic - feuille de route": {"relation": {"database_id": "epics"}},
        }
    }

    def notion(methode, chemin, charge=None):
        if methode == "GET":
            return schema
        base = chemin.split("/")[1]
        return {
            "equipes": reponse(page("e1", "Prescription "), page("e2", "Emplois")),
            "epics": reponse(page("p1", "DORA - RUN", Pizza_team=["e1"]), page("p2", "RUN EMPLOIS", Pizza_team=["e2"])),
            "backlog": reponse(
                page("t1", "Modale DORA", Pizza_team=["e1"]),
                page("t2", "Fiche salarié", Pizza_team=["e2"]),
                page("t3", "", Pizza_team=["e2"]),
            ),
        }[base]

    mocker.patch("lib.notion.notion_request", side_effect=notion)
    contexte = backlog.charger_contexte()
    assert contexte["equipes"] == [
        {
            "id": "e1",
            "nom": "Prescription",
            "epics": [{"id": "p1", "nom": "DORA - RUN"}],
            "tickets_recents": ["Modale DORA"],
        },
        {
            "id": "e2",
            "nom": "Emplois",
            "epics": [{"id": "p2", "nom": "RUN EMPLOIS"}],
            "tickets_recents": ["Fiche salarié"],
        },
    ]


def test_formater_contexte_trie_les_equipes_et_liste_epics_et_tickets():
    contexte = {
        "genere_le": "2026-10-30T02:00:00+00:00",
        "equipes": [
            {"id": "e2", "nom": "Prescription", "epics": [], "tickets_recents": ["Modale DORA"]},
            {"id": "e1", "nom": "Emplois", "epics": [{"id": "p", "nom": "RUN EMPLOIS"}], "tickets_recents": []},
        ],
    }
    assert backlog.formater_contexte(contexte) == (
        "# Équipes produit actives (au 2026-10-30)\n\n"
        "## Emplois\n- Épics actifs : RUN EMPLOIS\n- Tickets récents :\n\n"
        "## Prescription\n- Tickets récents :\n  - Modale DORA\n"
    )


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        (
            "Masquer aux employeurs les candidatures non acceptées",
            ["Masquer", "employeurs", "candidatures", "acceptées"],
        ),
        ("Afficher une modale pour les prescripteurs", ["modale", "prescripteurs"]),
        ("le la de", []),
    ],
)
def test_mots_cles(texte, attendu):
    assert backlog.mots_cles(texte) == attendu


def test_dod_3_chercher_doublons_classe_et_ecarte_les_rapprochements_faibles(mocker):
    mocker.patch.object(backlog.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch(
        "lib.notion.notion_request",
        return_value=reponse(
            page("a", "Masquer les candidatures des employeurs", statut="Cadrage", url="u-a"),
            page("b", "Candidatures : export CSV", statut="Métier", url="u-b"),
            page("c", "Masquer candidatures employeurs non acceptées", statut="Bac à sable 🏝️", url="u-c"),
        ),
    )
    trouves = backlog.chercher_doublons("Masquer aux employeurs les candidatures non acceptées")
    assert [t["url"] for t in trouves] == ["u-c", "u-a"]
    assert trouves[0] == {
        "titre": "Masquer candidatures employeurs non acceptées",
        "url": "u-c",
        "statut": "Bac à sable 🏝️",
        "communs": 4,
    }


def test_dod_3_chercher_doublons_exige_la_moitie_des_mots_cles(mocker):
    mocker.patch.object(backlog.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch(
        "lib.notion.notion_request",
        return_value=reponse(
            page("a", "Export des candidatures employeurs", url="u-a"),
            page("b", "Export candidatures employeurs prescripteurs DDETS", url="u-b"),
        ),
    )
    trouves = backlog.chercher_doublons("Export mensuel des candidatures employeurs prescripteurs DDETS GEIQ")
    assert [t["url"] for t in trouves] == ["u-b"]


def test_dod_3_trouver_auteur_croise_annuaire_et_comptes_notion(mocker):
    mocker.patch.object(backlog.config, "NOTION_ANNUAIRE_DB", "annuaire")
    fiche = {
        "id": "f",
        "properties": {
            "Nom": titre_notion("Camille"),
            "Rôle": {"type": "multi_select", "multi_select": [{"name": "Designer"}]},
            "🍕 Équipes": relation("e1"),
        },
    }
    comptes = {
        "results": [
            {"id": "u1", "type": "person", "name": "Camille", "person": {"email": "camille@exemple.fr"}},
            {"id": "b1", "type": "bot", "name": "Robot"},
        ],
        "has_more": False,
    }
    mocker.patch("lib.notion.notion_request", side_effect=[reponse(fiche), comptes])
    assert backlog.trouver_auteur("Camille@exemple.fr") == backlog.Auteur(
        nom="Camille", roles=["Designer"], equipes=["e1"], notion_id="u1"
    )


@pytest.mark.parametrize(
    ("roles", "equipes_auteur", "destinataires", "champ"),
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
def test_dod_3_champ_auteur(roles, equipes_auteur, destinataires, champ):
    auteur = backlog.Auteur(nom="x", roles=roles, equipes=equipes_auteur, notion_id="u")
    assert backlog.champ_auteur(auteur, destinataires) == champ
