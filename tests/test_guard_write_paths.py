"""Tests for the guard_write_paths.py pre-tool-use hook."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_HOOK_PATH = Path(__file__).parent.parent / ".claude" / "hooks" / "guard_write_paths.py"
_spec = importlib.util.spec_from_file_location("guard_write_paths", _HOOK_PATH)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

SERVER = {"AUTOMETA_ENV": "prod"}
ROOT = "/app"


def _verdict(path, env=SERVER, exists=lambda slug: True):
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
def test_server_allows_data_claude_tmp(path):
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
def test_server_blocks_code_and_outside_paths(path):
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
def test_server_blocks_guard_config(path):
    assert _verdict(path) == guard.BLOCK_GUARD_MSG


def test_server_blocks_unregistered_slug_dir():
    v = _verdict("/app/data/interactive/rogue-app/index.html", exists=lambda slug: False)
    assert v == guard.BLOCK_UNREGISTERED_MSG


def test_server_allows_registered_slug_dir():
    seen = []

    def exists(slug):
        seen.append(slug)
        return True

    assert _verdict("/app/data/interactive/my-tdb/sub/data.json", exists=exists) is None
    assert seen == ["my-tdb"]


def test_server_blocks_html_at_interactive_root():
    assert _verdict("/app/data/interactive/page.html") == guard.BLOCK_ROOT_HTML_MSG
    assert _verdict("/app/data/interactive/page.htm") == guard.BLOCK_ROOT_HTML_MSG
    assert _verdict("/app/data/interactive/export.csv") is None


@pytest.mark.parametrize("env_value", ["live", "Production", "prd"])
def test_invalid_env_fails_closed(env_value):
    assert _verdict("/tmp/x.py", env={"AUTOMETA_ENV": env_value}) == guard.BLOCK_BAD_ENV_MSG


def test_slug_exists_fails_open_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert guard.slug_exists("anything") is True


def test_slug_exists_fails_open_on_connection_error(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none?connect_timeout=1")
    assert guard.slug_exists("anything") is True


@pytest.mark.parametrize(
    ("stdin_payload", "env_value", "expected_exit"),
    [
        ('{"tool_input": {"file_path": "/app/web/x.py"}}', "dev", 0),
        ('{"tool_input": {"file_path": "/app/web/x.py"}}', "staging", 2),
        ('{"tool_input": {"file_path": "/app/web/x.py"}}', "review", 2),
        ('{"tool_input": {"file_path": "/app/web/x.py"}}', "prod", 2),
        ('{"tool_input": {"file_path": "/app/web/x.py"}}', "live", 2),
        ('{"tool_input": {"file_path": "/tmp/x.py"}}', "live", 2),
        ('{"tool_input": {"file_path": "/tmp/x.py"}}', "prod", 0),
        ('{"tool_input": {}}', "prod", 0),
        ("not json", "prod", 1),
    ],
)
def test_main_protocol_exit_codes(stdin_payload, env_value, expected_exit, tmp_path):
    env = dict(os.environ, AUTOMETA_ENV=env_value)  # noqa: TID251
    env.pop("DATABASE_URL", None)
    result = subprocess.run(
        [sys.executable, str(_HOOK_PATH)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
        cwd="/app" if Path("/app").is_dir() else str(tmp_path),
        timeout=10,
    )
    assert result.returncode == expected_exit


def test_the_repo_root_is_the_hook_location_not_the_cwd(tmp_path):
    """Depuis un autre cwd, data/ du dépôt reste autorisé : la racine ne se déduit pas du cwd."""
    env = dict(os.environ, AUTOMETA_ENV="prod")  # noqa: TID251
    env.pop("DATABASE_URL", None)
    allowed = _HOOK_PATH.parents[2] / "data" / "cache" / "x.json"

    result = subprocess.run(
        [sys.executable, str(_HOOK_PATH)],
        input=json.dumps({"tool_input": {"file_path": str(allowed)}}),
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr


CONFORMING = "from lib.dashboard_api import query_matomo\n"
OFFENDING = "from lib.query import execute_matomo_query\n"


@pytest.mark.parametrize(
    ("path", "code", "refuse"),
    [
        ("/app/data/interactive/tdb/cron.py", OFFENDING, True),
        ("/app/data/interactive/tdb/lib/helper.py", OFFENDING, True),
        ("/app/data/interactive/tdb/cron.py", CONFORMING, False),
        ("/app/data/interactive/tdb/cron.py", "import json\n", False),
        # Why: un fragment d'Edit n'est pas un module complet — le refuser bloquerait toute retouche.
        ("/app/data/interactive/tdb/cron.py", "def main(\n", False),
        ("/app/data/interactive/notes.py", OFFENDING, False),
        ("/app/data/cache/script.py", OFFENDING, False),
        ("/app/lib/query.py", OFFENDING, False),
        ("/app/data/interactive/tdb/index.html", OFFENDING, False),
    ],
)
def test_the_facade_is_enforced_where_the_dashboard_code_enters(path, code, refuse):
    """Le hook voit passer le code d'un TDB, quel que soit l'environnement — les métadonnées non."""
    verdict = guard.facade_verdict(path, code, ROOT)

    assert (verdict is not None) == refuse
    if refuse:
        assert "lib.query" in verdict
