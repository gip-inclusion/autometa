"""Lecture seule des maquettes Figma : cadres, textes visibles et images."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from web import config

logger = logging.getLogger(__name__)

API = "https://api.figma.com/v1"
# Why: Figma met plusieurs secondes à sérialiser un gros nœud ou à rendre un cadre, au-delà du délai par défaut de 5 s.
TIMEOUT = 30
MAX_WIDTH = 1600
FRAME_TYPES = {"FRAME", "SECTION", "COMPONENT", "COMPONENT_SET"}
SCREEN_TYPES = {"FRAME", "COMPONENT", "COMPONENT_SET", "INSTANCE"}
LINK = re.compile(
    r"/(?:design|file|board|proto)/(?P<key>[0-9A-Za-z]{22,128})"
    r"(?:(?:/[^/]*)?/branch/(?P<branch>[0-9A-Za-z]{22,128}))?"
)
NODE_ID = re.compile(r"[?&]node-id=(\d+)(?:-|:|%3A)(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class FigmaLink:
    key: str
    node: str | None


@dataclass(frozen=True)
class Frame:
    id: str
    name: str
    texts: list[str]
    width: float


def parse_link(url: str) -> FigmaLink | None:
    """Fichier et nœud d'un lien https vers figma.com, ou None si ce n'en est pas un."""
    parts = urlsplit(url.strip())
    on_figma = parts.scheme == "https" and parts.hostname in ("figma.com", "www.figma.com")
    link = LINK.match(parts.path) if on_figma else None
    if not link:
        return None
    node = NODE_ID.search(url)
    return FigmaLink(
        key=link.group("branch") or link.group("key"),
        node=f"{node.group(1)}:{node.group(2)}" if node else None,
    )


def visible_texts(node: dict) -> list[str]:
    """Textes des calques visibles, dans l'ordre du document."""
    if node.get("visible") is False:
        return []
    text = node.get("characters", "").strip()
    texts = [text] if text else []
    for child in node.get("children", []):
        texts.extend(visible_texts(child))
    return texts


def pick_frames(node: dict) -> list[dict]:
    """Le nœud s'il est un écran, sinon ses cadres enfants visibles."""
    if node.get("type") in SCREEN_TYPES:
        return [node]
    children = [e for e in node.get("children", []) if e.get("type") in FRAME_TYPES and e.get("visible") is not False]
    return children or [node]


def call_api(path: str, params: dict | None = None) -> dict:
    """GET sur l'API Figma avec le jeton de plan."""
    response = httpx.get(
        f"{API}/{path}",
        params=params,
        headers={"X-Figma-Token": config.FIGMA_ACCESS_TOKEN or ""},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def read_frames(link: FigmaLink) -> list[Frame]:
    """Cadres du nœud lié, avec leurs textes visibles."""
    if not link.node:
        return []
    document = (call_api(f"files/{link.key}/nodes", {"ids": link.node})["nodes"].get(link.node) or {}).get("document")
    if not document:
        return []
    return [
        Frame(
            id=frame["id"],
            name=frame.get("name", ""),
            texts=visible_texts(frame),
            width=(frame.get("absoluteBoundingBox") or {}).get("width") or 0,
        )
        for frame in pick_frames(document)
    ]


def export_images(link: FigmaLink, frames: list[Frame], folder: Path) -> dict[str, Path]:
    """Une image PNG par cadre, réduite à MAX_WIDTH pixels, rangée par identifiant de cadre."""
    folder.mkdir(parents=True, exist_ok=True)
    scales = {c.id: max(0.01, round(min(1.0, MAX_WIDTH / c.width), 3)) if c.width else 1.0 for c in frames}
    urls = {}
    for scale in sorted(set(scales.values())):
        ids = [i for i, e in scales.items() if e == scale]
        response = call_api(f"images/{link.key}", {"ids": ",".join(ids), "format": "png", "scale": scale})
        urls.update(response["images"] or {})
    images = {}
    for rank, frame in enumerate(frames, start=1):
        url = urls.get(frame.id)
        if not url:
            logger.warning("Figma n'a pas rendu le cadre %s", frame.id)
            continue
        image = httpx.get(url, timeout=TIMEOUT)
        image.raise_for_status()
        path = folder / f"frame-{rank}.png"
        path.write_bytes(image.content)
        images[frame.id] = path
    return images
