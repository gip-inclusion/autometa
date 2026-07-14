#!/usr/bin/env python3
"""Stop hook: empêche l'agent de conclure sur du lint ou des tests creux (phase 4b, sans DB)."""

import json
import shutil
import subprocess
import sys

SCOPE = ["web/", "lib/", "tests/", "scripts/"]


def ruff_base():
    if shutil.which("ruff"):
        return ["ruff"]
    return ["uv", "run", "--frozen", "ruff"]


def commands():
    base = ruff_base()
    return [
        (base + ["check", *SCOPE], "ruff check"),
        (base + ["format", "--check", *SCOPE], "ruff format --check"),
        ([sys.executable, "scripts/check_test_quality.py", "tests"], "détecteur de tests creux"),
    ]


def failing_checks(run=subprocess.run):
    failures = []
    for cmd, label in commands():
        proc = run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            failures.append((label, (proc.stdout + proc.stderr).strip()))
    return failures


def block_reason(failures):
    parts = ["Tu ne peux pas conclure : des contrôles sont rouges. Corrige-les avant de t'arrêter."]
    for label, output in failures:
        parts.append(f"\n[{label}]\n{output}")
    return "\n".join(parts)


def main():
    data = json.load(sys.stdin)
    if data.get("stop_hook_active"):
        return 0
    failures = failing_checks()
    if failures:
        print(json.dumps({"decision": "block", "reason": block_reason(failures)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
