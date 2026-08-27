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
    assert names == {
        "Lint & format",
        "Security",
        "Tests unit (sans services)",
        "Tests integration (Postgres + Redis)",
        "Couverture fusionnée + diff-cover",
        "Migrations",
        "Docker",
        "Review app",
        "Ce qui devait marcher",
    }


@pytest.mark.parametrize(
    "declared,required,blocking,to_require",
    [
        ({"Tests"}, {"Tests"}, 0, 0),
        ({"Tests", "Docker"}, {"Tests"}, 0, 1),
        ({"Tests"}, {"Tests", "CodeQL"}, 1, 0),
        ({"Tests"}, {"Docker"}, 1, 1),
    ],
)
def test_drift(declared, required, blocking, to_require):
    bloquants, a_inscrire = _module.drift(declared, required)

    assert (len(bloquants), len(a_inscrire)) == (blocking, to_require)


def test_drift_names_the_job_left_out_of_the_protection():
    assert "Docker" in _module.drift({"Tests", "Docker"}, {"Tests"})[1][0]


def test_a_renamed_job_stays_blocking():
    """Renommer un job éteindrait la protection en silence : le nom requis disparaît de ci.yml."""
    bloquants, a_inscrire = _module.drift({"Unit tests"}, {"Tests"})

    assert "Tests" in bloquants[0]
    assert "Unit tests" in a_inscrire[0]


@pytest.mark.parametrize(
    ("required", "expected"),
    [({"Tests"}, 0), ({"Docker"}, 1)],
)
def test_main_ne_bloque_que_sur_un_check_requis_inexistant(mocker, required, expected):
    mocker.patch.object(_module, "declared_check_names", return_value={"Tests"})
    mocker.patch.object(_module, "required_check_names", return_value=required)

    assert _module.main() == expected


def ruleset(contexts, autres_regles=()):
    """Forme rendue par `gh api repos/{repo}/rules/branches/{branch}`."""
    regle = {
        "type": "required_status_checks",
        "parameters": {"required_status_checks": [{"context": c} for c in contexts]},
    }
    return json.dumps([*({"type": t} for t in autres_regles), regle])


@pytest.mark.parametrize(
    "process,expected",
    [
        (completed(0, ruleset(["Tests", "Docker"])), {"Tests", "Docker"}),
        (completed(0, ruleset(["Tests"], autres_regles=("deletion", "non_fast_forward"))), {"Tests"}),
        (completed(0, "[]"), set()),
        (completed(0, '[{"type": "deletion"}]'), set()),
    ],
)
def test_required_check_names(mocker, process, expected):
    mocker.patch.object(subprocess, "run", return_value=process)
    assert _module.required_check_names("owner/repo", "main") == expected


def test_required_check_names_reads_the_ruleset_not_the_classic_protection(mocker):
    """Les sept checks vivent dans le ruleset ; la protection classique n'en connaît qu'un."""
    run = mocker.patch.object(subprocess, "run", return_value=completed(0, ruleset(["Tests"])))

    _module.required_check_names("owner/repo", "main")

    assert run.call_args.args[0] == ["gh", "api", "repos/owner/repo/rules/branches/main"]


def test_required_check_names_without_gh_installed(mocker):
    mocker.patch.object(subprocess, "run", side_effect=FileNotFoundError)
    assert _module.required_check_names("owner/repo", "main") is None


def test_required_check_names_raises_when_the_api_refuses(mocker):
    """Un check aveugle est vert quoi qu'il arrive : on échoue plutôt que de rassurer."""
    mocker.patch.object(
        subprocess, "run", return_value=subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="HTTP 403")
    )

    with pytest.raises(RuntimeError, match="HTTP 403"):
        _module.required_check_names("owner/repo", "main")


def test_main_fails_when_the_ruleset_is_unreadable(mocker, capsys):
    mocker.patch.object(_module, "required_check_names", side_effect=RuntimeError("HTTP 403"))

    assert _module.main() == 1
    assert "illisible" in capsys.readouterr().out


@pytest.mark.parametrize(
    "required,attendu_dans_la_sortie",
    [(None, "gh absent"), (set(), "Aucun check requis")],
)
def test_main_passes_when_nothing_can_be_compared(mocker, capsys, required, attendu_dans_la_sortie):
    mocker.patch.object(_module, "declared_check_names", return_value={"Tests"})
    mocker.patch.object(_module, "required_check_names", return_value=required)

    assert _module.main() == 0
    assert attendu_dans_la_sortie in capsys.readouterr().out


def test_main_fails_on_drift(mocker):
    mocker.patch.object(_module, "declared_check_names", return_value={"Tests"})
    mocker.patch.object(_module, "required_check_names", return_value={"Docker"})
    assert _module.main() == 1


def test_main_passes_when_aligned(mocker):
    mocker.patch.object(_module, "declared_check_names", return_value={"Tests"})
    mocker.patch.object(_module, "required_check_names", return_value={"Tests"})
    assert _module.main() == 0
