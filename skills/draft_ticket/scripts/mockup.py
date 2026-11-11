"""Lit une maquette Figma : cadres, textes visibles et une image par cadre à regarder."""

import argparse

import httpx

from lib import figma
from skills.draft_ticket.scripts.common import conversation_folder
from web import config


def error_message(error: httpx.HTTPError) -> str:
    if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 429:
        return "Maquette non lue : Figma limite les appels (429), réessayer dans une minute."
    if isinstance(error, httpx.HTTPStatusError) and error.response.status_code in (403, 404):
        return f"Maquette non lue : Figma répond {error.response.status_code} (accès refusé ou fichier introuvable)."
    if isinstance(error, httpx.HTTPStatusError):
        return f"Maquette non lue : Figma répond {error.response.status_code}."
    return "Maquette non lue : Figma ne répond pas."


def run(args: argparse.Namespace) -> str:
    link = figma.parse_link(args.url)
    if link is None:
        return f"Ce n'est pas un lien Figma : {args.url}"
    if not link.node:
        return "Lien Figma sans cadre précis (pas de node-id) : maquette non lue. Demander un lien vers le cadre."
    if not config.FIGMA_ACCESS_TOKEN:
        return "FIGMA_ACCESS_TOKEN absent : maquette non lue."
    if not config.agent_conversation_id():
        return "AUTOMETA_CONVERSATION_ID absent : maquette non lue (pas de dossier pour les images)."
    try:
        frames = figma.read_frames(link)
    except httpx.HTTPError as error:
        return error_message(error)
    if not frames:
        return "Cadre introuvable dans ce fichier Figma (supprimé, ou lien vers un autre fichier) : demander un lien vers le cadre."
    lines = [f"# Maquette : {args.url}", ""]
    try:
        images = figma.export_images(
            link, frames, conversation_folder() / "figma" / f"{link.key}-{link.node.replace(':', '-')}"
        )
    except httpx.HTTPError as error:
        images = None
        lines.extend([f"Images non rendues ({error_message(error)}) : se fier aux textes.", ""])
    for rank, frame in enumerate(frames, start=1):
        lines.append(f"## Cadre {rank} : {frame.name}")
        if images is not None and frame.id in images:
            lines.append(f"Image à regarder : {images[frame.id]}")
        else:
            lines.append("Image non rendue")
        if frame.texts:
            lines.append("Textes visibles :")
            lines.extend(f"- {text}" for text in frame.texts)
        else:
            lines.append("Textes visibles : aucun")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="lien Figma vers un cadre (avec node-id)")
    print(run(parser.parse_args()))


if __name__ == "__main__":
    main()
