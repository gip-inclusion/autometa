"""Tool protocol and execution helpers for the Ollama backend."""

from __future__ import annotations

import fnmatch
import glob
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable, Optional

from .. import config

MAX_OUTPUT_CHARS = int(config.OLLAMA_MAX_OUTPUT_CHARS)


def tool_protocol() -> str:
    """Return instructions for the JSON tool-call protocol."""
    return (
        "Outils disponibles (repondez UNIQUEMENT avec un objet JSON sur une seule ligne):\n"
        "- Read: {\"tool\": \"Read\", \"input\": {\"file_path\": \"...\"}}\n"
        "- Write: {\"tool\": \"Write\", \"input\": {\"file_path\": \"...\", \"content\": \"...\"}}\n"
        "- Edit: {\"tool\": \"Edit\", \"input\": {\"file_path\": \"...\", \"old_string\": \"...\", \"new_string\": \"...\"}}\n"
        "- Glob: {\"tool\": \"Glob\", \"input\": {\"pattern\": \"...\"}}\n"
        "- Grep: {\"tool\": \"Grep\", \"input\": {\"pattern\": \"regex\", \"path\": \"...\"}}\n"
        "- Bash: {\"tool\": \"Bash\", \"input\": {\"command\": \"...\"}}\n"
        "- Skill: {\"tool\": \"Skill\", \"input\": {\"skill\": \"nom_du_skill\"}}\n"
        "\n"
        "Si vous devez utiliser un outil, repondez uniquement avec l'objet JSON.\n"
        "Sinon, repondez normalement."
    )


