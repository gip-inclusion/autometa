import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from skills.verify_prescriber_authorization.scripts import establishment


def unite(siret="13000548100010", etat="A", nature="9220", sigle=None, **complements):
    return {
        "nom_complet": "ASSOCIATION EXEMPLE",
        "sigle": sigle,
        "activite_principale": "88.99B",
        "nature_juridique": nature,
        "date_creation": "2001-05-04",
        "nombre_etablissements_ouverts": 2,
        "complements": complements,
        "siege": {"siret": siret},
        "matching_etablissements": [
            {
                "siret": siret,
                "etat_administratif": etat,
                "est_siege": False,
                "date_creation": "2026-11-24",
                "activite_principale": "88.99B",
                "adresse": "1 RUE EXEMPLE 69001 LYON",
                "libelle_commune": "LYON",
                "code_postal": "69001",
                "commune": "69381",
                "liste_enseignes": None,
                "liste_finess": ["690000000"],
            }
        ],
    }


def response(*results, status=200):
    request = httpx.Request("GET", establishment.API)
    return httpx.Response(status, json={"results": list(results)}, request=request)


def answer(mocker, *responses):
    return mocker.patch.object(establishment.httpx, "get", side_effect=list(responses))


def test_fiche_lists_the_facts_of_the_matching_establishment(mocker):
    get = answer(mocker, response(unite(sigle="AE", est_association=True, est_finess=True, est_siae=False)))
    assert establishment.fiche("130 005 481 00010").splitlines() == [
        "Nom : ASSOCIATION EXEMPLE (AE)",
        "Enseignes : aucune",
        "SIRET 13000548100010 : ouvert, établissement secondaire, créé le 2026-11-24",
        "Unité légale : créée le 2001-05-04, 2 établissement(s) ouvert(s)",
        "Commune : LYON (69001, INSEE 69381)",
        "Adresse : 1 RUE EXEMPLE 69001 LYON",
        "Activité (NAF) : établissement 88.99B, unité légale 88.99B",
        "Forme juridique : 9220 Association déclarée",
        "Indicateurs : association, FINESS",
        "FINESS : 690000000",
        "Fiche : https://annuaire-entreprises.data.gouv.fr/etablissement/13000548100010",
    ]
    assert get.call_args.kwargs == {"params": {"q": "13000548100010"}, "timeout": 5}


@pytest.mark.parametrize(
    ("unite_", "line"),
    [
        (unite(etat="F"), "SIRET 13000548100010 : fermé, établissement secondaire, créé le 2026-11-24"),
        (unite(sigle="EXEMPLE"), "Nom : ASSOCIATION EXEMPLE"),
        (unite(nature="5710"), "Forme juridique : 5710 (libellé à chercher)"),
        (
            unite(nature="7113"),
            "Repère : PJJ et SPIP s'inscrivent avec le SIRET de leur service territorial (7172), pas du ministère.",
        ),
    ],
)
def test_fiche_renders_each_fact(mocker, unite_, line):
    answer(mocker, response(unite_))
    assert line in establishment.fiche("13000548100010").splitlines()


@pytest.mark.parametrize(
    ("ccas", "line"),
    [
        (
            [unite(siret="26691006600916")],
            "CCAS ou CIAS ouvert dans la commune : ASSOCIATION EXEMPLE — SIRET 26691006600916",
        ),
        ([], "CCAS ou CIAS ouvert dans la commune : aucun"),
    ],
)
def test_fiche_looks_for_the_ccas_of_a_commune(mocker, ccas, line):
    get = answer(mocker, response(unite(nature="7210")), response(*ccas))
    assert line in establishment.fiche("13000548100010").splitlines()
    assert get.call_args.kwargs["params"] == {
        "nature_juridique": "7361,7367",
        "code_commune": "69381",
        "etat_administratif": "A",
    }


@pytest.mark.parametrize("results", [[], [unite(siret="13000548100028")]])
def test_fiche_says_when_the_siret_is_not_found(mocker, results):
    answer(mocker, response(*results))
    assert establishment.fiche("13000548100010") == "SIRET 13000548100010 introuvable dans Recherche d'entreprises."


@pytest.mark.parametrize("siret", ["123", "1300054810001A", "13000548100010; DROP"])
def test_fiche_refuses_anything_but_fourteen_digits_without_calling(mocker, siret):
    get = answer(mocker)
    assert establishment.fiche(siret) == "SIRET refusé : 14 chiffres attendus."
    get.assert_not_called()


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (httpx.HTTPStatusError("", request=None, response=httpx.Response(429)), "répond 429"),
        (httpx.ConnectError(""), "ne répond pas"),
    ],
)
def test_main_exits_in_one_line_when_the_api_fails(mocker, error, message):
    mocker.patch.object(establishment.httpx, "get", side_effect=error)
    mocker.patch.object(sys, "argv", ["establishment", "13000548100010"])
    with pytest.raises(SystemExit, match=message):
        establishment.main()


def test_script_runs_as_a_module_from_the_repository_root():
    result = subprocess.run(
        [sys.executable, "-m", "skills.verify_prescriber_authorization.scripts.establishment", "--help"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
