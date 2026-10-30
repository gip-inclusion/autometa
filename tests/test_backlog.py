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
    payloads = {}
    tickets = {
        "e1": reponse(page("t1", "Modale DORA")),
        "e2": reponse(page("t3", ""), page("t2", "Fiche salarié")),
    }

    def notion(methode, chemin, charge=None):
        if methode == "GET":
            return schema
        base = chemin.split("/")[1]
        payloads[base] = charge
        if base == "backlog":
            return tickets[charge["filter"]["and"][0]["relation"]["contains"]]
        return {
            "equipes": reponse(page("e1", "Prescription "), page("e2", "Emplois")),
            "epics": reponse(page("p1", "DORA - RUN", Pizza_team=["e1"]), page("p2", "RUN EMPLOIS", Pizza_team=["e2"])),
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
    assert payloads["equipes"]["filter"] == {
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
        "## Emplois\n- Épics actifs : RUN EMPLOIS\n- Tickets récents : aucun\n\n"
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
        ("Permettre à l’employeur d'exporter la liste", ["employeur", "exporter", "liste"]),
        ("[DATA] Exporter les candidatures", ["Exporter", "candidatures"]),
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


def test_dod_3_chercher_doublons_compare_les_debuts_de_mots(mocker):
    mocker.patch.object(backlog.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch(
        "lib.notion.notion_request",
        return_value=reponse(
            page("a", "Afficher le salarié", url="u-a"),
            page("b", "Modifier la fiche du salarié", url="u-b"),
        ),
    )
    trouves = backlog.chercher_doublons("Modifier la fiche salarié")
    assert [t["url"] for t in trouves] == ["u-b"]


def test_dod_3_chercher_doublons_garde_les_debuts_de_mots_apres_une_apostrophe_typographique(mocker):
    mocker.patch.object(backlog.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch(
        "lib.notion.notion_request",
        return_value=reponse(page("a", "Permettre à l’employeur d’exporter la fiche", url="u-a")),
    )
    trouves = backlog.chercher_doublons("Exporter la fiche employeur")
    assert [t["url"] for t in trouves] == ["u-a"]


def test_dod_3_chercher_doublons_ignore_un_titre_a_un_seul_mot_cle(mocker):
    mocker.patch("lib.notion.notion_request", side_effect=AssertionError("aucune requête attendue"))
    assert backlog.chercher_doublons("Export") == []


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


@pytest.mark.parametrize(
    ("fiches", "comptes", "attendu"),
    [
        (True, True, backlog.Auteur(nom="Camille", roles=["Designer"], equipes=["e1"], notion_id="u1")),
        (True, False, backlog.Auteur(nom="Fiche Camille", roles=["Designer"], equipes=["e1"], notion_id=None)),
        (False, True, backlog.Auteur(nom="Camille", roles=[], equipes=[], notion_id="u1")),
        (False, False, None),
    ],
)
def test_dod_3_trouver_auteur_selon_ce_qui_existe(mocker, fiches, comptes, attendu):
    mocker.patch.object(backlog.config, "NOTION_ANNUAIRE_DB", "annuaire")
    fiche = {
        "id": "f",
        "properties": {
            "Nom": titre_notion("Fiche Camille"),
            "Rôle": {"type": "multi_select", "multi_select": [{"name": "Designer"}]},
            "🍕 Équipes": relation("e1"),
        },
    }
    personnes = [
        {"id": "u1", "type": "person", "name": "Camille", "person": {"email": "camille@exemple.fr"}},
        {"id": "b1", "type": "bot", "name": "Robot"},
    ]
    mocker.patch(
        "lib.notion.notion_request",
        side_effect=[
            reponse(fiche) if fiches else reponse(),
            {"results": personnes if comptes else [], "has_more": False},
        ],
    )
    assert backlog.trouver_auteur("Camille@exemple.fr") == attendu


def test_utilisateur_notion_pagine(mocker):
    appel = mocker.patch(
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
    assert backlog.utilisateur_notion("camille@exemple.fr") == ("u1", "Camille")
    assert "start_cursor=c1" in appel.call_args_list[1].args[1]
