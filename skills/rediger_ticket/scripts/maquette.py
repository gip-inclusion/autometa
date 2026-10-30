"""Lit une maquette Figma : cadres, textes visibles et une image par cadre à regarder."""

import argparse
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import figma  # noqa: E402
from web import config  # noqa: E402


def dossier_images() -> Path:
    return Path("/tmp/rediger_ticket") / (config.agent_conversation_id() or "local")


def message_erreur(erreur: httpx.HTTPError) -> str:
    if isinstance(erreur, httpx.HTTPStatusError) and erreur.response.status_code == 429:
        return "Maquette non lue : Figma limite les appels (429), réessayer dans une minute."
    if isinstance(erreur, httpx.HTTPStatusError) and erreur.response.status_code in (403, 404):
        return f"Maquette non lue : Figma répond {erreur.response.status_code} (accès refusé ou fichier introuvable)."
    if isinstance(erreur, httpx.HTTPStatusError):
        return f"Maquette non lue : Figma répond {erreur.response.status_code}."
    return "Maquette non lue : Figma ne répond pas."


def run(args: argparse.Namespace) -> str:
    lien = figma.analyser_lien(args.url)
    if lien is None:
        return f"Ce n'est pas un lien Figma : {args.url}"
    if not lien.noeud:
        return "Lien Figma sans cadre précis (pas de node-id) : maquette non lue. Demander un lien vers le cadre."
    if not config.FIGMA_ACCESS_TOKEN:
        return "FIGMA_ACCESS_TOKEN absent : maquette non lue."
    try:
        cadres = figma.lire_cadres(lien)
    except httpx.HTTPError as erreur:
        return message_erreur(erreur)
    if not cadres:
        return "Cadre introuvable dans ce fichier Figma (supprimé, ou lien vers un autre fichier) : demander un lien vers le cadre."
    lignes = [f"# Maquette : {args.url}", ""]
    try:
        images = figma.exporter_images(lien, cadres, dossier_images() / f"{lien.cle}-{lien.noeud.replace(':', '-')}")
    except httpx.HTTPError as erreur:
        images = {}
        lignes.extend([f"Images non rendues ({message_erreur(erreur)}) : se fier aux textes.", ""])
    for rang, cadre in enumerate(cadres, start=1):
        lignes.append(f"## Cadre {rang} : {cadre.nom}")
        if cadre.id in images:
            lignes.append(f"Image à regarder : {images[cadre.id]}")
        elif images:
            lignes.append("Image non rendue")
        if cadre.textes:
            lignes.append("Textes visibles :")
            lignes.extend(f"- {texte}" for texte in cadre.textes)
        else:
            lignes.append("Textes visibles : aucun")
        lignes.append("")
    return "\n".join(lignes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="lien Figma vers un cadre (avec node-id)")
    print(run(parser.parse_args()))


if __name__ == "__main__":
    main()
