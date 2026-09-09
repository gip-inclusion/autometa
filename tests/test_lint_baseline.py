"""Tests for scripts/check_lint_baseline.py — une dette gelée se résorbe, elle ne s'étend pas."""

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "check_lint_baseline", Path(__file__).parent.parent / "scripts" / "check_lint_baseline.py"
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

GELE = {"web/routes/reports.py:S608": 3, "lib/query.py:BLE001": 1}


@pytest.mark.parametrize(
    ("mesure", "attendu"),
    [
        ({"web/routes/reports.py:S608": 3, "lib/query.py:BLE001": 1}, []),
        ({"web/routes/reports.py:S608": 4, "lib/query.py:BLE001": 1}, ["passe de 3 à 4"]),
        ({"web/routes/reports.py:S608": 3, "lib/query.py:BLE001": 1, "web/neuf.py:S608": 1}, ["passe de 0 à 1"]),
        ({"web/routes/reports.py:S608": 2, "lib/query.py:BLE001": 1}, ["descend de 3 à 2"]),
        ({"web/routes/reports.py:S608": 3}, ["descend de 1 à 0"]),
    ],
)
def test_report_blocks_growth_and_reclaims_what_was_repaired(mesure, attendu):
    problems = _module.report(mesure, GELE)

    assert len(problems) == len(attendu)
    for problem, motif in zip(problems, attendu, strict=True):
        assert motif in problem


def test_the_baseline_of_the_repository_is_read_as_counts_by_file_and_rule():
    rules, frozen = _module.read_baseline(Path(__file__).parent.parent / "gates.toml")

    assert set(rules) == {"S608", "BLE001"}
    assert all(":" in key and count > 0 for key, count in frozen.items())


def test_measure_counts_ruff_findings_by_file_and_rule(mocker, tmp_path):
    sortie = (
        f'[{{"filename": "{tmp_path}/web/a.py", "code": "S608"}}, {{"filename": "{tmp_path}/web/a.py",'
        f' "code": "S608"}}, {{"filename": "{tmp_path}/lib/b.py", "code": "BLE001"}}]'
    )
    run = mocker.patch.object(_module.subprocess, "run", return_value=mocker.Mock(stdout=sortie, returncode=1))

    assert _module.measure(["S608", "BLE001"], tmp_path) == {"web/a.py:S608": 2, "lib/b.py:BLE001": 1}
    assert "S608,BLE001" in run.call_args.args[0]


def test_measure_says_why_when_ruff_itself_fails(mocker, tmp_path):
    """Un lock désynchronisé sortait en JSONDecodeError, en perdant le message de ruff."""
    mocker.patch.object(
        _module.subprocess, "run", return_value=mocker.Mock(stdout="", stderr="error: invalid value", returncode=2)
    )

    with pytest.raises(RuntimeError, match="invalid value"):
        _module.measure(["NEXISTEPAS"], tmp_path)


def test_the_frozen_baseline_matches_what_the_repository_actually_carries():
    """Sans cette mesure, la baseline dérive et le gel ne gèle plus rien."""
    root = Path(__file__).parent.parent
    rules, frozen = _module.read_baseline(root / "gates.toml")

    assert _module.report(_module.measure(rules, root), frozen) == []


DOCSTRING_TROP_LONGUE = 'def f():\n    """Une docstring\n    sur\n    trois lignes."""\n    return 1\n'


def test_measure_conventions_counts_violations_by_file_and_skips_what_is_not_ours(tmp_path):
    (tmp_path / "a.py").write_text(DOCSTRING_TROP_LONGUE)
    for ignore in (".venv", "data"):
        (tmp_path / ignore).mkdir()
        (tmp_path / ignore / "b.py").write_text(DOCSTRING_TROP_LONGUE)

    assert _module.measure_conventions(tmp_path) == {"a.py": 1}


def test_the_frozen_conventions_match_what_the_repository_actually_carries():
    """Les trois règles de `.claude/rules/` qui citent ce script comme vérificateur deviennent vraies ici."""
    root = Path(__file__).parent.parent

    assert _module.report(_module.measure_conventions(root), _module.read_conventions(root / "gates.toml")) == []


def test_main_refuses_a_convention_debt_that_grows(mocker, capsys):
    mocker.patch.object(_module, "measure", return_value={})
    mocker.patch.object(_module, "read_baseline", return_value=([], {}))
    mocker.patch.object(_module, "read_conventions", return_value={"web/a.py": 1})
    mocker.patch.object(_module, "measure_conventions", return_value={"web/a.py": 2})

    assert _module.main() == 1
    assert "passe de 1 à 2" in capsys.readouterr().out
