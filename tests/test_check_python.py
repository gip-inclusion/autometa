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
    "import psycopg2\n"
    + "url = os."
    + 'environ.get("DATABASE_URL")\n'
    + '"SELECT id FROM foo WHERE id = %'
    + 's"\n'
)


@pytest.mark.parametrize(
    ("path", "expect_violations"),
    [
        (".claude/hooks/guard_write_paths.py", False),
        ("/app/.claude/hooks/guard_write_paths.py", False),
        ("lib/foo.py", True),
        ("web/routes/bar.py", True),
    ],
)
def test_hook_scripts_exempt_from_import_env_sql_checks(path, expect_violations):
    violations = check_python.check(HOOK_ONLY_CODE, path)
    assert bool(violations) == expect_violations


def test_hook_scripts_still_checked_for_comments():
    code = "# ------------------------\nx = 1\n"
    assert check_python.check(code, ".claude/hooks/guard_write_paths.py")
