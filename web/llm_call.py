"""`claude --print` one-shot pour complétions courtes (titres, tags)."""

import subprocess
from pathlib import Path

from web import config
from web.llm_errors import LLMError

# Why: cwd vide dédié — évite le chargement CLAUDE.md/skills (coût plusieurs
# secondes) et les fichiers parasites de /tmp racine.
CWD = Path("/tmp/autometa-llm-call")


def llm_call(prompt: str, *, model: str | None = None, timeout: float = 60.0) -> str:
    CWD.mkdir(exist_ok=True)
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

    if result.returncode != 0:
        raise LLMError(result.stderr.strip() or "Claude CLI error")

    return result.stdout.strip()
