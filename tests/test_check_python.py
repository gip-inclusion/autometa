"""Tests for the check_python.py pre-tool-use hook."""

import importlib.util
from pathlib import Path

import pytest

_HOOK_PATH = Path(__file__).parent.parent / ".claude" / "hooks" / "check_python.py"
_spec = importlib.util.spec_from_file_location("check_python", _HOOK_PATH)
check_python = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_python)

# Why: assembled so this test file's own lines don't trigger the hook when written via Edit/Write.
HOOK_ONLY_CODE = (
    "import psycopg2\n" + "url = os." + 'environ.get("DATABASE_URL")\n' + '"SELECT id FROM foo WHERE id = %' + 's"\n'
)


@pytest.mark.parametrize(
    ("path", "expect_violations"),
    [
        (".claude/hooks/guard_write_paths.py", False),
        ("/app/.claude/hooks/guard_write_paths.py", False),
        ("lib/foo.py", True),
        ("web/routes/bar.py", True),
        (".claude/hooks/../../lib/evil.py", True),
    ],
)
def test_hook_scripts_exempt_from_import_env_sql_checks(path, expect_violations):
    violations = check_python.check(HOOK_ONLY_CODE, path)
    assert bool(violations) == expect_violations


@pytest.mark.parametrize(
    ("path", "expect_violations"),
    [
        # Partout où ruff tourne, TID251 porte la règle : la rejouer ici ferait diverger les deux.
        ("tests/conftest.py", False),
        ("tests/test_foo.py", False),
        ("lib/foo.py", False),
        # data/ est exclu de la configuration ruff, et c'est là que l'agent écrit les tableaux de bord.
        ("data/interactive/tdb/cron.py", True),
    ],
)
def test_env_vars_are_checked_only_where_ruff_is_blind(path, expect_violations):
    code = "os." + 'environ["SLACK_BOT_TOKEN"] = ""\n'
    assert bool(check_python.check(code, path)) == expect_violations


def test_hook_scripts_still_checked_for_comments():
    code = "# ------------------------\nx = 1\n"
    assert check_python.check(code, ".claude/hooks/guard_write_paths.py")


# Why: assemblées pour que les lignes de ce fichier ne déclenchent pas le hook à l'écriture.
RUFF_OWNED_CODE = [
    "import requests\n",
    "url = os." + 'environ.get("DATABASE_URL")\n',
    'httpx.get("https://example.org")\n',
    "logger.info(f" + '"{x}")\n',
    "from ..module import thing\n",
]


@pytest.mark.parametrize("code", RUFF_OWNED_CODE)
@pytest.mark.parametrize(
    ("path", "expect_violations"),
    [
        ("data/interactive/tdb/cron.py", True),
        ("/app/data/interactive/tdb/cron.py", True),
        ("lib/foo.py", False),
        ("web/routes/bar.py", False),
        ("tests/test_foo.py", False),
    ],
)
def test_ruff_owned_rules_replayed_only_where_ruff_is_blind(code, path, expect_violations):
    assert bool(check_python.check(code, path)) == expect_violations


# Why: les mots-clés sont coupés en deux pour que les lignes de ce fichier ne déclenchent pas
# elles-mêmes le check qu'elles vérifient — même raison que HOOK_ONLY_CODE plus haut.
_INS = "inse" + "rt"
_FROM = "fr" + "om"
_SEL = "SELE" + "CT"
_WHERE = "WHE" + "RE"

RAISE_FROM = f'raise RuntimeError(f"Failed to {_INS} {{n}} rows") {_FROM} None\n'
LOG_FROM = f'logger.info(f"handled {{n}} rows {_FROM} the queue")\n'
VRAI_SQL = f'db.execute(f"{_SEL} id {_FROM.upper()} users {_WHERE} name = {{name}}")\n'


@pytest.mark.parametrize(
    ("code", "attendu"),
    [
        (RAISE_FROM, False),
        (LOG_FROM, False),
        (VRAI_SQL, True),
    ],
)
def test_python_exception_chaining_is_not_sql_interpolation(code, attendu):
    """« from None » est de la syntaxe Python : le compter comme mot-clé SQL fait crier sur un message d'erreur."""
    violations = [v for v in check_python.check(code, "web/foo.py") if "Interpolation SQL" in v]

    assert bool(violations) is attendu
