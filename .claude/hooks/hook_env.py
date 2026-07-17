"""Partagé par les hooks lint (phase 4) : détection serveur et binaire ruff."""

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from web.environment import Environment  # noqa: E402


def is_server():
    try:
        return Environment.current(os.environ.get("AUTOMETA_ENV")).is_server
    except ValueError:  # Why: env inconnu → on saute le hook de confort plutôt que de bloquer/spammer l'agent.
        return True


def ruff_base():
    if shutil.which("ruff"):
        return ["ruff"]
    return ["uv", "run", "--frozen", "ruff"]
