"""Fiche d'un établissement dans l'API publique Recherche d'entreprises, à partir de son SIRET."""

import argparse
import re
import sys

import httpx


def fiche(siret: str) -> str:
    siret = re.sub(r"\s", "", siret)
    if not re.fullmatch(r"\d{14}", siret):
        return "SIRET refusé : 14 chiffres attendus."
    response = httpx.get("https://recherche-entreprises.api.gouv.fr/search", params={"q": siret}, timeout=10)
    response.raise_for_status()
    for unite in response.json()["results"]:
        for etablissement in unite["matching_etablissements"]:
            if etablissement["siret"] == siret:
                return render(unite, etablissement)
    return f"SIRET {siret} introuvable dans Recherche d'entreprises."


def render(unite: dict, etablissement: dict) -> str:
    complements = unite["complements"]
    indicateurs = {
        "est_association": "association",
        "est_finess": "FINESS",
        "est_service_public": "service public",
        "est_administration": "administration",
        "collectivite_territoriale": "collectivité territoriale",
        "est_siae": "SIAE",
        "est_ess": "ESS",
    }
    siret = etablissement["siret"]
    return "\n".join([
        f"Nom : {unite['nom_complet']}",
        f"Enseignes : {', '.join(etablissement['liste_enseignes'] or []) or 'aucune'}",
        f"SIRET {siret} : {'ouvert' if etablissement['etat_administratif'] == 'A' else 'fermé'}",
        f"Adresse : {etablissement['adresse']} (commune INSEE {etablissement['commune']})",
        f"Activité (NAF) : établissement {etablissement['activite_principale']}, "
        f"unité légale {unite['activite_principale']}",
        f"Nature juridique (code INSEE) : {unite['nature_juridique']}",
        f"Indicateurs : {', '.join(nom for cle, nom in indicateurs.items() if complements.get(cle)) or 'aucun'}",
        f"FINESS : {', '.join(etablissement['liste_finess'] or []) or 'aucun'}",
        f"Fiche : https://annuaire-entreprises.data.gouv.fr/etablissement/{siret}",
    ])


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
