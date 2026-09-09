import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "check_required_checks", Path(__file__).parent.parent / "scripts" / "check_required_checks.py"
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

RULESET = json.dumps([
    {"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "Lint"}]}}
])


def completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["gh"], returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.mark.parametrize(
    ("resultat", "attendu"),
    [
        (completed(0, RULESET), {"Lint"}),
        (completed(_module.GH_UNAUTHENTICATED, stderr="gh: not authenticated"), None),
    ],
)
def test_gh_absent_ou_non_authentifie_ne_leve_pas(mocker, resultat, attendu):
    mocker.patch("subprocess.run", return_value=resultat)
    assert _module.required_check_names("dep", "main") == attendu


def test_gh_introuvable_rend_none(mocker):
    mocker.patch("subprocess.run", side_effect=FileNotFoundError)
    assert _module.required_check_names("dep", "main") is None


@pytest.mark.parametrize("code", [1, 2, 3, 5])
def test_erreur_api_leve(mocker, code):
    mocker.patch("subprocess.run", return_value=completed(code, stderr="HTTP 403"))
    with pytest.raises(RuntimeError):
        _module.required_check_names("dep", "main")


def test_main_sort_zero_quand_gh_non_authentifie(mocker, capsys):
    mocker.patch("subprocess.run", return_value=completed(_module.GH_UNAUTHENTICATED))
    assert _module.main() == 0
    assert "non authentifié" in capsys.readouterr().out
