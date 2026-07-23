"""Tests for the stop_lint_gate.py stop hook (phase 4b, lint-only)."""

import importlib.util
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).parent.parent / ".claude" / "hooks"
sys.path.insert(0, str(_HOOKS_DIR))
_spec = importlib.util.spec_from_file_location("stop_lint_gate", _HOOKS_DIR / "stop_lint_gate.py")
stop_lint_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stop_lint_gate)


class _Proc:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _fake_run(codes):
    procs = [_Proc(rc, stdout=out) for rc, out in codes]

    def run(cmd, **kwargs):
        return procs.pop(0)

    return run


def test_no_failure_when_all_green():
    run = _fake_run([(0, ""), (0, ""), (0, "")])
    assert stop_lint_gate.failing_checks(run=run) == []


def test_collects_failing_check_with_label_and_output():
    run = _fake_run([(1, "F401 unused import"), (0, ""), (0, "")])
    failures = stop_lint_gate.failing_checks(run=run)
    assert len(failures) == 1
    label, output = failures[0]
    assert "ruff" in label
    assert "F401" in output


def test_collects_failing_detector():
    run = _fake_run([(0, ""), (0, ""), (1, "test sans vérification")])
    failures = stop_lint_gate.failing_checks(run=run)
    assert len(failures) == 1
    assert "vérification" in failures[0][1]


def test_commands_are_lint_only_suite_runs_at_pre_push():
    cmds = [cmd for cmd, _label in stop_lint_gate.commands()]
    assert not any("pytest" in cmd for cmd in cmds)


def test_block_reason_mentions_each_failure():
    reason = stop_lint_gate.block_reason([("ruff check", "F401 boom"), ("détecteur", "creux")])
    assert "ruff check" in reason
    assert "F401 boom" in reason
    assert "détecteur" in reason
