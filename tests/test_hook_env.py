"""Tests for the shared hook_env helper — server detection gates the lint hooks (phase 4)."""

import importlib.util
import sys
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).parent.parent / ".claude" / "hooks"
sys.path.insert(0, str(_HOOKS_DIR))
_spec = importlib.util.spec_from_file_location("hook_env", _HOOKS_DIR / "hook_env.py")
hook_env = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook_env)


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, False),
        ({"AUTOMETA_ENV": "dev"}, False),
        ({"AUTOMETA_ENV": "review"}, True),
        ({"AUTOMETA_ENV": "staging"}, True),
        ({"AUTOMETA_ENV": "prod"}, True),
        ({"AUTOMETA_ENV": "bogus"}, True),
    ],
)
def test_is_server(mocker, env, expected):
    mocker.patch.dict("os.environ", env, clear=True)
    assert hook_env.is_server() is expected
