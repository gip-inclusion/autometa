"""Lecture seule des maquettes Figma : cadres, textes visibles et images."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from web import config

logger = logging.getLogger(__name__)

API = "https://api.figma.com/v1"
# Why: Figma met plusieurs secondes à sérialiser un gros nœud ou à rendre un cadre, au-delà du délai par défaut de 5 s.
TIMEOUT = 30
LARGEUR_MAX = 1600
TYPES_CADRE = {"FRAME", "SECTION", "COMPONENT", "COMPONENT_SET"}
TYPES_ECRAN = {"FRAME", "COMPONENT", "COMPONENT_SET", "INSTANCE"}
LIEN = re.compile(
    r"figma\.com/(?:design|file|board|proto)/(?P<cle>[0-9A-Za-z]{22,128})"
    r"(?:(?:/[^/?]*)?/branch/(?P<branche>[0-9A-Za-z]{22,128}))?"
)
NOEUD = re.compile(r"[?&]node-id=(\d+)(?:-|:|%3A)(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class LienFigma:
    cle: str
    noeud: str | None


@dataclass(frozen=True)
class Cadre:
    id: str
    nom: str
    textes: list[str]
    largeur: float


def analyser_lien(url: str) -> LienFigma | None:
    """Fichier et nœud d'un lien Figma, ou None si ce n'en est pas un."""
    lien = LIEN.search(url)
    if not lien:
        return None
    noeud = NOEUD.search(url)
    return LienFigma(
        cle=lien.group("branche") or lien.group("cle"),
        noeud=f"{noeud.group(1)}:{noeud.group(2)}" if noeud else None,
    )


def textes_visibles(noeud: dict) -> list[str]:
    """Textes des calques visibles, dans l'ordre du document."""
    if noeud.get("visible") is False:
        return []
    texte = noeud.get("characters", "").strip()
    textes = [texte] if texte else []
    for enfant in noeud.get("children", []):
        textes.extend(textes_visibles(enfant))
    return textes


def choisir_cadres(noeud: dict, maximum: int = 6) -> list[dict]:
    """Le nœud s'il est un écran, sinon ses cadres enfants visibles."""
    if noeud.get("type") in TYPES_ECRAN:
        return [noeud]
    enfants = [e for e in noeud.get("children", []) if e.get("type") in TYPES_CADRE and e.get("visible") is not False]
    return (enfants or [noeud])[:maximum]


def appeler_api(chemin: str, params: dict | None = None) -> dict:
    """GET sur l'API Figma avec le jeton de plan."""
    reponse = httpx.get(
        f"{API}/{chemin}",
        params=params,
        headers={"X-Figma-Token": config.FIGMA_ACCESS_TOKEN or ""},
        timeout=TIMEOUT,
    )
    reponse.raise_for_status()
    return reponse.json()


def lire_cadres(lien: LienFigma) -> list[Cadre]:
    """Cadres du nœud lié, avec leurs textes visibles."""
    if not lien.noeud:
        return []
    document = (appeler_api(f"files/{lien.cle}/nodes", {"ids": lien.noeud})["nodes"].get(lien.noeud) or {}).get(
        "document"
    )
    if not document:
        return []
    return [
        Cadre(
            id=cadre["id"],
            nom=cadre.get("name", ""),
            textes=textes_visibles(cadre),
            largeur=(cadre.get("absoluteBoundingBox") or {}).get("width") or 0,
        )
        for cadre in choisir_cadres(document)
    ]


def exporter_images(lien: LienFigma, cadres: list[Cadre], dossier: Path) -> dict[str, Path]:
    """Une image PNG par cadre, réduite à LARGEUR_MAX pixels, rangée par identifiant de cadre."""
    dossier.mkdir(parents=True, exist_ok=True)
    echelles = {c.id: max(0.01, round(min(1.0, LARGEUR_MAX / c.largeur), 3)) if c.largeur else 1.0 for c in cadres}
    urls = {}
    for echelle in sorted(set(echelles.values())):
        ids = [i for i, e in echelles.items() if e == echelle]
        reponse = appeler_api(f"images/{lien.cle}", {"ids": ",".join(ids), "format": "png", "scale": echelle})
        urls.update(reponse["images"] or {})
    images = {}
    for rang, cadre in enumerate(cadres, start=1):
        url = urls.get(cadre.id)
        if not url:
            logger.warning("Figma n'a pas rendu le cadre %s", cadre.id)
            continue
        image = httpx.get(url, timeout=TIMEOUT)
        image.raise_for_status()
        chemin = dossier / f"cadre-{rang}.png"
        chemin.write_bytes(image.content)
        images[cadre.id] = chemin
    return images
