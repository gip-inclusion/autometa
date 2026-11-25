"""Faits SIRENE d'un établissement, lus dans l'API publique Recherche d'entreprises à partir de son SIRET."""

import argparse
import re
import sys

import httpx

API = "https://recherche-entreprises.api.gouv.fr/search"

FORMES_JURIDIQUES = {
    "7113": "Ministère",
    "7171": "Service déconcentré de l'État à compétence (inter)régionale",
    "7172": "Service déconcentré de l'État à compétence (inter)départementale",
    "7210": "Commune",
    "7220": "Département",
    "7230": "Région",
    "7361": "Centre communal d'action sociale",
    "7367": "Centre intercommunal d'action sociale",
    "9220": "Association déclarée",
    "9221": "Association déclarée d'insertion par l'économique",
    "9300": "Fondation",
}

INDICATEURS = {
    "est_association": "association",
    "est_finess": "FINESS",
    "est_service_public": "service public",
    "est_administration": "administration",
    "collectivite_territoriale": "collectivité territoriale",
    "est_siae": "SIAE",
    "est_ess": "ESS",
}


def search(**params) -> list[dict]:
    response = httpx.get(API, params=params, timeout=5)
    response.raise_for_status()
    return response.json()["results"]


def fiche(siret: str) -> str:
    siret = re.sub(r"\s", "", siret)
    if not re.fullmatch(r"\d{14}", siret):
        return "SIRET refusé : 14 chiffres attendus."
    for unite in search(q=siret):
        for etablissement in unite["matching_etablissements"]:
            if etablissement["siret"] == siret:
                return render(unite, etablissement)
    return f"SIRET {siret} introuvable dans Recherche d'entreprises."


def render(unite: dict, etablissement: dict) -> str:
    siret = etablissement["siret"]
    nature = unite["nature_juridique"]
    complements = unite["complements"]
    lines = [
        f"Nom : {unite['nom_complet']}"
        + (f" ({sigle})" if (sigle := unite["sigle"]) and sigle not in unite["nom_complet"] else ""),
        f"Enseignes : {', '.join(etablissement['liste_enseignes'] or []) or 'aucune'}",
        f"SIRET {siret} : {'ouvert' if etablissement['etat_administratif'] == 'A' else 'fermé'}, "
        f"{'siège' if etablissement['est_siege'] else 'établissement secondaire'}, créé le {etablissement['date_creation']}",
        f"Unité légale : créée le {unite['date_creation']}, {unite['nombre_etablissements_ouverts']} établissement(s) ouvert(s)",
        f"Commune : {etablissement['libelle_commune']} ({etablissement['code_postal']}, INSEE {etablissement['commune']})",
        f"Adresse : {etablissement['adresse']}",
        f"Activité (NAF) : établissement {etablissement['activite_principale']}, unité légale {unite['activite_principale']}",
        f"Forme juridique : {nature} {FORMES_JURIDIQUES.get(nature, '(libellé à chercher)')}",
        f"Indicateurs : {', '.join(nom for cle, nom in INDICATEURS.items() if complements.get(cle)) or 'aucun'}",
        f"FINESS : {', '.join(etablissement['liste_finess'] or []) or 'aucun'}",
    ]
    if nature == "7210":
        ccas = search(nature_juridique="7361,7367", code_commune=etablissement["commune"], etat_administratif="A")
        lines.append(
            "CCAS ou CIAS ouvert dans la commune : "
            + ("; ".join(f"{u['nom_complet']} — SIRET {u['siege']['siret']}" for u in ccas) or "aucun")
        )
    if nature == "7113":
        lines.append(
            "Repère : PJJ et SPIP s'inscrivent avec le SIRET de leur service territorial (7172), pas du ministère."
        )
    lines.append(f"Fiche : https://annuaire-entreprises.data.gouv.fr/etablissement/{siret}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("siret", help="SIRET de l'établissement (14 chiffres, espaces tolérés)")
    try:
        print(fiche(parser.parse_args().siret))
    except httpx.HTTPStatusError as error:
        sys.exit(f"Recherche d'entreprises répond {error.response.status_code} : réessayer dans une minute.")
    except httpx.TransportError:
        sys.exit("Recherche d'entreprises ne répond pas.")


if __name__ == "__main__":
    main()
