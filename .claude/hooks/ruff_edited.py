#!/usr/bin/env python3
"""Post-tool-use hook: lance ruff sur le .py édité et renvoie les erreurs à l'agent (phase 4a)."""

import json
import shutil
import subprocess
import sys


def edited_py_path(data):
    if data.get("tool_name") not in ("Edit", "Write"):
        return None
    path = data.get("tool_input", {}).get("file_path", "")
    return path if path.endswith(".py") else None


def ruff_base():
    if shutil.which("ruff"):
        return ["ruff"]
    return ["uv", "run", "--frozen", "ruff"]


def run_ruff(path, run=subprocess.run):
    base = ruff_base()
    problems = []
    for args in (["check", path], ["format", "--check", path]):
        proc = run(base + args, capture_output=True, text=True)
        if proc.returncode != 0:
            problems.append((proc.stdout + proc.stderr).strip())
    return problems


def main():
    data = json.load(sys.stdin)
    path = edited_py_path(data)
    if path is None:
        return 0
    problems = run_ruff(path)
    if not problems:
        return 0
    print(f"ruff signale des problèmes sur {path} :\n", file=sys.stderr)
    for report in problems:
        print(report, file=sys.stderr)
    print("\nCorrige (ou lance `make format`) avant de continuer.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
