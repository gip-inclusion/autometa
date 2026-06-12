"""Tests for the guard_write_paths.py pre-tool-use hook."""

import importlib.util
from pathlib import Path

import pytest

_HOOK_PATH = Path(__file__).parent.parent / ".claude" / "hooks" / "guard_write_paths.py"
_spec = importlib.util.spec_from_file_location("guard_write_paths", _HOOK_PATH)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

LIVE = {"AUTOMETA_ENV": "live"}
ROOT = "/app"


def _verdict(path, env=LIVE, exists=lambda slug: True):
    return guard.verdict(path, ROOT, env, exists=exists)


@pytest.mark.parametrize("env", [{}, {"AUTOMETA_ENV": "dev"}])
def test_dev_or_unset_allows_everything(env):
    assert _verdict("/app/web/app.py", env=env) is None
    assert _verdict("/app/lib/query.py", env=env) is None


@pytest.mark.parametrize(
    "path",
    [
        "/tmp/scratch.py",
        "/tmp/sub/dir/file.json",
        "/app/data/cache/matomo/x.json",
        "/app/data/interactive/registered/index.html",
        "/app/data/interactive/notes.csv",
        "/app/.claude/plans/foo.md",
    ],
)
def test_live_allows_data_claude_tmp(path):
    assert _verdict(path) is None


@pytest.mark.parametrize(
    "path",
    [
        "/app/web/routes/interactive.py",
        "/app/lib/query.py",
        "/app/knowledge/sites/dora.md",
        "/app/alembic/versions/new.py",
        "/app/skills/create_dashboard/SKILL.md",
        "/app/config/sources.yaml",
        "/app/CLAUDE.md",
        "/app/Procfile",
        "/home/appsdeck/.bashrc",
    ],
)
def test_live_blocks_code_and_outside_paths(path):
    assert _verdict(path) == guard.BLOCK_CODE_MSG


@pytest.mark.parametrize(
    "path",
    [
        "/app/.claude/settings.json",
        "/app/.claude/settings.local.json",
        "/app/.claude/hooks/guard_write_paths.py",
        "/app/.claude/hooks/check_python.py",
    ],
)
def test_live_blocks_guard_config(path):
    assert _verdict(path) == guard.BLOCK_GUARD_MSG
