import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from skills.verifier_habilitation.scripts import etablissement


def unite(siret="13000548100010", etat="A", **complements):
    return {
        "nom_complet": "ASSOCIATION EXEMPLE",
        "activite_principale": "88.99B",
        "nature_juridique": "9220",
        "complements": complements,
        "matching_etablissements": [
            {
                "siret": siret,
                "etat_administratif": etat,
                "activite_principale": "88.99B",
                "adresse": "1 RUE EXEMPLE 69001 LYON",
                "commune": "69381",
                "liste_enseignes": None,
                "liste_finess": ["690000000"],
            }
        ],
    }


def answer(mocker, *results, status=200):
    request = httpx.Request("GET", "https://recherche-entreprises.api.gouv.fr/search")
    return mocker.patch.object(
        etablissement.httpx,
        "get",
        return_value=httpx.Response(status, json={"results": list(results)}, request=request),
    )


def test_fiche_lists_the_facts_of_the_matching_establishment(mocker):
    get = answer(mocker, unite(est_association=True, est_finess=True, est_siae=False))
    assert etablissement.fiche("130 005 481 00010").splitlines() == [
        "Nom : ASSOCIATION EXEMPLE",
        "Enseignes : aucune",
        "SIRET 13000548100010 : ouvert",
        "Adresse : 1 RUE EXEMPLE 69001 LYON (commune INSEE 69381)",
        "Activité (NAF) : établissement 88.99B, unité légale 88.99B",
        "Nature juridique (code INSEE) : 9220",
        "Indicateurs : association, FINESS",
        "FINESS : 690000000",
        "Fiche : https://annuaire-entreprises.data.gouv.fr/etablissement/13000548100010",
    ]
    assert get.call_args.kwargs["params"] == {"q": "13000548100010"}


def test_fiche_says_a_closed_establishment_is_closed(mocker):
    answer(mocker, unite(etat="F"))
    assert "SIRET 13000548100010 : fermé" in etablissement.fiche("13000548100010")


@pytest.mark.parametrize("results", [[], [unite(siret="13000548100028")]])
def test_fiche_says_when_the_siret_is_not_found(mocker, results):
    answer(mocker, *results)
    assert etablissement.fiche("13000548100010") == "SIRET 13000548100010 introuvable dans Recherche d'entreprises."


@pytest.mark.parametrize("siret", ["123", "1300054810001A", "13000548100010; DROP"])
def test_fiche_refuses_anything_but_fourteen_digits_without_calling(mocker, siret):
    get = answer(mocker)
    assert etablissement.fiche(siret) == "SIRET refusé : 14 chiffres attendus."
    get.assert_not_called()


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (httpx.HTTPStatusError("", request=None, response=httpx.Response(429)), "répond 429"),
        (httpx.ConnectError(""), "ne répond pas"),
    ],
)
def test_main_exits_in_one_line_when_the_api_fails(mocker, error, message):
    mocker.patch.object(etablissement.httpx, "get", side_effect=error)
    mocker.patch.object(sys, "argv", ["etablissement", "13000548100010"])
    with pytest.raises(SystemExit, match=message):
        etablissement.main()


def test_script_runs_as_a_module_from_the_repository_root():
    result = subprocess.run(
        [sys.executable, "-m", "skills.verifier_habilitation.scripts.etablissement", "--help"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
