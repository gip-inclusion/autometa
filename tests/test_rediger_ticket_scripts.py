import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import httpx
import pytest

from lib import backlog
from lib.figma import Cadre

SCRIPTS = Path(__file__).parent.parent / "skills/rediger_ticket/scripts"


def charger(nom):
    spec = importlib.util.spec_from_file_location(f"rediger_ticket_{nom}", SCRIPTS / f"{nom}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTEXTE = {
    "genere_le": "2026-10-30T02:00:00+00:00",
    "equipes": [
        {
            "id": "e1",
            "nom": "Emplois inclusifs et dispositifs réglementés",
            "epics": [{"id": "p1", "nom": "RUN EMPLOIS"}],
            "tickets_recents": [],
        },
    ],
}
AUTEUR = backlog.Auteur(nom="Camille", roles=["Responsable d'équipe"], equipes=["e1"], notion_id="u1")


def brouillon(tmp_path, **champs):
    valeurs = {
        "titre": "Masquer les candidatures anciennes",
        "corps": ":autometa: Texte.",
        "equipes": ["Emplois inclusifs et dispositifs réglementés"],
        "statut": "Cadrage",
        "types": ["Fonctionnalité"],
        "epic": "RUN EMPLOIS",
    }
    valeurs.update(champs)
    chemin = tmp_path / "brouillon.json"
    chemin.write_text(json.dumps(valeurs, ensure_ascii=False))
    return str(chemin)


