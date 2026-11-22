"""Un graphique Mermaid en PNG : merman-cli dans un processus à part, sans réseau ni police du système, temps borné."""

import logging
import struct
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Où bin/install_merman.sh pose le binaire et la police qu'il mesure et peint.
MERMAN = Path.home() / ".merman"


def render(source: str) -> bytes | None:
    """Le PNG du graphique ; None si merman-cli manque, le refuse, dépasse 10 s, ou rend une image trop grande."""
    command = [
        str(MERMAN / "merman-cli"),
        *("render", "-", "--format", "png", "--output", "-", "--quiet"),
        # Why: la police fournie, jamais celles du système : le même dessin sur toutes les machines.
        *("--font-file", str(MERMAN / "DejaVuSans.ttf"), "--font-file", str(MERMAN / "DejaVuSans-Bold.ttf")),
        *("--font-system", "off"),
        # Why: le texte d'un graphique vient d'une conversation ; le profil « constrained » de merman borne le travail
        # d'un document non fiable, et le réseau reste fermé faute de --allow-network.
        *("--resource-profile", "constrained", "--operation-timeout-ms", "8000"),
        *("--theme", "default", "--background", "white", "--scale", "2"),
        # Why: au-delà, merman réduit l'image à ces bornes ; un graphique réduit en hauteur n'est plus lisible.
        *("--raster-max-width", "2400", "--raster-max-height", "4000"),
    ]
    try:
        # Why: le délai de merman est coopératif ; celui-ci tue le processus s'il ne le respecte pas.
        drawn = subprocess.run(command, input=source.encode(), capture_output=True, timeout=10, check=False)
    except OSError as error:
        logger.warning("Graphique non dessiné, merman-cli inutilisable (bin/install_merman.sh l'installe) : %s", error)
        return None
    except subprocess.TimeoutExpired:
        logger.warning("Graphique non dessiné : rendu arrêté après 10 s")
        return None
    png = drawn.stdout
    if drawn.returncode or not png.startswith(b"\x89PNG"):
        logger.warning(
            "Graphique non dessiné (code %s) : %s", drawn.returncode, drawn.stderr.decode(errors="replace")[-500:]
        )
        return None
    width, height = struct.unpack(">II", png[16:24])
    if height >= 4000 or len(png) > 3_000_000:
        logger.warning("Graphique non montré : image de %s × %s px, %s octets", width, height, len(png))
        return None
    return png
