"""Backend-agnostic LLM helpers for short prompts (titles, tags, etc.)."""

from __future__ import annotations

import logging

import httpx
import redis

from web import config
from web.llm_call import llm_call
from web.llm_errors import LLMError
from web.runner import limit_key

logger = logging.getLogger(__name__)

__all__ = ["LLMError", "backend_is_limited", "generate_text", "get_llm_backend", "ollama_generate"]


def get_llm_backend() -> str:
    backend = (config.LLM_BACKEND or config.AGENT_BACKEND).lower()
    return backend


def backend_is_limited(backend: str) -> bool:
    """Le moteur est dans sa fenêtre de limite d'usage — l'appeler ne ferait qu'attendre les retries."""
    # Why: client synchrone jetable — ces prompts partent de threads démons sans boucle asyncio,
    # et emprunter le pool async du runner depuis une autre boucle le corromprait.
    try:
        with redis.Redis.from_url(config.REDIS_URL, decode_responses=True) as client:
            return bool(client.exists(limit_key(backend)))
    except redis.RedisError as exc:
        logger.warning("Lecture de l'état de limite impossible pour %s : %s", backend, exc)
        return False


def generate_text(
    prompt: str,
    *,
    model: str | None = None,
    max_tokens: int = 100,
    temperature: float = 0.2,
    timeout: float | None = None,
) -> str:
    backend = get_llm_backend()

    # Why: sans ce garde-fou, chaque nouvelle conversation d'une fenêtre de limite consomme la
    # série complète de retries du CLI (~174 s) pour un résultat toujours vide.
    if backend_is_limited(backend):
        raise LLMError(f"Backend {backend} limité — prompt court abandonné")

    if backend in ("ollama", "cli-ollama"):
        return ollama_generate(
            prompt,
            model=model or config.OLLAMA_MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )

    if backend == "cli":
        return llm_call(prompt, model=model, timeout=timeout if timeout is not None else 60.0)

    raise LLMError(f"Unsupported LLM backend: {backend}")


def ollama_generate(
    prompt: str,
    *,
    model: str,
    max_tokens: int,
    temperature: float,
    timeout: float | None,
) -> str:
    base_url = config.OLLAMA_BASE_URL.rstrip("/")
    url = f"{base_url}/api/generate"
    timeout = timeout if timeout is not None else config.OLLAMA_REQUEST_TIMEOUT

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    try:
        response = httpx.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        text = data.get("response", "")
        return text.strip()
    except httpx.RequestError as exc:
        raise LLMError(f"Ollama request failed: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        raise LLMError(f"Ollama request failed: {exc}") from exc
