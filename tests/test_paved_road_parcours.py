"""Le parcours paved road, joué de bout en bout par la CLI sur un dépôt jetable."""

# Les tests unitaires de `lib/attestation.py` font tous partir la branche de parcours de `main`.
# La vraie vie n'a pas cette forme, et c'est ce qui a laissé passer un contrôle faux : ici, chaque
# déroulé nominal est rejoué sur trois topologies de dépôt, et chaque contrôle a son pendant
# négatif. Sans cette seconde moitié, on pourrait désarmer tous les contrôles sans qu'un test bronche.

import importlib.util
import shutil
from pathlib import Path

import pytest

from lib import attestation
from tests.test_attestation import commit, make_repo, prove_command

FEATURE = "ma-feature"
ROOT = Path(__file__).parent.parent

# Le dépôt jetable porte de quoi jouer le parcours pour de vrai : la CLI que les checks d'`align` et
# de `prove` rappellent en sous-processus, le diagnostic que `build` lance, et les cibles `make` que
# `start` et `build` invoquent. Rien de tout cela n'est simulé — seul `PYTHONPATH` rend `lib/`.
OUTILLAGE = """hooks:
\t@printf '#!/bin/sh\\nexit 0\\n' > "$$(git rev-parse --git-path hooks)/pre-commit"
\t@chmod +x "$$(git rev-parse --git-path hooks)/pre-commit"

install-hooks:
\t@printf '#!/bin/sh\\nexit 0\\n' > "$$(git rev-parse --git-path hooks)/pre-push"
\t@chmod +x "$$(git rev-parse --git-path hooks)/pre-push"

lint security test:
\t@true
"""
DOCTEUR = "print('  ok    Docker')\nprint('Environnement prêt.')\n"

CONTRAT = """# Notification de fin de réponse

## Ce que je veux

Être prévenu quand l'agent a fini de répondre.

## Ce qui devra marcher

DOD-1 — Un son se fait entendre quand la réponse est terminée.

## Sources lues

Le brief du demandeur.

## Questions ouvertes

Aucune.

## Validation

Validé par test@example.invalid le 2026-09-01.
"""

ROUGE = prove_command("DOD-1", ok=False)
VERT = prove_command("DOD-1")


def equip(repo: Path) -> None:
    """Installe dans le dépôt jetable l'outillage que le parcours invoque réellement."""
    (repo / "scripts").mkdir(exist_ok=True)
    shutil.copy(ROOT / "scripts" / "paved_road_cli.py", repo / "scripts" / "paved_road_cli.py")
    (repo / "scripts" / "doctor.py").write_text(DOCTEUR)
    (repo / "Makefile").write_text(OUTILLAGE)
    commit(repo, "outillage du dépôt")