def parse_tool_call(text: str) -> Optional[tuple[str, dict]]:
    """Parse a tool call from the model output."""
    cleaned = text.strip()
    if not cleaned:
        return None

    if cleaned.startswith("```"):
        cleaned = _strip_code_fence(cleaned)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    if isinstance(payload, dict) and "tool" in payload and "input" in payload:
        tool_name = str(payload.get("tool"))
        tool_input = payload.get("input")
        if isinstance(tool_input, dict):
            return tool_name, tool_input
    return None


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and return its output as text."""
    if not isinstance(tool_input, dict):
        return f"Invalid tool input: expected dict, got {type(tool_input).__name__}"
    if tool_name == "Read":
        return _read_file(tool_input)
    if tool_name == "Write":
        return _write_file(tool_input)
    if tool_name == "Edit":
        return _edit_file(tool_input)
    if tool_name == "Glob":
        return _glob_files(tool_input)
    if tool_name == "Grep":
        return _grep_files(tool_input)
    if tool_name == "Bash":
        return _run_bash(tool_input)
    if tool_name == "Skill":
        return _read_skill(tool_input)
    return f"Unknown tool: {tool_name}"


def _strip_code_fence(text: str) -> str:
    lines = text.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return text


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = (config.BASE_DIR / path).resolve()
    return path.resolve()


def _is_within(path: Path, roots: Iterable[Path]) -> bool:
    resolved = path.resolve()
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def _read_file(tool_input: dict) -> str:
    file_path = tool_input.get("file_path")
    if not file_path:
        return "Missing file_path"

    path = _resolve_path(file_path)
    allowed_roots = [config.BASE_DIR, config.DATA_DIR, Path("/tmp")] + [Path(p) for p in config.ADDITIONAL_DIRS]

    if not _is_within(path, allowed_roots):
        return f"Read blocked: {path} is outside allowed roots"
    if not path.exists():
        return f"File not found: {path}"

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_bytes().decode("utf-8", errors="replace")

    return _truncate(content)


def _write_file(tool_input: dict) -> str:
    file_path = tool_input.get("file_path")
    content = tool_input.get("content")
    if not file_path:
        return "Missing file_path"
    if content is None:
        return "Missing content"

    path = _resolve_path(file_path)
    allowed_roots = [config.BASE_DIR, config.DATA_DIR, Path("/tmp")]
    if not _is_within(path, allowed_roots):
        return f"Write blocked: {path} is outside allowed roots"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {path}"


def _edit_file(tool_input: dict) -> str:
    file_path = tool_input.get("file_path")
    old_string = tool_input.get("old_string")
    new_string = tool_input.get("new_string")
    if not file_path:
        return "Missing file_path"
    if old_string is None or new_string is None:
        return "Missing old_string or new_string"

    path = _resolve_path(file_path)
    allowed_roots = [config.BASE_DIR, config.DATA_DIR, Path("/tmp")]
    if not _is_within(path, allowed_roots):
        return f"Edit blocked: {path} is outside allowed roots"
    if not path.exists():
        return f"File not found: {path}"

    content = path.read_text(encoding="utf-8")
    count = content.count(old_string)
    if count == 0:
        return f"old_string not found in {path}"
    if count > 1:
        return f"old_string matches {count} times in {path} — must be unique"

    content = content.replace(old_string, new_string, 1)
    path.write_text(content, encoding="utf-8")
    return f"Edited {path}"


def _glob_files(tool_input: dict) -> str:
    pattern = tool_input.get("pattern")
    if not pattern:
        return "Missing pattern"

    base = config.BASE_DIR
    matches = glob.glob(pattern, root_dir=base, recursive=True)
    limited = matches[:200]
    return "\n".join(limited) if limited else "No matches"


def _grep_files(tool_input: dict) -> str:
    pattern = tool_input.get("pattern")
    path_str = tool_input.get("path", ".")
    if not pattern:
        return "Missing pattern"

    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return f"Invalid regex: {exc}"

    root = _resolve_path(path_str)
    if not root.exists():
        return f"Path not found: {root}"

    allowed_roots = [config.BASE_DIR, config.DATA_DIR, Path("/tmp")]
    if not _is_within(root, allowed_roots):
        return f"Grep blocked: {root} is outside allowed roots"

    results = []

    paths = [root]
    if root.is_dir():
        paths = [p for p in root.rglob("*") if p.is_file()]

    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for idx, line in enumerate(lines, 1):
            if regex.search(line):
                rel_path = str(path.relative_to(config.BASE_DIR)) if _is_within(path, [config.BASE_DIR]) else str(path)
                results.append(f"{rel_path}:{idx}: {line}")
                if len(results) >= 200:
                    return "\n".join(results)

    return "\n".join(results) if results else "No matches"


def _run_bash(tool_input: dict) -> str:
    command = tool_input.get("command")
    if not command:
        return "Missing command"

    if not _bash_allowed(command):
        return "Bash command blocked by allowlist"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(config.BASE_DIR),
            text=True,
            capture_output=True,
            timeout=config.OLLAMA_BASH_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return "Bash command timed out"

    output = (result.stdout or "") + (result.stderr or "")
    output = output.strip()
    if not output:
        output = "(no output)"
    return _truncate(output)


def _bash_allowed(command: str) -> bool:
    allowed_tools = config.ALLOWED_TOOLS or ""

    # Bare "Bash" (not followed by "(") means all commands allowed
    if re.search(r"\bBash\b(?!\()", allowed_tools):
        return True

    # Extract Bash(prefix:glob) patterns — Claude CLI format
    patterns = re.findall(r"Bash\(([^)]+)\)", allowed_tools)
    if not patterns:
        return False

    for pattern in patterns:
        if ":" in pattern:
            prefix, arg_glob = pattern.split(":", 1)
            if command.startswith(prefix):
                rest = command[len(prefix):]
                # Enforce word boundary: rest must start with space or be empty
                if rest and not rest[0].isspace():
                    continue
                if fnmatch.fnmatch(rest, arg_glob):
                    return True
        else:
            if fnmatch.fnmatch(command, pattern):
                return True
    return False


def _read_skill(tool_input: dict) -> str:
    name = tool_input.get("skill")
    if not name:
        return "Missing skill name"

    candidates = [
        config.BASE_DIR / "skills" / name / "SKILL.md",
        config.BASE_DIR / ".claude" / "skills" / name / "SKILL.md",
    ]

    for path in candidates:
        if path.exists():
            return _truncate(path.read_text(encoding="utf-8"))

    return f"Skill not found: {name}"


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "\n... [truncated]"
