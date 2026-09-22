"""Les hooks de .claude/settings.json tournent depuis n'importe quel cwd, et ne se taisent jamais."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK_COMMANDS = [
    hook["command"]
    for groups in json.loads((ROOT / ".claude" / "settings.json").read_text())["hooks"].values()
    for group in groups
    for hook in group["hooks"]
]


def run_hook(command, cwd, project_dir, home, payload, env_value="dev"):
    """Le shell d'un hook Claude Code : cwd libre, $CLAUDE_PROJECT_DIR et $HOME posés par le CLI."""
    env = {
        "PATH": os.environ["PATH"],  # noqa: TID251
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "HOME": str(home),
        "AUTOMETA_ENV": env_value,
    }
    return subprocess.run(
        command, shell=True, input=json.dumps(payload), capture_output=True, text=True, env=env, cwd=cwd, timeout=30
    )


@pytest.mark.parametrize("command", HOOK_COMMANDS)
def test_a_hook_declared_in_user_settings_runs_from_a_foreign_project_dir(command, tmp_path):
    # Why: en prod HOME=/app, le settings.json est utilisateur et `claude` peut démarrer ailleurs
    # (cwd /tmp/autometa-llm-call) : le hook doit être trouvé à côté du settings qui le déclare.
    result = run_hook(command, cwd=tmp_path, project_dir=tmp_path, home=ROOT, payload={"stop_hook_active": True})

    assert result.returncode == 0, result.stderr
    assert "No such file" not in result.stderr


@pytest.mark.parametrize("command", HOOK_COMMANDS)
def test_a_hook_missing_from_both_locations_fails_loudly(command, tmp_path):
    """Jamais de garde muette : sans script ni côté projet ni côté utilisateur, python3 échoue."""
    result = run_hook(command, cwd=tmp_path, project_dir=tmp_path, home=tmp_path, payload={})

    assert result.returncode != 0
    assert "No such file" in result.stderr


def test_the_write_guard_still_blocks_when_started_outside_the_project(tmp_path):
    """La preuve que la garde d'écriture s'exécute, et pas seulement que la commande sort 0."""
    command = next(c for c in HOOK_COMMANDS if "guard_write_paths" in c)
    payload = {"tool_input": {"file_path": str(ROOT / "web" / "app.py")}}

    result = run_hook(command, cwd=tmp_path, project_dir=tmp_path, home=ROOT, payload=payload, env_value="prod")

    assert result.returncode == 2
    assert "Écriture refusée" in result.stderr
