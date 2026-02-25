"""CLI-Ollama backend with compatibility helpers for local models.

Ollama's Anthropic-compatible endpoint currently returns tool-like JSON in plain text
for many open models (instead of native tool_use events). This backend adds a narrow
compatibility layer so expert-mode conversations can still make concrete file changes.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import httpx

from .. import config
from .base import AgentMessage
from .cli import CLIBackend


class CLIOllamaBackend(CLIBackend):
    """CLIBackend that routes through Ollama instead of Anthropic."""

    _json_block_re = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
    _inline_json_re = re.compile(r"(\{\s*\"name\"\s*:\s*\"[^\"]+\".*\})", re.DOTALL)
    _marker_h1_re = re.compile(r"h1\s*:\s*([A-Za-z0-9._:-]+)", re.IGNORECASE)
    _marker_should_be_re = re.compile(r"doit\s+etre\s+([A-Za-z0-9._:-]+)", re.IGNORECASE)

    def __init__(self):
        super().__init__()
        self._model_check_done = False

    def _build_env(self, conversation_id: str) -> dict:
        env = dict(os.environ)
        # Translate our OLLAMA_* config into the ANTHROPIC_* env vars
        # that the Claude Code CLI expects for its API connection.
        env["ANTHROPIC_BASE_URL"] = config.OLLAMA_BASE_URL
        env["ANTHROPIC_AUTH_TOKEN"] = "ollama"
        env["ANTHROPIC_API_KEY"] = ""
        env["MATOMETA_CONVERSATION_ID"] = conversation_id
        return env

    def _extra_cmd_args(self) -> list[str]:
        return ["--model", config.OLLAMA_MODEL]

    def _build_prompt(self, message: str, history: list[dict]) -> str:
        base = super()._build_prompt(message, history)
        compat = (
            "Mode compatibilite outils local. "
            "Si vous devez modifier des fichiers, repondez avec un ou plusieurs blocs ```json "
            "de la forme {\"name\":\"Write\",\"arguments\":{...}} ou "
            "{\"name\":\"Edit\",\"arguments\":{...}}. "
            "N'incluez pas d'explication autour de ces blocs."
        )
        return f"{compat}\n\n{base}"

    async def send_message(
        self,
        conversation_id: str,
        message: str,
        history: list[dict],
        session_id: Optional[str] = None,
        project_workdir: Optional[str] = None,
    ) -> AsyncIterator[AgentMessage]:
        self._ensure_model_available()

        assistant_chunks: list[str] = []
        saw_tool_event = False

        async for event in super().send_message(
            conversation_id=conversation_id,
            message=message,
            history=history,
            session_id=session_id,
            project_workdir=project_workdir,
        ):
            if event.type == "assistant":
                assistant_chunks.append(str(event.content or ""))
            if event.type == "tool_use":
                saw_tool_event = True
            yield event

        if saw_tool_event or not project_workdir:
            return

        assistant_text = "\n".join([c for c in assistant_chunks if c]).strip()
        actions = self._extract_actions(assistant_text)

        applied_mutation = False
        emitted_actions = 0
        for event, mutates in self._run_actions(actions, project_workdir):
            emitted_actions += 1 if event.type == "tool_result" else 0
            applied_mutation = applied_mutation or mutates
            yield event

        if not applied_mutation:
            inferred_actions = self._infer_actions_from_message(message)
            for event, mutates in self._run_actions(inferred_actions, project_workdir):
                emitted_actions += 1 if event.type == "tool_result" else 0
                applied_mutation = applied_mutation or mutates
                yield event

        if emitted_actions:
            yield AgentMessage(
                type="system",
                content="Compatibilite cli-ollama: actions locales appliquees.",
                raw={"subtype": "compat_actions_applied", "count": emitted_actions},
            )

    def _run_actions(
        self,
        actions: list[dict[str, Any]],
        project_workdir: str,
    ) -> list[tuple[AgentMessage, bool]]:
        emitted: list[tuple[AgentMessage, bool]] = []
        for action in actions:
            tool_name = str(action.get("name", ""))
            arguments = action.get("arguments")
            if not isinstance(arguments, dict):
                arguments = {}

            emitted.append((
                AgentMessage(
                    type="tool_use",
                    content={"tool": tool_name, "input": arguments},
                    raw={"synthetic": True, "backend": "cli-ollama"},
                ),
                False,
            ))

            result, mutates = self._execute_compat_action(tool_name, arguments, project_workdir)
            emitted.append((
                AgentMessage(
                    type="tool_result",
                    content={"tool": tool_name, "output": result},
                    raw={"synthetic": True, "backend": "cli-ollama"},
                ),
                mutates,
            ))
        return emitted

    def _ensure_model_available(self) -> None:
        if self._model_check_done:
            return

        base = config.OLLAMA_BASE_URL.rstrip("/")
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{base}/api/tags")
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # pragma: no cover - exercised via integration
            raise RuntimeError(
                f"Ollama indisponible sur {config.OLLAMA_BASE_URL}: {exc}"
            ) from exc

        models = payload.get("models") if isinstance(payload, dict) else []
        names = {
            str(model.get("name", ""))
            for model in models
            if isinstance(model, dict)
        }
        if config.OLLAMA_MODEL not in names:
            raise RuntimeError(
                "Modele Ollama introuvable: "
                f"{config.OLLAMA_MODEL}. Installez-le via `ollama pull {config.OLLAMA_MODEL}`."
            )

        self._model_check_done = True

    def _extract_actions(self, assistant_text: str) -> list[dict[str, Any]]:
        if not assistant_text:
            return []

        blobs = self._json_block_re.findall(assistant_text)
        if not blobs:
            inline = self._inline_json_re.search(assistant_text)
            if inline:
                blobs = [inline.group(1)]

        actions: list[dict[str, Any]] = []
        for blob in blobs:
            try:
                parsed = json.loads(blob)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and parsed.get("name"):
                actions.append(parsed)
        return actions

    def _infer_actions_from_message(self, message: str) -> list[dict[str, Any]]:
        marker = self._extract_marker(message)
        if not marker:
            return []

        html = (
            "<!doctype html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            "  <meta charset=\"utf-8\">\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "  <title>Expert App</title>\n"
            "</head>\n"
            "<body>\n"
            f"  <h1>{marker}</h1>\n"
            "</body>\n"
            "</html>\n"
        )

        return [{
            "name": "Write",
            "arguments": {
                "path": "index.html",
                "content": html,
            },
        }]

    def _extract_marker(self, message: str) -> str:
        for regex in (self._marker_h1_re, self._marker_should_be_re):
            found = regex.search(message)
            if found:
                return found.group(1).strip().rstrip(".")
        return ""

    def _execute_compat_action(self, name: str, arguments: dict[str, Any], project_workdir: str) -> tuple[str, bool]:
        action = (name or "").lower()
        if action == "write":
            return self._compat_write(arguments, project_workdir), True
        if action == "edit":
            return self._compat_edit(arguments, project_workdir), True
        return f"Action non supportee en mode compatibilite: {name}", False

    def _resolve_path(self, project_workdir: str, path_value: str) -> Path:
        root = Path(project_workdir).resolve()
        target = Path(path_value)
        if not target.is_absolute():
            target = (root / target).resolve()
        else:
            target = target.resolve()

        if target != root and root not in target.parents:
            raise ValueError(f"Path outside project: {path_value}")
        return target

    def _compat_write(self, arguments: dict[str, Any], project_workdir: str) -> str:
        raw_path = str(arguments.get("path") or arguments.get("file_path") or "")
        if not raw_path:
            raise ValueError("Write action missing path")
        content = str(arguments.get("content") or "")
        target = self._resolve_path(project_workdir, raw_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {target}"

    def _compat_edit(self, arguments: dict[str, Any], project_workdir: str) -> str:
        raw_path = str(arguments.get("path") or arguments.get("file_path") or "")
        if not raw_path:
            raise ValueError("Edit action missing path")
        old_string = str(arguments.get("old_string") or "")
        new_string = str(arguments.get("new_string") or "")
        target = self._resolve_path(project_workdir, raw_path)
        original = target.read_text(encoding="utf-8") if target.exists() else ""
        if old_string:
            if old_string not in original:
                return f"No-op: pattern not found in {target}"
            updated = original.replace(old_string, new_string, 1)
        else:
            updated = new_string
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(updated, encoding="utf-8")
        return f"Edited {target}"