def preparer_creer(mocker):
    creer = charger("creer")
    mocker.patch.object(creer.backlog_stockage, "contexte_courant", return_value=CONTEXTE)
    mocker.patch.object(creer.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch.object(creer.backlog, "trouver_auteur", return_value=AUTEUR)
    mocker.patch.object(creer.backlog_creation, "verifier_relations")
    creation = mocker.patch.object(creer.backlog_creation, "creer_ticket", return_value=("p", "https://notion/p"))
    return creer, creation


def test_dod_5_creer_sans_go_ne_cree_rien(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    sortie = creer.run(Namespace(brouillon=brouillon(tmp_path), go=False))
    creation.assert_not_called()
    creer.backlog_creation.verifier_relations.assert_called_once()
    assert sortie.startswith("Vérification seulement")
    assert '"POM"' in sortie


def test_dod_5_creer_avec_go_resout_noms_et_auteur(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    assert creer.run(Namespace(brouillon=brouillon(tmp_path), go=True)) == "Ticket créé : https://notion/p"
    ticket = creation.call_args.args[0]
    assert (ticket.equipes, ticket.epic, ticket.champ_auteur, ticket.auteur_notion_id) == (["e1"], "p1", "POM", "u1")
    assert ticket.noms == {"e1": "Emplois inclusifs et dispositifs réglementés", "p1": "RUN EMPLOIS"}


def test_creer_respecte_le_champ_donne_par_l_auteur(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    creer.run(Namespace(brouillon=brouillon(tmp_path, champ_auteur="UX"), go=True))
    assert creation.call_args.args[0].champ_auteur == "UX"


@pytest.mark.parametrize(
    ("champs", "message"),
    [({"equipes": ["Équipe fantôme"]}, "Équipe inconnue"), ({"epic": "Épic fantôme"}, "Épic inconnu")],
)
def test_creer_refuse_un_nom_inconnu(mocker, tmp_path, champs, message):
    creer, _ = preparer_creer(mocker)
    with pytest.raises(ValueError, match=message):
        creer.run(Namespace(brouillon=brouillon(tmp_path, **champs), go=True))


@pytest.mark.parametrize(
    ("url", "debut"),
    [
        ("https://exemple.fr/x", "Ce n'est pas un lien Figma"),
        ("https://www.figma.com/board/AAAAAAAAAAAAAAAAAAAAAA/x", "Lien Figma sans cadre précis"),
    ],
)
def test_dod_1_maquette_ne_lit_pas_un_lien_inexploitable(mocker, url, debut):
    maquette = charger("maquette")
    mocker.patch.object(maquette.config, "FIGMA_ACCESS_TOKEN", "jeton")
    lire = mocker.patch.object(maquette.figma, "lire_cadres")
    assert maquette.run(Namespace(url=url)).startswith(debut)
    lire.assert_not_called()


def test_dod_1_maquette_liste_cadres_textes_et_images(mocker, tmp_path):
    maquette = charger("maquette")
    mocker.patch.object(maquette.config, "FIGMA_ACCESS_TOKEN", "jeton")
    mocker.patch.object(maquette, "dossier_images", return_value=tmp_path)
    mocker.patch.object(
        maquette.figma, "lire_cadres", return_value=[Cadre(id="2:2", nom="Choix 1", textes=["Accepter"], largeur=100)]
    )
    mocker.patch.object(maquette.figma, "exporter_images", return_value={"2:2": tmp_path / "cadre-1.png"})
    sortie = maquette.run(Namespace(url="https://www.figma.com/design/AAAAAAAAAAAAAAAAAAAAAA/x?node-id=1-2"))
    assert "## Cadre 1 : Choix 1" in sortie
    assert f"Image à regarder : {tmp_path / 'cadre-1.png'}" in sortie
    assert "- Accepter" in sortie


LIEN_CADRE = "https://www.figma.com/design/AAAAAAAAAAAAAAAAAAAAAA/x?node-id=1-2"
REQUETE = httpx.Request("GET", "https://api.figma.com")


@pytest.mark.parametrize(
    ("erreur", "attendu"),
    [
        (
            httpx.HTTPStatusError("403", request=REQUETE, response=httpx.Response(403)),
            "Maquette non lue : Figma répond 403 (accès refusé ou fichier introuvable).",
        ),
        (
            httpx.HTTPStatusError("429", request=REQUETE, response=httpx.Response(429)),
            "Maquette non lue : Figma limite les appels (429), réessayer dans une minute.",
        ),
        (httpx.ConnectTimeout("lent", request=REQUETE), "Maquette non lue : Figma ne répond pas."),
    ],
)
def test_dod_1_maquette_dit_pourquoi_elle_n_est_pas_lue(mocker, erreur, attendu):
    maquette = charger("maquette")
    mocker.patch.object(maquette.config, "FIGMA_ACCESS_TOKEN", "jeton")
    mocker.patch.object(maquette.figma, "lire_cadres", side_effect=erreur)
    assert maquette.run(Namespace(url=LIEN_CADRE)) == attendu


def test_dod_1_maquette_signale_un_cadre_introuvable(mocker):
    maquette = charger("maquette")
    mocker.patch.object(maquette.config, "FIGMA_ACCESS_TOKEN", "jeton")
    mocker.patch.object(maquette.figma, "lire_cadres", return_value=[])
    assert maquette.run(Namespace(url=LIEN_CADRE)).startswith("Cadre introuvable dans ce fichier Figma")


def test_dod_1_maquette_garde_les_textes_si_les_images_echouent(mocker):
    maquette = charger("maquette")
    mocker.patch.object(maquette.config, "FIGMA_ACCESS_TOKEN", "jeton")
    mocker.patch.object(
        maquette.figma, "lire_cadres", return_value=[Cadre(id="2:2", nom="Choix 1", textes=["Accepter"], largeur=100)]
    )
    mocker.patch.object(maquette.figma, "exporter_images", side_effect=httpx.ReadTimeout("lent", request=REQUETE))
    sortie = maquette.run(Namespace(url=LIEN_CADRE))
    assert "Images non rendues (Maquette non lue : Figma ne répond pas.) : se fier aux textes." in sortie
    assert "- Accepter" in sortie
    assert "Image à regarder" not in sortie


def test_auteur_sans_session_le_dit(mocker):
    auteur = charger("auteur")
    mocker.patch.object(auteur.config, "agent_user_email", return_value=None)
    assert auteur.run(Namespace(equipe=[])) == "Personne connectée inconnue : l'auteur ne sera pas inscrit."


def test_dod_3_auteur_donne_le_champ_pour_l_equipe_visee(mocker):
    auteur = charger("auteur")
    mocker.patch.object(auteur.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch.object(auteur.backlog, "trouver_auteur", return_value=AUTEUR)
    mocker.patch.object(auteur.backlog_stockage, "contexte_courant", return_value=CONTEXTE)
    sortie = auteur.run(Namespace(equipe=["Emplois inclusifs et dispositifs réglementés"]))
    assert "Rôles : Responsable d'équipe" in sortie
    assert "Inscrit dans : POM" in sortie


def test_contexte_rafraichi_relit_notion_et_range(mocker):
    script = charger("contexte")
    mocker.patch.object(script.backlog, "charger_contexte", return_value=CONTEXTE)
    ranger = mocker.patch.object(script.backlog_stockage, "enregistrer_contexte")
    sortie = script.run(Namespace(rafraichir=True))
    ranger.assert_called_once_with(CONTEXTE)
    assert "## Emplois inclusifs et dispositifs réglementés" in sortie


def test_dod_3_doublons_liste_les_tickets_proches(mocker):
    doublons = charger("doublons")
    mocker.patch.object(
        doublons.backlog,
        "chercher_doublons",
        return_value=[{"titre": "T", "url": "u", "statut": "Cadrage", "communs": 3}],
    )
    assert doublons.run(Namespace(titre="Masquer les candidatures")) == "- T (Cadrage, 3 mots communs) u"
