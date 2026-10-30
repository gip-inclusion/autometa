import pytest

from lib import backlog_creation as creation


def ticket(**champs):
    valeurs = {
        "titre": "Masquer les candidatures anciennes",
        "corps": ":autometa: Les employeurs gardent l'accès.",
        "equipes": ["e1"],
        "statut": "Cadrage",
        "types": ["Fonctionnalité"],
    }
    valeurs.update(champs)
    return creation.Ticket(**valeurs)


FIGMA = "https://www.figma.com/design/AbCdEfGhIjKlMnOpQrStUv/Maquette"


def test_dod_4_construire_proprietes_ne_pose_que_les_champs_autorises():
    proprietes = creation.construire_proprietes(
        ticket(figma=FIGMA, epic="p1", champ_auteur="UX", auteur_notion_id="u1")
    )
    assert proprietes == {
        "Nom": {"title": [{"text": {"content": "Masquer les candidatures anciennes"}}]},
        "Pizza team": {"relation": [{"id": "e1"}]},
        "Statut": {"select": {"name": "Cadrage"}},
        "Type": {"multi_select": [{"name": "Fonctionnalité"}]},
        "Figma": {"url": FIGMA},
        "Epic - feuille de route": {"relation": [{"id": "p1"}]},
        "UX": {"people": [{"id": "u1"}]},
    }


@pytest.mark.parametrize(
    ("champs", "message"),
    [
        ({"statut": "𝗗𝗘𝗩 En prod"}, "Statut non proposable : .* Valeurs : Bac à sable.*Prêt à développer"),
        ({"statut": "𝗗𝗘𝗩 Ce sprint"}, "Statut non proposable"),
        ({"types": ["Épopée"]}, "Type inconnu"),
        ({"types": []}, "Type inconnu"),
        ({"equipes": []}, "Au moins une équipe"),
        ({"champ_auteur": "Responsable(s)", "auteur_notion_id": "u1"}, "Champ d'auteur inconnu"),
    ],
)
def test_dod_4_construire_proprietes_refuse(champs, message):
    with pytest.raises(ValueError, match=message):
        creation.construire_proprietes(ticket(**champs))


