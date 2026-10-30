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


def test_dod_4_construire_proprietes_ne_pose_que_les_champs_autorises():
    proprietes = creation.construire_proprietes(
        ticket(figma="https://figma", epic="p1", champ_auteur="UX", auteur_notion_id="u1")
    )
    assert set(proprietes) == {"Nom", "Pizza team", "Statut", "Type", "Figma", "Epic - feuille de route", "UX"}
    assert proprietes["UX"] == {"people": [{"id": "u1"}]}
    assert not {"Priorité", "Période", "Estimation"} & set(proprietes)


@pytest.mark.parametrize(
    ("champs", "message"),
    [
        ({"statut": "𝗗𝗘𝗩 En prod"}, "Statut non proposable"),
        ({"statut": "𝗗𝗘𝗩 Ce sprint"}, "Statut non proposable"),
        ({"types": ["Épopée"]}, "Type inconnu"),
        ({"equipes": []}, "Au moins une équipe"),
        ({"champ_auteur": "Responsable(s)", "auteur_notion_id": "u1"}, "Champ d'auteur inconnu"),
    ],
)
def test_dod_4_construire_proprietes_refuse(champs, message):
    with pytest.raises(ValueError, match=message):
        creation.construire_proprietes(ticket(**champs))


def paragraphe(texte):
    return {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": texte}}]}}


def test_dod_4_placer_marqueur_insere_l_emoji():
    blocs = creation.placer_marqueur([paragraphe(":autometa: Les employeurs gardent l'accès.")], "emoji-1")
    textes = blocs[0]["paragraph"]["rich_text"]
    assert textes[0] == {"type": "mention", "mention": {"type": "custom_emoji", "custom_emoji": {"id": "emoji-1"}}}
    assert textes[1]["text"]["content"] == " Les employeurs gardent l'accès."


def test_placer_marqueur_sans_emoji_garde_le_texte():
    blocs = creation.placer_marqueur([paragraphe(":autometa: Texte")], None)
    assert blocs[0]["paragraph"]["rich_text"][0]["text"]["content"] == ":autometa: Texte"


def test_emoji_autometa_parcourt_les_pages(mocker):
    mocker.patch(
        "lib.notion.notion_request",
        side_effect=[
            {"results": [{"id": "x", "name": "autre"}], "has_more": True, "next_cursor": "c"},
            {"results": [{"id": "e", "name": "autometa"}], "has_more": False},
        ],
    )
    assert creation.emoji_autometa() == "e"


def page_notion(base, titre="", archivee=False):
    return {
        "parent": {"database_id": base},
        "archived": archivee,
        "properties": {"Nom": {"type": "title", "title": [{"plain_text": titre}]}},
    }


@pytest.mark.parametrize(
    ("pages", "champs", "message"),
    [
        ({"e1": page_notion("autre-base")}, {}, "pas une page active"),
        ({"e1": page_notion("equipes"), "p1": page_notion("equipes")}, {"epic": "p1"}, "pas une page active"),
        ({"e1": page_notion("equipes", archivee=True)}, {}, "pas une page active"),
        ({"e1": page_notion("equipes", "Prescription")}, {"noms": {"e1": "Emplois"}}, "ne s'appelle pas"),
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
    mocker.patch.object(creation.backlog, "bases_liees", return_value={"equipes": "equi-pes", "epics": "epics"})
    pages = {"e1": page_notion("equipes", "Emplois"), "p1": page_notion("e-pics", "RUN EMPLOIS")}
    appel = mocker.patch(
        "lib.notion.notion_request", side_effect=lambda methode, chemin, charge=None: pages[chemin.split("/")[1]]
    )
    creation.verifier_relations(ticket(epic="p1", noms={"e1": "Emplois", "p1": "RUN EMPLOIS"}))
    assert [c.args[1] for c in appel.call_args_list] == ["pages/e1", "pages/p1"]


def test_dod_4_creer_ticket_envoie_100_blocs_puis_le_reste(mocker):
    mocker.patch.object(creation.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch.object(creation, "emoji_autometa", return_value=None)
    verification = mocker.patch.object(creation, "verifier_relations")
    mocker.patch("lib.notion.markdown_to_blocks", return_value=[paragraphe(str(i)) for i in range(150)])
    appel = mocker.patch("lib.notion.notion_request", side_effect=[{"id": "p", "url": "https://notion/p"}, {}])
    assert creation.creer_ticket(ticket()) == ("p", "https://notion/p")
    creer, ajouter = appel.call_args_list
    assert creer.args[2]["parent"] == {"database_id": "backlog"}
    assert len(creer.args[2]["children"]) == 100
    assert ajouter.args[:2] == ("PATCH", "blocks/p/children")
    verification.assert_called_once()
    assert len(ajouter.args[2]["children"]) == 50
