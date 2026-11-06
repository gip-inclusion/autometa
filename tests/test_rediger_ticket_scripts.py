import argparse
import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import httpx
import pytest

from lib import backlog
from lib.figma import Cadre
from skills.rediger_ticket.scripts import commun

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
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(creer.backlog_stockage, "contexte_courant", return_value=CONTEXTE)
    mocker.patch.object(creer.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch.object(creer.backlog, "trouver_auteur", return_value=AUTEUR)
    mocker.patch.object(creer.backlog_creation, "verifier_relations")
    mocker.patch.object(creer.backlog_creation, "emoji_autometa", return_value="emoji-1")
    mocker.patch("lib.notion.query_database", return_value=[])
    creation = mocker.patch.object(creer.backlog_creation, "creer_ticket", return_value=("p", "https://notion/p"))
    return creer, creation


def test_dod_5_creer_sans_go_ne_cree_rien(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    sortie = creer.run(Namespace(brouillon=brouillon(tmp_path), go=False))
    creation.assert_not_called()
    creer.backlog_creation.verifier_relations.assert_called_once()
    assert sortie.startswith("Vérification seulement")
    assert '"POM"' in sortie
    assert "Corps : 1 blocs" in sortie
    assert "Texte." in sortie


def test_dod_5_creer_sans_go_passe_par_preparer(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    preparer = mocker.spy(creer.backlog_creation, "preparer")
    creer.run(Namespace(brouillon=brouillon(tmp_path), go=False))
    preparer.assert_called_once()
    creation.assert_not_called()


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
    creer, creation = preparer_creer(mocker)
    with pytest.raises(ValueError, match=message):
        creer.run(Namespace(brouillon=brouillon(tmp_path, **champs), go=True))
    creation.assert_not_called()


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
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(commun.config, "NOTION_ANNUAIRE_DB", "annuaire")
    mocker.patch.object(auteur.config, "agent_user_email", return_value=None)
    assert auteur.run(Namespace(equipe=[])) == "Personne connectée inconnue : l'auteur ne sera pas inscrit."


def test_dod_3_auteur_donne_le_champ_pour_l_equipe_visee(mocker):
    auteur = charger("auteur")
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(commun.config, "NOTION_ANNUAIRE_DB", "annuaire")
    mocker.patch.object(auteur.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch.object(auteur.backlog, "trouver_auteur", return_value=AUTEUR)
    mocker.patch.object(auteur.backlog_stockage, "contexte_courant", return_value=CONTEXTE)
    sortie = auteur.run(Namespace(equipe=["Emplois inclusifs et dispositifs réglementés"]))
    assert "Rôles : Responsable d'équipe" in sortie
    assert "Inscrit dans : POM" in sortie


def test_contexte_rafraichi_relit_notion_et_range(mocker):
    script = charger("contexte")
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(script.backlog, "charger_contexte", return_value=CONTEXTE)
    ranger = mocker.patch.object(script.backlog_stockage, "enregistrer_contexte")
    sortie = script.run(Namespace(rafraichir=True))
    ranger.assert_called_once_with(CONTEXTE)
    assert "## Emplois inclusifs et dispositifs réglementés" in sortie


def test_dod_3_doublons_liste_les_tickets_proches(mocker):
    doublons = charger("doublons")
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(
        doublons.backlog,
        "chercher_doublons",
        return_value=[{"titre": "T", "url": "u", "statut": "Cadrage", "communs": 3}],
    )
    assert doublons.run(Namespace(titre="Masquer les candidatures")) == "- T (Cadrage, 3 mots communs) u"


def lancer(mocker, script, *arguments):
    mocker.patch("sys.argv", [f"{script.__name__}.py", *arguments])
    script.main()


def test_creer_sans_argument_lit_le_brouillon_de_la_conversation_et_le_consomme(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    chemin = tmp_path / "brouillon.json"
    chemin.write_text(Path(brouillon(tmp_path)).read_text())
    mocker.patch.object(creer, "chemin_brouillon", return_value=chemin)
    assert creer.run(Namespace(brouillon=None, go=True)).startswith("Ticket créé")
    assert not chemin.exists()
    creation.assert_called_once()


def test_creer_chemin_par_defaut_depend_de_la_conversation(mocker):
    creer = charger("creer")
    mocker.patch.object(creer.config, "agent_conversation_id", return_value="conv-1")
    assert creer.chemin_brouillon() == Path("/tmp/rediger_ticket/conv-1/brouillon.json")


def test_creer_apres_creation_le_brouillon_est_supprime(mocker, tmp_path):
    creer, _ = preparer_creer(mocker)
    chemin = brouillon(tmp_path)
    creer.run(Namespace(brouillon=chemin, go=True))
    assert not Path(chemin).exists()


@pytest.mark.parametrize("champ", ["titre", "corps", "equipes", "statut", "types"])
def test_creer_refuse_un_brouillon_sans_champ_obligatoire(mocker, tmp_path, champ):
    creer, creation = preparer_creer(mocker)
    with pytest.raises(ValueError, match=champ):
        creer.run(Namespace(brouillon=brouillon(tmp_path, **{champ: None}), go=True))
    creation.assert_not_called()


def test_creer_refuse_des_equipes_qui_ne_sont_pas_une_liste(mocker, tmp_path):
    creer, _ = preparer_creer(mocker)
    with pytest.raises(ValueError, match="doit être une liste"):
        creer.run(Namespace(brouillon=brouillon(tmp_path, equipes="Emplois"), go=True))


def test_creer_sans_base_backlog_refuse(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", None)
    with pytest.raises(ValueError, match="NOTION_BACKLOG_DB absent"):
        creer.run(Namespace(brouillon=brouillon(tmp_path), go=True))
    creation.assert_not_called()


def test_creer_continue_sans_auteur_si_l_annuaire_est_illisible(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    mocker.patch.object(creer.backlog, "trouver_auteur", side_effect=httpx.ReadTimeout("lent", request=REQUETE))
    sortie = creer.run(Namespace(brouillon=brouillon(tmp_path), go=True))
    assert "Ticket créé : https://notion/p" in sortie
    assert "Auteur non inscrit : annuaire ou comptes Notion illisibles." in sortie
    assert creation.call_args.args[0].champ_auteur is None


def test_creer_sans_auteur_connu_cree_quand_meme(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    mocker.patch.object(creer.backlog, "trouver_auteur", return_value=None)
    creer.run(Namespace(brouillon=brouillon(tmp_path), go=True))
    assert creation.call_args.args[0].auteur_notion_id is None


def test_dod_5_creer_a_blanc_montre_les_noms_resolus(mocker, tmp_path):
    creer, _ = preparer_creer(mocker)
    sortie = creer.run(Namespace(brouillon=brouillon(tmp_path), go=False))
    assert '"p1": "RUN EMPLOIS"' in sortie


def test_dod_5_creer_en_ligne_de_commande_sans_go_ne_cree_rien(mocker, tmp_path, capsys):
    creer, creation = preparer_creer(mocker)
    lancer(mocker, creer, brouillon(tmp_path))
    creation.assert_not_called()
    assert capsys.readouterr().out.startswith("Vérification seulement")


@pytest.mark.parametrize(
    ("erreur", "message"),
    [
        (
            httpx.HTTPStatusError("404", request=REQUETE, response=httpx.Response(404, text="object_not_found")),
            "Notion répond 404 : object_not_found",
        ),
        (httpx.ConnectTimeout("lent", request=REQUETE), "Notion ne répond pas : vérifier dans Notion"),
    ],
)
def test_creer_en_ligne_de_commande_dit_l_erreur_notion(mocker, tmp_path, erreur, message):
    creer, creation = preparer_creer(mocker)
    creation.side_effect = erreur
    chemin = brouillon(tmp_path)
    with pytest.raises(SystemExit, match=message):
        lancer(mocker, creer, chemin, "--go")
    assert Path(chemin).exists()


def test_creer_en_ligne_de_commande_refuse_un_fichier_absent(mocker, tmp_path):
    creer, _ = preparer_creer(mocker)
    with pytest.raises(SystemExit, match="Refusé, rien n'est créé"):
        lancer(mocker, creer, str(tmp_path / "absent.json"))


def test_creer_en_ligne_de_commande_refuse_un_json_invalide(mocker, tmp_path):
    creer, _ = preparer_creer(mocker)
    mauvais = tmp_path / "mauvais.json"
    mauvais.write_text("{pas du json")
    with pytest.raises(SystemExit, match="Refusé, rien n'est créé"):
        lancer(mocker, creer, str(mauvais))


def test_creer_en_ligne_de_commande_refuse_une_equipe_inconnue(mocker, tmp_path):
    creer, _ = preparer_creer(mocker)
    with pytest.raises(SystemExit, match="Équipe inconnue"):
        lancer(mocker, creer, brouillon(tmp_path, equipes=["Équipe fantôme"]))


@pytest.mark.parametrize("nom", ["contexte", "doublons", "auteur"])
def test_scripts_de_lecture_sans_base_backlog_le_disent(mocker, nom):
    script = charger(nom)
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", None)
    sortie = script.run(Namespace(rafraichir=False, titre="x", equipe=[]))
    assert sortie.startswith("NOTION_BACKLOG_DB absent")


def test_doublons_sans_resultat(mocker):
    doublons = charger("doublons")
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(doublons.backlog, "chercher_doublons", return_value=[])
    assert doublons.run(Namespace(titre="x")) == "Aucun ticket proche."


def test_contexte_sans_rafraichir_lit_le_contexte_stocke(mocker):
    script = charger("contexte")
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(script.backlog_stockage, "contexte_courant", return_value=CONTEXTE)
    charge = mocker.patch.object(script.backlog, "charger_contexte")
    assert "## Emplois inclusifs et dispositifs réglementés" in script.run(Namespace(rafraichir=False))
    charge.assert_not_called()


def test_auteur_introuvable_le_dit(mocker):
    auteur = charger("auteur")
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(commun.config, "NOTION_ANNUAIRE_DB", "annuaire")
    mocker.patch.object(auteur.config, "agent_user_email", return_value="x@exemple.fr")
    mocker.patch.object(auteur.backlog, "trouver_auteur", return_value=None)
    assert auteur.run(Namespace(equipe=[])).startswith("Absent de l'Annuaire")


def test_auteur_signale_une_equipe_inconnue(mocker):
    auteur = charger("auteur")
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(commun.config, "NOTION_ANNUAIRE_DB", "annuaire")
    mocker.patch.object(auteur.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch.object(auteur.backlog, "trouver_auteur", return_value=AUTEUR)
    mocker.patch.object(auteur.backlog_stockage, "contexte_courant", return_value=CONTEXTE)
    champ = mocker.patch.object(auteur.backlog, "champ_auteur", return_value="POM")
    sortie = auteur.run(Namespace(equipe=["Équipe fantôme", "Emplois inclusifs et dispositifs réglementés"]))
    assert "Équipe inconnue : Équipe fantôme (nom exact : voir contexte.py)" in sortie
    champ.assert_called_once_with(AUTEUR, ["e1"])


def test_dod_1_maquette_sans_jeton_figma_le_dit(mocker):
    maquette = charger("maquette")
    mocker.patch.object(maquette.config, "FIGMA_ACCESS_TOKEN", None)
    lire = mocker.patch.object(maquette.figma, "lire_cadres")
    assert maquette.run(Namespace(url=LIEN_CADRE)).startswith("FIGMA_ACCESS_TOKEN absent")
    lire.assert_not_called()


def test_dod_1_maquette_ne_promet_pas_un_acces_refuse_pour_un_500(mocker):
    maquette = charger("maquette")
    mocker.patch.object(maquette.config, "FIGMA_ACCESS_TOKEN", "jeton")
    erreur = httpx.HTTPStatusError("500", request=REQUETE, response=httpx.Response(500))
    mocker.patch.object(maquette.figma, "lire_cadres", side_effect=erreur)
    assert maquette.run(Namespace(url=LIEN_CADRE)) == "Maquette non lue : Figma répond 500."


def test_dod_1_maquette_signale_cadre_sans_texte_et_sans_image(mocker, tmp_path):
    maquette = charger("maquette")
    mocker.patch.object(maquette.config, "FIGMA_ACCESS_TOKEN", "jeton")
    mocker.patch.object(maquette, "dossier_images", return_value=tmp_path)
    cadres = [
        Cadre(id="2:2", nom="Vide", textes=[], largeur=100),
        Cadre(id="2:3", nom="Autre", textes=["Ok"], largeur=100),
    ]
    mocker.patch.object(maquette.figma, "lire_cadres", return_value=cadres)
    mocker.patch.object(maquette.figma, "exporter_images", return_value={"2:3": tmp_path / "c.png"})
    sortie = maquette.run(Namespace(url=LIEN_CADRE))
    assert "Textes visibles : aucun" in sortie
    assert "Image non rendue" in sortie


def test_creer_ne_plante_pas_si_le_brouillon_a_deja_disparu(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    chemin = Path(brouillon(tmp_path))
    creation.side_effect = lambda ticket: (chemin.unlink(), ("p", "https://notion/p"))[1]
    assert creer.run(Namespace(brouillon=str(chemin), go=True)).startswith("Ticket créé")


def test_creer_en_ligne_de_commande_traite_un_5xx_comme_une_absence_de_reponse(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    creation.side_effect = httpx.HTTPStatusError(
        "502", request=REQUETE, response=httpx.Response(502, text="bad gateway")
    )
    with pytest.raises(SystemExit, match="Notion ne répond pas correctement : vérifier dans Notion"):
        lancer(mocker, creer, brouillon(tmp_path), "--go")


def test_creer_refuse_un_brouillon_qui_n_est_pas_un_objet(mocker, tmp_path):
    creer, _ = preparer_creer(mocker)
    liste = tmp_path / "liste.json"
    liste.write_text("[1, 2]")
    with pytest.raises(ValueError, match="objet JSON"):
        creer.run(Namespace(brouillon=str(liste), go=False))


def test_creer_continue_sans_auteur_apres_les_reessais_429(mocker, tmp_path):
    creer, _ = preparer_creer(mocker)
    mocker.patch.object(creer.backlog, "trouver_auteur", side_effect=RuntimeError("429"))
    assert "Auteur non inscrit" in creer.run(Namespace(brouillon=brouillon(tmp_path), go=True))


@pytest.mark.parametrize("erreur", [httpx.ReadTimeout("lent", request=REQUETE), RuntimeError("429")])
def test_auteur_illisible_ne_fait_pas_sortir_en_erreur(mocker, erreur):
    auteur = charger("auteur")
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(commun.config, "NOTION_ANNUAIRE_DB", "annuaire")
    mocker.patch.object(auteur.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch.object(auteur.backlog, "trouver_auteur", side_effect=erreur)
    assert auteur.run(Namespace(equipe=[])) == "Auteur non inscrit : annuaire ou comptes Notion illisibles."


@pytest.mark.parametrize(
    ("nom", "arguments", "attendu"),
    [
        ("contexte", [], "## Emplois inclusifs"),
        ("doublons", ["Titre test"], "- T (Cadrage, 1 mots communs) u"),
        ("auteur", [], "Auteur : Camille"),
        ("maquette", ["https://www.figma.com/board/AAAAAAAAAAAAAAAAAAAAAA/x"], "Lien Figma sans cadre précis"),
    ],
)
def test_scripts_de_lecture_en_ligne_de_commande_affichent_leur_resultat(mocker, capsys, nom, arguments, attendu):
    script = charger(nom)
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(commun.config, "NOTION_ANNUAIRE_DB", "annuaire")
    mocker.patch.object(commun.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch("lib.backlog_stockage.contexte_courant", return_value=CONTEXTE)
    mocker.patch("lib.backlog.trouver_auteur", return_value=AUTEUR)
    mocker.patch(
        "lib.backlog.chercher_doublons",
        return_value=[{"titre": "T", "url": "u", "statut": "Cadrage", "communs": 1}],
    )
    lancer(mocker, script, *arguments)
    assert attendu in capsys.readouterr().out


@pytest.mark.parametrize(
    ("erreur", "message"),
    [
        (
            httpx.HTTPStatusError("401", request=REQUETE, response=httpx.Response(401, text="unauthorized")),
            "Notion répond 401 : unauthorized",
        ),
        (httpx.ConnectTimeout("lent", request=REQUETE), "Notion ne répond pas."),
        (RuntimeError("429"), "Notion limite les appels : réessayer dans une minute."),
    ],
)
def test_lancer_traduit_les_erreurs_notion_en_une_ligne(mocker, erreur, message):
    parser = argparse.ArgumentParser()
    mocker.patch("sys.argv", ["script.py"])
    with pytest.raises(SystemExit, match=message):
        commun.lancer(mocker.Mock(side_effect=erreur), parser)


def test_lancer_affiche_le_resultat(mocker, capsys):
    mocker.patch("sys.argv", ["script.py"])
    commun.lancer(lambda args: "résultat", argparse.ArgumentParser())
    assert capsys.readouterr().out == "résultat\n"


@pytest.mark.parametrize(
    ("base", "annuaire", "demande", "attendu"),
    [
        (None, None, False, "NOTION_BACKLOG_DB absent"),
        ("db", None, False, None),
        ("db", None, True, "NOTION_ANNUAIRE_DB absent"),
        ("db", "annuaire", True, None),
    ],
)
def test_verifier_configuration_nomme_la_variable_absente(mocker, base, annuaire, demande, attendu):
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", base)
    mocker.patch.object(commun.config, "NOTION_ANNUAIRE_DB", annuaire)
    message = commun.verifier_configuration(annuaire=demande)
    assert (message is None) if attendu is None else message.startswith(attendu)


def test_creer_en_ligne_de_commande_dit_que_notion_limite_les_appels(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    creation.side_effect = RuntimeError("429")
    with pytest.raises(SystemExit, match="Notion limite les appels"):
        lancer(mocker, creer, brouillon(tmp_path), "--go")


def test_auteur_sans_compte_notion_dit_qu_il_ne_sera_pas_inscrit(mocker):
    auteur = charger("auteur")
    mocker.patch.object(commun.config, "NOTION_BACKLOG_DB", "db")
    mocker.patch.object(commun.config, "NOTION_ANNUAIRE_DB", "annuaire")
    mocker.patch.object(commun.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch.object(
        auteur.backlog, "trouver_auteur", return_value=backlog.Auteur("Camille", ["Designer"], ["e1"], None)
    )
    mocker.patch.object(auteur.backlog_stockage, "contexte_courant", return_value=CONTEXTE)
    sortie = auteur.run(Namespace(equipe=["Emplois inclusifs et dispositifs réglementés"]))
    assert "Inscrit dans : personne (pas de compte Notion)" in sortie
    assert "Inscrit dans : UX" not in sortie


def test_creer_sans_go_signale_un_auteur_sans_compte_notion(mocker, tmp_path):
    creer, _ = preparer_creer(mocker)
    mocker.patch.object(creer.backlog, "trouver_auteur", return_value=backlog.Auteur("Camille", [], ["e1"], None))
    sortie = creer.run(Namespace(brouillon=brouillon(tmp_path), go=False))
    assert "Auteur non inscrit : pas de compte Notion." in sortie


def test_creer_sans_go_refuse_si_le_ticket_vient_d_etre_cree(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    mocker.patch("lib.notion.query_database", return_value=[{"url": "https://notion/deja"}])
    with pytest.raises(ValueError, match="https://notion/deja"):
        creer.run(Namespace(brouillon=brouillon(tmp_path), go=False))
    creation.assert_not_called()
