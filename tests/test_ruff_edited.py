"""Tests for the ruff_edited.py post-tool-use hook (phase 4a)."""

import importlib.util
from pathlib import Path

import pytest

_HOOK_PATH = Path(__file__).parent.parent / ".claude" / "hooks" / "ruff_edited.py"
_spec = importlib.util.spec_from_file_location("ruff_edited", _HOOK_PATH)
ruff_edited = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ruff_edited)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"tool_name": "Edit", "tool_input": {"file_path": "web/foo.py"}}, "web/foo.py"),
        ({"tool_name": "Write", "tool_input": {"file_path": "lib/bar.py"}}, "lib/bar.py"),
        ({"tool_name": "Edit", "tool_input": {"file_path": "docs/x.md"}}, None),
        ({"tool_name": "Bash", "tool_input": {"command": "ls"}}, None),
        ({"tool_name": "Write", "tool_input": {}}, None),
    ],
)
def test_edited_py_path(data, expected):
    assert ruff_edited.edited_py_path(data) == expected


def _fake_run(results):
    calls = list(results)

    def run(cmd, **kwargs):
        return calls.pop(0)

    return run


class _Proc:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_ruff_clean_returns_no_problem():
    run = _fake_run([_Proc(0), _Proc(0)])
    assert ruff_edited.run_ruff("web/foo.py", run=run) == []


def test_run_ruff_reports_check_failure():
    run = _fake_run([_Proc(1, stdout="F401 unused import"), _Proc(0)])
    problems = ruff_edited.run_ruff("web/foo.py", run=run)
    assert len(problems) == 1
    assert "F401" in problems[0]


def test_run_ruff_reports_format_failure():
    run = _fake_run([_Proc(0), _Proc(1, stdout="would reformat")])
    problems = ruff_edited.run_ruff("web/foo.py", run=run)
    assert len(problems) == 1
    assert "reformat" in problems[0]
