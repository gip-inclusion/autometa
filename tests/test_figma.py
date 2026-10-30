import pytest

from lib import figma

CLE = "A" * 22
BRANCHE = "B" * 22


def noeud(type_, nom="n", enfants=None, texte=None, visible=True, largeur=None, id_="1:1"):
    n = {"id": id_, "type": type_, "name": nom, "children": enfants or []}
    if texte is not None:
        n["characters"] = texte
    if not visible:
        n["visible"] = False
    if largeur is not None:
        n["absoluteBoundingBox"] = {"width": largeur, "height": 100}
    return n


@pytest.mark.parametrize(
    ("url", "attendu"),
    [
        (f"https://www.figma.com/design/{CLE}/Maquette?node-id=4524-5330&t=x", figma.LienFigma(CLE, "4524:5330")),
        (f"https://www.figma.com/design/{CLE}/Maquette?node-id=12%3A34", figma.LienFigma(CLE, "12:34")),
        (f"https://www.figma.com/board/{CLE}/Notifications?t=x", figma.LienFigma(CLE, None)),
        (f"https://www.figma.com/design/{CLE}/branch/{BRANCHE}/x?node-id=1-5", figma.LienFigma(BRANCHE, "1:5")),
        (f"https://www.figma.com/design/{CLE}/x/branch/{BRANCHE}/x?node-id=1-5", figma.LienFigma(BRANCHE, "1:5")),
        ("https://exemple.fr/design/abc", None),
    ],
)
def test_analyser_lien(url, attendu):
    assert figma.analyser_lien(url) == attendu


def test_dod_1_textes_visibles_ignore_les_calques_masques():
    cadre = noeud(
        "FRAME",
        enfants=[
            noeud("TEXT", texte="Titre"),
            noeud("GROUP", visible=False, enfants=[noeud("TEXT", texte="Ancien texte")]),
            noeud("TEXT", texte="  "),
            noeud("TEXT", texte="Bouton"),
        ],
    )
    assert figma.textes_visibles(cadre) == ["Titre", "Bouton"]


@pytest.mark.parametrize(
    ("racine", "noms"),
    [
        (noeud("FRAME", nom="Écran"), ["Écran"]),
        (
            noeud("SECTION", nom="S", enfants=[noeud("FRAME", nom="Vue pro"), noeud("FRAME", nom="Vue candidat")]),
            ["Vue pro", "Vue candidat"],
        ),
        (noeud("CANVAS", enfants=[noeud("FRAME", nom=str(i)) for i in range(8)]), ["0", "1", "2", "3", "4", "5"]),
        (
            noeud("CANVAS", enfants=[noeud("FRAME", nom="masqué", visible=False), noeud("FRAME", nom="visible")]),
            ["visible"],
        ),
    ],
)
def test_choisir_cadres(racine, noms):
    assert [c["name"] for c in figma.choisir_cadres(racine)] == noms


def test_dod_1_lire_cadres_sans_noeud_ne_lit_rien(mocker):
    appel = mocker.patch.object(figma, "appeler_api")
    assert figma.lire_cadres(figma.LienFigma(CLE, None)) == []
    appel.assert_not_called()


def test_dod_1_lire_cadres_donne_nom_textes_et_largeur(mocker):
    document = noeud(
        "SECTION",
        enfants=[
            noeud(
                "FRAME",
                nom="Choix 1",
                id_="2:2",
                largeur=1435,
                enfants=[noeud("TEXT", texte="Accepter la candidature")],
            )
        ],
    )
    mocker.patch.object(figma, "appeler_api", return_value={"nodes": {"4:5": {"document": document}}})
    cadres = figma.lire_cadres(figma.LienFigma(CLE, "4:5"))
    assert cadres == [figma.Cadre(id="2:2", nom="Choix 1", textes=["Accepter la candidature"], largeur=1435)]


@pytest.mark.parametrize(("largeur", "echelle"), [(3200, 0.5), (800, 1.0), (0, 1.0)])
def test_dod_1_exporter_images_reduit_la_largeur_et_ecrit_le_png(mocker, tmp_path, largeur, echelle):
    appel = mocker.patch.object(figma, "appeler_api", return_value={"images": {"2:2": "https://rendu/2-2.png"}})
    mocker.patch.object(figma.httpx, "get", return_value=mocker.Mock(content=b"PNG"))
    cadre = figma.Cadre(id="2:2", nom="Choix 1", textes=[], largeur=largeur)
    images = figma.exporter_images(figma.LienFigma(CLE, "4:5"), [cadre], tmp_path)
    assert appel.call_args.args[1]["scale"] == echelle
    assert images == {"2:2": tmp_path / "cadre-1.png"}
    assert (tmp_path / "cadre-1.png").read_bytes() == b"PNG"


def test_dod_1_exporter_images_saute_un_cadre_non_rendu(mocker, tmp_path):
    appel = mocker.patch.object(
        figma, "appeler_api", return_value={"images": {"2:2": None, "2:3": "https://rendu/2-3.png"}}
    )
    mocker.patch.object(figma.httpx, "get", return_value=mocker.Mock(content=b"PNG"))
    cadres = [figma.Cadre(id=i, nom=i, textes=[], largeur=800) for i in ("2:2", "2:3")]
    images = figma.exporter_images(figma.LienFigma(CLE, "4:5"), cadres, tmp_path)
    assert images == {"2:3": tmp_path / "cadre-2.png"}
    assert not (tmp_path / "cadre-1.png").exists()
    appel.assert_called_once()
    assert appel.call_args.args[1]["ids"] == "2:2,2:3"


@pytest.mark.parametrize("reponse", [{"nodes": {}}, {"nodes": {"4:5": None}}])
def test_dod_1_lire_cadres_noeud_absent_ne_renvoie_rien(mocker, reponse):
    mocker.patch.object(figma, "appeler_api", return_value=reponse)
    assert figma.lire_cadres(figma.LienFigma(CLE, "4:5")) == []


def test_appeler_api_envoie_le_jeton_de_plan(mocker):
    mocker.patch.object(figma.config, "FIGMA_ACCESS_TOKEN", "jeton")
    get = mocker.patch.object(figma.httpx, "get", return_value=mocker.Mock(json=lambda: {"ok": True}))
    assert figma.appeler_api("files/x/nodes", {"ids": "1:2"}) == {"ok": True}
    assert get.call_args.kwargs["headers"] == {"X-Figma-Token": "jeton"}
    assert get.call_args.kwargs["timeout"] == figma.TIMEOUT
