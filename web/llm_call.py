"""`claude --print` one-shot pour complétions courtes (titres, tags)."""

import subprocess
import threading
from pathlib import Path

from web import config
from web.llm_errors import LLMError

# Why: cwd vide dédié — évite le chargement CLAUDE.md/skills (coût plusieurs
# secondes) et les fichiers parasites de /tmp racine.
CWD = Path("/tmp/autometa-llm-call")
# Why: le titre et les tags d'une conversation partent ensemble au premier message, à côté du CLI de
# l'agent ; chaque `claude --print` pèse ~180 Mio. Un seul à la fois borne le pic mémoire du conteneur
# (le code -9 de la review app de #278).
ONE_AT_A_TIME = threading.Lock()


def llm_call(prompt: str, *, model: str | None = None, timeout: float = 60.0) -> str:
    CWD.mkdir(exist_ok=True)
    if not ONE_AT_A_TIME.acquire(timeout=timeout):
        raise LLMError("Claude CLI busy with another short prompt")
    try:
        result = subprocess.run(
            [config.CLAUDE_CLI, "--print", "--model", model or config.LLM_MODEL, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(CWD),
        )
    except subprocess.TimeoutExpired as exc:
        raise LLMError("Claude CLI timed out") from exc
    except OSError as exc:
        raise LLMError(f"Claude CLI failed: {exc}") from exc
    finally:
        ONE_AT_A_TIME.release()

    if result.returncode != 0:
        raise LLMError(result.stderr.strip() or "Claude CLI error")

    return result.stdout.strip()