def paragraphe(texte):
    return {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": texte}}]}}


def notion_blocs(markdown):
    return creation.notion.markdown_to_blocks(markdown)


MENTION = {"type": "mention", "mention": {"type": "custom_emoji", "custom_emoji": {"id": "emoji-1"}}}


def test_dod_4_placer_marqueur_insere_l_emoji():
    blocs = creation.placer_marqueur([paragraphe(":autometa: Les employeurs gardent l'accès.")], "emoji-1")
    textes = blocs[0]["paragraph"]["rich_text"]
    assert textes[0] == MENTION
    assert textes[1]["text"]["content"] == " "
    assert textes[2]["text"]["content"] == "Les employeurs gardent l'accès."


def test_placer_marqueur_sans_emoji_garde_le_texte_une_seule_fois():
    blocs = creation.placer_marqueur([paragraphe(":autometa: Texte")], None)
    assert [t["text"]["content"] for t in blocs[0]["paragraph"]["rich_text"]] == [":autometa:", " ", "Texte"]


def test_placer_marqueur_ajoute_le_marqueur_absent():
    blocs = creation.placer_marqueur([paragraphe("Texte")], "emoji-1")
    assert blocs[0]["paragraph"]["rich_text"][0] == MENTION
    assert [t["text"]["content"] for t in blocs[0]["paragraph"]["rich_text"][1:]] == [" ", "Texte"]


def test_placer_marqueur_vise_le_premier_paragraphe_apres_un_titre():
    titre = {"type": "heading_2", "heading_2": {"rich_text": []}}
    blocs = creation.placer_marqueur([titre, paragraphe("Texte")], "emoji-1")
    assert blocs[0] == titre
    assert blocs[1]["paragraph"]["rich_text"][0] == MENTION


def test_placer_marqueur_cree_un_paragraphe_si_le_corps_n_en_a_pas():
    titre = {"type": "heading_2", "heading_2": {"rich_text": []}}
    blocs = creation.placer_marqueur([titre], "emoji-1")
    assert blocs[0]["paragraph"]["rich_text"] == [MENTION]
    assert blocs[1] == titre


def test_placer_marqueur_ne_touche_pas_un_paragraphe_plus_loin():
    blocs = creation.placer_marqueur(
        notion_blocs("## Périmètre\n- x\n\n**Version A**"),
        "emoji-1",
    )
    assert blocs[0]["paragraph"]["rich_text"] == [MENTION]
    assert blocs[-1]["paragraph"]["rich_text"][0]["text"]["content"] == "Version A"
    assert len(blocs[-1]["paragraph"]["rich_text"]) == 1


def test_dod_4_verifier_corps_refuse_un_titre_dans_le_corps():
    with pytest.raises(ValueError, match="le titre ne va pas dans le corps"):
        creation.verifier_corps(ticket(corps="\n# Un titre\n\nTexte"))


def test_emoji_autometa_filtre_par_nom(mocker):
    appel = mocker.patch("lib.notion.notion_request", return_value={"results": [{"id": "e", "name": "autometa"}]})
    assert creation.emoji_autometa() == "e"
    assert "name=autometa" in appel.call_args.args[1]


def test_emoji_autometa_ignore_un_autre_nom_en_tete(mocker):
    resultats = [{"id": "x", "name": "autometa-beta"}, {"id": "e", "name": "autometa"}]
    mocker.patch("lib.notion.notion_request", return_value={"results": resultats})
    assert creation.emoji_autometa() == "e"


def test_emoji_autometa_absent(mocker):
    mocker.patch("lib.notion.notion_request", return_value={"results": []})
    assert creation.emoji_autometa() is None


def page_notion(base, titre="", archivee=False, corbeille=False, equipes=()):
    return {
        "parent": {"database_id": base},
        "archived": archivee,
        "in_trash": corbeille,
        "properties": {
            "Nom": {"type": "title", "title": [{"plain_text": titre}]},
            "Pizza team": {"relation": [{"id": e} for e in equipes]},
        },
    }


@pytest.mark.parametrize(
    ("pages", "champs", "message"),
    [
        ({"e1": page_notion("autre-base", "Emplois")}, {"noms": {"e1": "Emplois"}}, "pas une page active"),
        (
            {"e1": page_notion("equipes", "Emplois"), "p1": page_notion("equipes", "RUN")},
            {"epic": "p1", "noms": {"e1": "Emplois", "p1": "RUN"}},
            "pas une page active",
        ),
        ({"e1": page_notion("equipes", "Emplois", archivee=True)}, {"noms": {"e1": "Emplois"}}, "pas une page active"),
        ({"e1": page_notion("equipes", "Emplois", corbeille=True)}, {"noms": {"e1": "Emplois"}}, "pas une page active"),
        ({"e1": page_notion("equipes", "Prescription")}, {"noms": {"e1": "Emplois"}}, "ne s'appelle pas"),
        ({"e1": page_notion("equipes", "Emplois")}, {}, "nom non fourni"),
        (
            {"e1": page_notion("equipes", "Emplois"), "p1": page_notion("epics", "RUN", equipes=("autre",))},
            {"epic": "p1", "noms": {"e1": "Emplois", "p1": "RUN"}},
            "aucune des équipes",
        ),
    ],
)
def test_dod_4_verifier_relations_refuse(mocker, pages, champs, message):
    mocker.patch.object(creation.backlog, "bases_liees", return_value={"equipes": "equi-pes", "epics": "epics"})
    mocker.patch(
        "lib.notion.notion_request", side_effect=lambda methode, chemin, charge=None: pages[chemin.split("/")[1]]
    )
    with pytest.raises(ValueError, match=message):
        creation.verifier_relations(ticket(**champs))


def test_dod_4_verifier_relations_accepte_les_pages_attendues(mocker):
    mocker.patch.object(creation.backlog, "bases_liees", return_value={"equipes": "equi-pes", "epics": "e-pics"})
    pages = {"e1": page_notion("equipes", "Emplois"), "p1": page_notion("e-pics", "RUN EMPLOIS", equipes=("e1",))}
    appel = mocker.patch(
        "lib.notion.notion_request", side_effect=lambda methode, chemin, charge=None: pages[chemin.split("/")[1]]
    )
    creation.verifier_relations(ticket(epic="p1", noms={"e1": "Emplois", "p1": "RUN EMPLOIS"}))
    assert [c.args[1] for c in appel.call_args_list] == ["pages/e1", "pages/p1"]


@pytest.mark.parametrize(
    ("champs", "message"),
    [
        ({"corps": "x" * 2000}, "2000 caractères ou plus"),
        ({"corps": "a" * 1500 + "\n" + "b" * 1500}, "2000 caractères ou plus"),
        ({"corps": "```\n" + "\n".join("c" * 50 for _ in range(60)) + "\n```"}, "2000 caractères ou plus"),
        ({"corps": "\n".join(f"- point {i}" for i in range(101))}, "Ticket trop long"),
        ({"corps": "voir [lien](javascript:alert)"}, "Lien refusé"),
        ({"corps": "voir [lien](/relatif)"}, "Lien refusé"),
        ({"corps": "voir [x](javascript:x y)"}, "Lien refusé"),
        ({"corps": "voir [x]( javascript:x)"}, "Lien refusé"),
        ({"figma": "https://exemple.fr/design"}, "lien Figma"),
        ({"figma": "https://evil.example/?u=figma.com/design/AbCdEfGhIjKlMnOpQrStUv"}, "lien Figma"),
    ],
)
def test_dod_4_verifier_corps_refuse_avant_toute_requete(mocker, champs, message):
    appel = mocker.patch("lib.notion.notion_request")
    with pytest.raises(ValueError, match=message):
        creation.creer_ticket(ticket(**champs))
    appel.assert_not_called()


def test_dod_4_verifier_corps_accepte_liens_http_et_lignes_courtes():
    assert (
        creation.verifier_corps(
            ticket(corps="voir [a](https://x.fr/a) et [b](http://x.fr)\n\n" + "y" * 1999, figma=FIGMA)
        )
        is None
    )


def test_dod_4_creer_ticket_refuse_un_corps_de_plus_de_100_blocs(mocker):
    mocker.patch.object(creation, "verifier_relations")
    mocker.patch.object(creation, "emoji_autometa", return_value=None)
    mocker.patch("lib.notion.query_database", return_value=[])
    mocker.patch("lib.notion.markdown_to_blocks", return_value=[paragraphe(str(i)) for i in range(101)])
    appel = mocker.patch("lib.notion.notion_request")
    with pytest.raises(ValueError, match="Ticket trop long"):
        creation.creer_ticket(ticket())
    appel.assert_not_called()


def test_dod_4_creer_ticket_envoie_une_seule_creation(mocker):
    mocker.patch.object(creation.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch.object(creation, "emoji_autometa", return_value=None)
    verification = mocker.patch.object(creation, "verifier_relations")
    mocker.patch("lib.notion.query_database", return_value=[])
    mocker.patch("lib.notion.markdown_to_blocks", return_value=[paragraphe(str(i)) for i in range(3)])
    appel = mocker.patch("lib.notion.notion_request", return_value={"id": "p", "url": "https://notion/p"})
    assert creation.creer_ticket(ticket()) == ("p", "https://notion/p")
    appel.assert_called_once()
    assert appel.call_args.args[:2] == ("POST", "pages")
    assert appel.call_args.args[2]["parent"] == {"database_id": "backlog"}
    assert len(appel.call_args.args[2]["children"]) == 3
    verification.assert_called_once()


def test_dod_4_creer_ticket_n_ecrit_rien_si_la_verification_echoue(mocker):
    mocker.patch.object(creation, "verifier_relations", side_effect=ValueError("Relation refusée"))
    appel = mocker.patch("lib.notion.notion_request")
    with pytest.raises(ValueError, match="Relation refusée"):
        creation.creer_ticket(ticket())
    appel.assert_not_called()


def test_preparer_renvoie_le_payload_reel_avec_le_marqueur_sans_ecrire(mocker):
    mocker.patch.object(creation.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch.object(creation, "emoji_autometa", return_value="emoji-1")
    mocker.patch.object(creation, "verifier_relations")
    mocker.patch("lib.notion.query_database", return_value=[])
    appel = mocker.patch("lib.notion.notion_request")
    charge = creation.preparer(ticket(corps="Texte."))
    appel.assert_not_called()
    assert charge["parent"] == {"database_id": "backlog"}
    assert charge["properties"]["Nom"]["title"][0]["text"]["content"] == "Masquer les candidatures anciennes"
    assert charge["children"][0]["paragraph"]["rich_text"][0] == MENTION


def test_preparer_refuse_un_corps_de_plus_de_100_blocs(mocker):
    mocker.patch.object(creation, "verifier_relations")
    mocker.patch.object(creation, "emoji_autometa", return_value=None)
    mocker.patch("lib.notion.query_database", return_value=[])
    mocker.patch("lib.notion.markdown_to_blocks", return_value=[paragraphe(str(i)) for i in range(101)])
    with pytest.raises(ValueError, match="Ticket trop long"):
        creation.preparer(ticket())


def test_preparer_refuse_un_ticket_recent_au_meme_titre(mocker):
    mocker.patch.object(creation.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch.object(creation, "emoji_autometa", return_value=None)
    mocker.patch.object(creation, "verifier_relations")
    requete = mocker.patch("lib.notion.query_database", return_value=[{"url": "https://notion/deja"}])
    appel = mocker.patch("lib.notion.notion_request")
    with pytest.raises(ValueError, match="vient d'être créé : https://notion/deja"):
        creation.preparer(ticket())
    appel.assert_not_called()
    assert requete.call_args.args[0] == "backlog"
    filtre = requete.call_args.kwargs["filter"]["and"]
    assert {"property": "Nom", "title": {"equals": "Masquer les candidatures anciennes"}} in filtre
    assert {"property": "Statut", "select": {"does_not_equal": "Annulé"}} in filtre
    recent = next(f for f in filtre if f.get("timestamp") == "created_time")
    assert len(recent["created_time"]["on_or_after"]) == len("2026-10-30T10:00:00+00:00")