@pytest.fixture
def cli(mocker):
    """La CLI chargée par son chemin, avec `lib/` rendu aux sous-processus qu'elle lance."""
    spec = importlib.util.spec_from_file_location(
        "paved_road_cli", Path(__file__).parent.parent / "scripts" / "paved_road_cli.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    mocker.patch.dict("os.environ", {"PYTHONPATH": str(ROOT)})
    return module


def work_on(repo: Path, branch: str) -> None:
    """Ouvre une branche de travail et y committe du code, avant tout parcours."""
    attestation.git(repo, "checkout", "-q", "-b", branch)
    (repo / "web" / "chantier.py").write_text("chantier = 1\n")
    commit(repo, "travail en cours sur la branche de départ")


SANS_DISTANT = "dépôt sans aucune référence distante"
TOPOLOGIES = {
    "branche principale publiée": [],
    "branche de travail locale non publiée": ["--base", "chantier"],
    SANS_DISTANT: ["--base", "main"],
}


@pytest.fixture(params=TOPOLOGIES)
def depot(request, tmp_path):
    """Un dépôt jetable outillé, et les arguments d'ouverture, pour chaque forme de départ."""
    repo = make_repo(tmp_path / "repo")
    equip(repo)
    if request.param == SANS_DISTANT:
        attestation.git(repo, "update-ref", "-d", "refs/remotes/origin/main")
    if request.param == "branche de travail locale non publiée":
        work_on(repo, "chantier")
    attestation.git(repo, "checkout", "-q", "-b", FEATURE)
    return repo, TOPOLOGIES[request.param]


def run(cli, repo: Path, *argv: str) -> int:
    return cli.main(["--feature", FEATURE, *argv])


def write_contract(repo: Path, text: str = CONTRAT) -> None:
    path = attestation.dod_path(repo, FEATURE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def implement(repo: Path) -> None:
    """Le code qui fait passer le test — sans lui, le vert porte l'empreinte du rouge."""
    (repo / "lib" / "notification.py").write_text("son = 'ding'\n")
    commit(repo, "implémente la notification")


@pytest.fixture
def ouvert(cli, depot, mocker):
    """Un parcours ouvert sur le dépôt de la topologie, contrat écrit, validé et committé."""
    repo, opening = depot
    mocker.patch.object(cli, "REPO", repo)
    assert run(cli, repo, "start", *opening) == 0
    write_contract(repo)
    commit(repo, "contrat")
    return repo


def test_the_nominal_journey_never_refuses_a_step_whatever_the_branch_it_departs_from(cli, ouvert, capsys):
    assert run(cli, ouvert, "advance") == 0
    assert run(cli, ouvert, "advance", "--dod", "DOD-1", "--command", ROUGE, "--red") == 0
    implement(ouvert)
    assert run(cli, ouvert, "advance", "--dod", "DOD-1", "--command", VERT) == 0
    assert run(cli, ouvert, "advance") == 0
    assert run(cli, ouvert, "advance") == 0

    assert attestation.current_state(attestation.events(ouvert, FEATURE)) == "prove"
    assert attestation.verify_attestations(ouvert, FEATURE) == []
    assert "parcours démontré" in capsys.readouterr().out


def test_the_journey_answers_to_the_branch_it_departed_from_not_to_the_published_main(cli, depot, mocker):
    """Le contrôle d'antériorité jugeait un parcours sur les commits de la branche dont il part."""
    repo, opening = depot
    mocker.patch.object(cli, "REPO", repo)
    run(cli, repo, "start", *opening)
    write_contract(repo)
    commit(repo, "contrat")

    assert run(cli, repo, "advance") == 0


def test_a_green_without_any_recorded_red_is_refused(cli, ouvert, capsys):
    run(cli, ouvert, "advance")
    implement(ouvert)

    assert run(cli, ouvert, "advance", "--dod", "DOD-1", "--command", VERT) == 1
    assert "aucun rouge journalisé" in capsys.readouterr().out


def test_a_contract_committed_after_the_code_is_refused(cli, depot, mocker, capsys):
    repo, opening = depot
    mocker.patch.object(cli, "REPO", repo)
    run(cli, repo, "start", *opening)
    (repo / "web" / "app.py").write_text("x = 7\n")
    attestation.git(repo, "add", "web/app.py")
    attestation.git(repo, "commit", "-q", "-m", "code")
    write_contract(repo)
    commit(repo, "contrat")

    assert run(cli, repo, "advance") == 1
    assert "align — `dod` sort en 1" in capsys.readouterr().out


def test_a_journey_that_cannot_locate_where_it_starts_says_what_to_do(cli, tmp_path, mocker, capsys):
    """Sans référence distante ni base journalisée, le contrôle disait « conforme » au lieu de « je ne sais pas »."""
    repo = make_repo(tmp_path / "repo")
    equip(repo)
    attestation.git(repo, "update-ref", "-d", "refs/remotes/origin/main")
    attestation.git(repo, "checkout", "-q", "-b", FEATURE)
    mocker.patch.object(cli, "REPO", repo)
    run(cli, repo, "start")
    write_contract(repo)
    commit(repo, "contrat")

    assert run(cli, repo, "advance") == 1
    assert "BASE=" in capsys.readouterr().out


def test_start_leaves_the_worktree_with_the_hooks_the_journey_relies_on(cli, tmp_path, mocker, capsys):
    """Un worktree neuf n'en porte aucun : les premiers commits passaient sans lint ni tests."""
    repo = make_repo(tmp_path / "repo")
    equip(repo)
    attestation.git(repo, "checkout", "-q", "-b", FEATURE)
    mocker.patch.object(cli, "REPO", repo)
    assert attestation.missing_hooks(repo) == ["pre-commit", "pre-push"]

    run(cli, repo, "start")

    assert attestation.missing_hooks(repo) == []
    printed = capsys.readouterr().out
    assert "Environnement prêt." in printed
    assert "Docker" not in printed


UNACCEPTABLE = {
    "make test": "aucune commande de preuve admise",
    "uv run --frozen pytest --collect-only tests/": "collecte les tests sans les exécuter",
    "uv run --frozen python -c 'print(1)'": "doit exécuter un fichier du dépôt",
    "uv run --frozen python ../ailleurs/preuve.py": "est hors du dépôt",
}


@pytest.mark.parametrize(("command", "expected"), UNACCEPTABLE.items())
def test_an_unacceptable_proof_command_is_refused_on_the_red_as_on_the_green(cli, ouvert, capsys, command, expected):
    run(cli, ouvert, "advance")

    assert run(cli, ouvert, "advance", "--dod", "DOD-1", "--command", command, "--red") == 1
    assert expected in capsys.readouterr().out
    assert run(cli, ouvert, "advance", "--dod", "DOD-1", "--command", command) == 1
    assert expected in capsys.readouterr().out


def test_a_red_that_made_no_test_fail_is_refused(cli, ouvert, mocker, capsys):
    """Un `-k` qui ne désigne rien sort en 5, un fichier absent en 4 : ni l'un ni l'autre n'est un rouge."""
    run(cli, ouvert, "advance")
    mocker.patch.object(attestation, "run_command", return_value=(4, "no tests ran"))

    assert run(cli, ouvert, "advance", "--dod", "DOD-1", "--command", "uv run --frozen pytest -k dod_1", "--red") == 1
    assert "aucun test n'a échoué" in capsys.readouterr().out


def test_a_green_run_on_the_very_code_the_red_ran_against_is_refused(cli, ouvert, capsys):
    """Rien n'a été implémenté entre le rouge et le vert : le cycle n'a pas eu lieu."""
    run(cli, ouvert, "advance")
    run(cli, ouvert, "advance", "--dod", "DOD-1", "--command", ROUGE, "--red")

    assert run(cli, ouvert, "advance", "--dod", "DOD-1", "--command", VERT) == 1
    assert "le rouge et le vert portent sur le même code" in capsys.readouterr().out


def test_a_criterion_rewritten_after_validation_without_a_dated_revision_is_refused(cli, ouvert, capsys):
    write_contract(ouvert, CONTRAT.replace("Un son se fait entendre", "Un message s'affiche"))
    commit(ouvert, "contrat retouché")

    assert run(cli, ouvert, "advance") == 1
    assert "align — `dod` sort en 1" in capsys.readouterr().out


def test_the_state_never_reaches_prove_while_a_criterion_stays_undemonstrated(cli, ouvert, capsys):
    run(cli, ouvert, "advance")
    implement(ouvert)
    run(cli, ouvert, "advance")

    assert run(cli, ouvert, "advance") == 1
    assert attestation.current_state(attestation.events(ouvert, FEATURE)) == "prove"
    assert "prove — `attestations` sort en 1" in capsys.readouterr().out


def touch_interface(repo: Path) -> None:
    """Le parcours réécrit un écran : ce que le couloir hermétique ne sait pas juger."""
    (repo / "web" / "templates").mkdir(parents=True, exist_ok=True)
    (repo / "web" / "templates" / "accueil.html").write_text("<p>écran</p>\n")
    commit(repo, "réécrit l'écran d'accueil")


def demonstrated(cli, repo: Path) -> None:
    """Le cycle complet d'un critère : le rouge, le code, le vert."""
    run(cli, repo, "advance", "--dod", "DOD-1", "--command", ROUGE, "--red")
    implement(repo)
    run(cli, repo, "advance", "--dod", "DOD-1", "--command", VERT)


def test_touching_the_interface_without_a_browser_test_blocks_the_proof(cli, ouvert, capsys):
    run(cli, ouvert, "advance")
    touch_interface(ouvert)
    demonstrated(cli, ouvert)

    assert run(cli, ouvert, "check", "attestations") == 1
    assert "browser/" in capsys.readouterr().out


def test_a_browser_test_named_after_a_criterion_unblocks_the_proof(cli, ouvert):
    run(cli, ouvert, "advance")
    touch_interface(ouvert)
    (ouvert / "browser").mkdir()
    (ouvert / "browser" / "test_ecran.py").write_text("def test_dod_1_le_son_se_fait_entendre():\n    pass\n")
    commit(ouvert, "test de navigateur")
    demonstrated(cli, ouvert)

    assert run(cli, ouvert, "check", "attestations") == 0


def test_a_rebase_that_stales_every_proof_is_undone_by_one_replay(cli, ouvert):
    """Trois commits d'une branche précédente n'existaient que pour rejouer les preuves une par une."""
    run(cli, ouvert, "advance")
    demonstrated(cli, ouvert)
    (ouvert / "web" / "app.py").write_text("x = 99\n")
    commit(ouvert, "touche un chemin prouvé")
    assert run(cli, ouvert, "check", "attestations") == 1

    assert run(cli, ouvert, "reprove") == 0

    assert run(cli, ouvert, "check", "attestations") == 0
