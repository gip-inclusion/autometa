import importlib.util
import subprocess
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "check_required_checks", Path(__file__).parent.parent / "scripts" / "check_required_checks.py"
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def workflow_file(tmp_path, body):
    path = tmp_path / "ci.yml"
    path.write_text(body)
    return path


def completed(returncode, stdout=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


@pytest.mark.parametrize(
    "body,expected",
    [
        ("jobs:\n  lint:\n    name: Lint & format\n", {"Lint & format"}),
        ("jobs:\n  lint:\n    runs-on: ubuntu-latest\n", {"lint"}),
        ("jobs:\n  lint:\n    name: Lint\n  test:\n    name: Tests\n", {"Lint", "Tests"}),
    ],
)
def test_declared_check_names(tmp_path, body, expected):
    assert _module.declared_check_names(workflow_file(tmp_path, body)) == expected


def test_declared_check_names_reads_the_real_workflow():
    names = _module.declared_check_names(Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml")
    assert names == {"Lint & format", "Security", "Tests", "Migrations", "Docker"}


@pytest.mark.parametrize(
    "declared,required,expected_count",
    [
        ({"Tests"}, {"Tests"}, 0),
        ({"Tests", "Docker"}, {"Tests"}, 1),
        ({"Tests"}, {"Tests", "CodeQL"}, 1),
        ({"Tests"}, {"Docker"}, 2),
    ],
)
def test_drift(declared, required, expected_count):
    assert len(_module.drift(declared, required)) == expected_count


def test_drift_names_the_job_left_out_of_the_protection():
    assert "Docker" in _module.drift({"Tests", "Docker"}, {"Tests"})[0]


@pytest.mark.parametrize(
    "process,expected",
    [
        (completed(1), None),
        (completed(0, '{"contexts": ["Tests", "Docker"]}'), {"Tests", "Docker"}),
        (completed(0, "{}"), set()),
    ],
)
def test_required_check_names(mocker, process, expected):
    mocker.patch.object(subprocess, "run", return_value=process)
    assert _module.required_check_names("owner/repo", "main") == expected


def test_required_check_names_without_gh_installed(mocker):
    mocker.patch.object(subprocess, "run", side_effect=FileNotFoundError)
    assert _module.required_check_names("owner/repo", "main") is None


def test_main_passes_when_protection_is_not_armed(mocker, capsys):
    mocker.patch.object(_module, "required_check_names", return_value=None)
    assert _module.main() == 0
    assert "non armée" in capsys.readouterr().out


def test_main_fails_on_drift(mocker):
    mocker.patch.object(_module, "declared_check_names", return_value={"Tests"})
    mocker.patch.object(_module, "required_check_names", return_value={"Docker"})
    assert _module.main() == 1


def test_main_passes_when_aligned(mocker):
    mocker.patch.object(_module, "declared_check_names", return_value={"Tests"})
    mocker.patch.object(_module, "required_check_names", return_value={"Tests"})
    assert _module.main() == 0
