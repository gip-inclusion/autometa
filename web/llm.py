"""Backend-agnostic LLM helpers for short prompts (titles, tags, etc.)."""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from web import config
from web.llm_call import llm_call
from web.llm_errors import LLMError

logger = logging.getLogger(__name__)

__all__ = ["LLMError", "generate_text", "get_llm_backend", "ollama_generate"]


def get_llm_backend() -> str:
    backend = (config.LLM_BACKEND or config.AGENT_BACKEND).lower()
    return backend


def generate_text(
    prompt: str,
    *,
    model: Optional[str] = None,
    max_tokens: int = 100,
    temperature: float = 0.2,
    timeout: Optional[float] = None,
) -> str:
    backend = get_llm_backend()

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
    timeout: Optional[float],
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
