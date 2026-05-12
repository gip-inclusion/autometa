"""`claude --print` one-shot pour complétions courtes (titres, tags)."""

import logging
import subprocess
from pathlib import Path

from web import config
from web.llm_errors import LLMError

logger = logging.getLogger(__name__)

# Why: répertoire vide dédié — pas de CLAUDE.md/skills/permissions chargés (BASE_DIR coûte plusieurs secondes au démarrage), et pas de fichiers parasites comme dans /tmp racine sur lesquels l'agent pourrait s'égarer.
_CWD = Path("/tmp/autometa-llm-call")


def llm_call(prompt: str, *, model: str | None = None, timeout: float = 60.0) -> str:
    _CWD.mkdir(exist_ok=True)
    try:
        result = subprocess.run(
            [config.CLAUDE_CLI, "--print", "--model", model or config.LLM_MODEL, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(_CWD),
        )
    except subprocess.TimeoutExpired as exc:
        raise LLMError("Claude CLI timed out") from exc
    except OSError as exc:
        raise LLMError(f"Claude CLI failed: {exc}") from exc

    if result.returncode != 0:
        raise LLMError(result.stderr.strip() or "Claude CLI error")

    return result.stdout.strip()
