"""Un graphique Mermaid en PNG : un navigateur sans écran dans un processus à part, un seul à la fois, temps borné."""

import logging
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

rendering = threading.Lock()


def render(source: str) -> bytes | None:
    """Le PNG du graphique ; None s'il n'a pas pu être dessiné en 60 s, ou si un autre rendu occupe la place 30 s."""
    if not rendering.acquire(timeout=30):
        logger.warning("Graphique non dessiné : un autre rendu est en cours depuis plus de 30 s")
        return None
    try:
        # Why: son propre groupe de processus, pour arrêter d'un coup le navigateur et ses enfants s'il s'éternise.
        child = subprocess.Popen(
            [sys.executable, "-m", "lib.mermaid_draw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).parent.parent,
            start_new_session=True,
        )
        try:
            png, errors = child.communicate(source.encode(), timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            errors = child.communicate()[1]
            logger.warning(
                "Graphique non dessiné : rendu arrêté après 60 s : %s", errors.decode(errors="replace")[-500:]
            )
            return None
    finally:
        rendering.release()
    if child.returncode or not png.startswith(b"\x89PNG"):
        logger.warning("Graphique non dessiné (code %s) : %s", child.returncode, errors.decode(errors="replace")[-500:])
        return None
    return png
