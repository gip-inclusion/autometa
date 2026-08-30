"""Tests for lib/attestation.py — attestations rattachées au contenu prouvé."""

import importlib.util
from pathlib import Path

import pytest

from lib import attestation
from lib.pii import NIR_PLACEHOLDER


def make_repo(root: Path) -> Path:
    """Dépôt git jetable portant `web/`, `lib/` et `docs/`, avec un commit initial."""
    files = (
        ("web/app.py", "x = 1\n"),
        ("lib/util.py", "y = 2\n"),
        ("docs/note.md", "note\n"),
        ("outils/preuve.py", "import sys\n\nprint(f'preuve de {sys.argv[1]}')\nsys.exit(int(sys.argv[2]))\n"),
    )
    for path, content in files:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    attestation.git(root, "init", "-q", "-b", "main")
    attestation.git(root, "config", "user.email", "test@example.invalid")
    attestation.git(root, "config", "user.name", "Test")
    commit(root, "initial")
    return root


def commit(repo: Path, message: str) -> str:
    attestation.git(repo, "add", "-A")
    attestation.git(repo, "commit", "-q", "-m", message)
    return attestation.git(repo, "rev-parse", "HEAD").stdout.strip()


@pytest.fixture
def repo(tmp_path):
    return make_repo(tmp_path / "repo")


def test_fingerprints_cover_the_paths_that_exist_in_head(repo):
    recorded = attestation.fingerprints(repo, ["web", "lib", "alembic"])

    assert set(recorded) == {"web", "lib"}
    assert all(len(sha) == 40 for sha in recorded.values())


@pytest.mark.parametrize("path", ["paved-road", "paved-road/ma-feature/attestations", "paved-road/ma-feature/journal"])
def test_the_journey_own_artifacts_can_never_be_proven(repo, path):
    with pytest.raises(ValueError, match="exclus"):
        attestation.proven_paths(repo, [path])


def rewrite_history(repo: Path) -> None:
    attestation.git(repo, "commit", "-q", "--amend", "-m", "initial, reworded")


def rebase_onto_advanced_main(repo: Path) -> None:
    base = attestation.git(repo, "rev-parse", "HEAD").stdout.strip()
    attestation.git(repo, "checkout", "-q", "-b", "feature")
    (repo / "web" / "feature.py").write_text("z = 3\n")
    commit(repo, "feature work")
    attestation.git(repo, "checkout", "-q", "main")
    attestation.git(repo, "reset", "-q", "--hard", base)
    (repo / "docs" / "other.md").write_text("ailleurs\n")
    commit(repo, "docs on main")
    attestation.git(repo, "checkout", "-q", "feature")
    attestation.git(repo, "rebase", "-q", "main")


@pytest.mark.parametrize("rewrite", [rewrite_history, rebase_onto_advanced_main])
def test_rewriting_history_invalidates_no_attestation(repo, rewrite):
    if rewrite is rebase_onto_advanced_main:
        rebase_onto_advanced_main(repo)
        recorded = attestation.fingerprints(repo, ["web", "lib"])
        attestation.git(repo, "commit", "-q", "--allow-empty", "-m", "attestation rangée")
    else:
        recorded = attestation.fingerprints(repo, ["web", "lib"])
        rewrite(repo)

    assert attestation.stale_paths(repo, recorded) == []


def test_a_real_change_to_web_invalidates_the_attestations_that_prove_web(repo):
    recorded = attestation.fingerprints(repo, ["web", "lib"])

    (repo / "web" / "app.py").write_text("x = 42\n")
    commit(repo, "change web")

    assert attestation.stale_paths(repo, recorded) == ["web"]


def test_uncommitted_work_on_a_proven_path_is_reported(repo):
    (repo / "web" / "app.py").write_text("x = 3\n")
    (repo / "docs" / "note.md").write_text("autre\n")

    assert attestation.dirty_paths(repo, ["web", "lib"]) == ["web/app.py"]


DOD = """# Fonctionnalité de test

## Ce qui devra marcher

DOD-1 — Le premier critère produit un résultat observable.

DOD-2 — Le deuxième critère aussi, sur
  deux lignes.

## Questions ouvertes

Aucune.

## Validation

Validé par test@example.invalid le 2026-08-18.
"""


def prove_command(dod, ok=True):
    """Une commande de preuve admise : un fichier versionné du dépôt, pas du code écrit sur la ligne."""
    return f"uv run --frozen python outils/preuve.py {dod} {0 if ok else 1}"


PROUVE_1 = prove_command("DOD-1")
PROUVE_2 = prove_command("DOD-2")
PROUVE_1_ECHOUE = prove_command("DOD-1", ok=False)


FEATURE = "ma-feature"


@pytest.fixture
def journey(repo):
    attestation.dod_path(repo, FEATURE).parent.mkdir(parents=True)
    attestation.dod_path(repo, FEATURE).write_text(DOD)
    return repo


def test_criteria_keep_their_identifier_and_fold_continuation_lines(journey):
    parsed = attestation.criteria(attestation.dod_path(journey, FEATURE).read_text())

    assert list(parsed) == ["DOD-1", "DOD-2"]
    assert parsed["DOD-2"] == "Le deuxième critère aussi, sur deux lignes."


def test_an_attestation_survives_a_round_trip_through_markdown():
    entry = attestation.Attestation(
        dod="DOD-1",
        criterion="Le critère",
        command="pytest tests/ -k 'a or b' -q",
        exit_code=0,
        output="2 passed\nin 1.5s",
        trees={"web": "a" * 40},
        proven=True,
    )

    assert attestation.parse_attestation(attestation.render_attestation(entry)) == entry


def test_an_attestation_written_by_hand_is_read_back(tmp_path):
    handwritten = (
        "# DOD-3\n\n**Critère** — Le fichier contient le texte du rapport.\n\n"
        "**Commande** — `uv run --frozen pytest tests/test_rapports.py -q`\n\n"
        "**Code de sortie** — 0\n\n**Sortie** — `4 passed in 1.53s`\n\n"
        "**Contenu prouvé**\n\n| Chemin | Empreinte d'arbre |\n|---|---|\n"
        f"| `web` | `{'b' * 40}` |\n\n**Verdict** — démontré.\n"
    )

    entry = attestation.parse_attestation(handwritten)

    assert (entry.dod, entry.exit_code, entry.proven, entry.output) == ("DOD-3", 0, True, "4 passed in 1.53s")
    assert entry.trees == {"web": "b" * 40}


def test_the_journal_is_a_directory_where_one_event_is_one_file(journey):
    for index in range(3):
        attestation.append_event(journey, FEATURE, "advance", [("État", "align"), ("Détail", str(index))])

    files = sorted(attestation.journal_dir(journey, FEATURE).glob("*.md"))

    assert len(files) == 3
    assert [event["Détail"] for event in attestation.events(journey, FEATURE)] == ["0", "1", "2"]


def test_a_rebase_leaves_the_journal_untouched(journey):
    attestation.append_event(journey, FEATURE, "advance", [("État", "build"), ("Résultat", "succès")])
    commit(journey, "journal")
    before = sorted(path.name for path in attestation.journal_dir(journey, FEATURE).glob("*.md"))

    rewrite_history(journey)

    assert sorted(path.name for path in attestation.journal_dir(journey, FEATURE).glob("*.md")) == before
    assert attestation.current_state(attestation.events(journey, FEATURE)) == "build"


@pytest.mark.parametrize(
    ("journal", "expected"),
    [
        ([], "align"),
        ([{"État": "build", "Résultat": "succès"}], "build"),
        ([{"État": "build", "Résultat": "échec"}], "align"),
        ([{"État": "build", "Résultat": "succès"}, {"État": "prove", "Résultat": "échec"}], "build"),
    ],
)
def test_the_state_comes_from_the_successes_recorded_in_the_journal(journal, expected):
    assert attestation.current_state(journal) == expected


@pytest.mark.parametrize(
    ("journal", "expected"),
    [
        ([], 0),
        ([{"Résultat": "échec", "Famille": "A"}], 1),
        ([{"Résultat": "échec", "Famille": "A"}] * 3, 3),
        ([{"Résultat": "échec", "Famille": "A"}, {"Résultat": "échec", "Famille": "B"}], 0),
        ([{"Résultat": "échec", "Famille": "A"}, {"Résultat": "succès"}], 0),
    ],
)
def test_repairable_failures_are_counted_from_the_last_success(journal, expected):
    assert attestation.consecutive_repairable(journal) == expected


def check(name, family, argv):
    return attestation.Check(name, family, argv)


def test_advance_moves_on_when_every_check_exits_zero(journey, mocker):
    mocker.patch.object(attestation, "CHECKS", {"align": (check("dod", "A", ("true",)),)})

    moved, message = attestation.advance(journey, FEATURE)

    assert moved and message == "align → build."
    assert attestation.current_state(attestation.events(journey, FEATURE)) == "build"


def test_advance_refuses_to_progress_without_a_zero_exit_code(journey, mocker):
    mocker.patch.object(attestation, "CHECKS", {"align": (check("dod", "A", ("false",)),)})

    moved, message = attestation.advance(journey, FEATURE)

    assert not moved and "Famille A" in message
    assert attestation.current_state(attestation.events(journey, FEATURE)) == "align"


@pytest.mark.parametrize(("family", "expected_counter"), [("A", "1"), ("B", "0"), ("C", "0"), ("D", "0")])
def test_a_failing_check_records_the_family_that_commands_what_follows(journey, mocker, family, expected_counter):
    mocker.patch.object(attestation, "CHECKS", {"align": (check("env", family, ("false",)),)})

    attestation.advance(journey, FEATURE)

    recorded = attestation.events(journey, FEATURE)[-1]
    assert recorded["Famille"] == family
    assert recorded["Réponse"] == attestation.FAMILIES[family]
    assert recorded["Échecs A consécutifs"] == expected_counter


def test_the_repairable_counter_is_recorded_without_ever_blocking(journey, mocker):
    mocker.patch.object(attestation, "CHECKS", {"align": (check("dod", "A", ("false",)),)})

    for _ in range(5):
        attestation.advance(journey, FEATURE)

    assert [event["Échecs A consécutifs"] for event in attestation.events(journey, FEATURE)] == list("12345")


def test_proving_a_criterion_records_the_command_its_exit_code_and_the_content(journey):
    entry = prove_cycle(journey, "DOD-1")[0]

    assert (entry.exit_code, entry.proven, entry.output) == (0, True, "preuve de DOD-1")
    assert entry.trees == attestation.fingerprints(journey, ["web", "lib"])
    filed = attestation.parse_attestation((attestation.attestations_dir(journey, FEATURE) / "DOD-1.md").read_text())
    assert filed == entry


def test_a_failing_command_is_attested_as_not_demonstrated(journey):
    entry = attestation.prove(journey, FEATURE, "DOD-1", PROUVE_1_ECHOUE)

    assert not entry.proven
    assert "DOD-1 — non démontré" in " ".join(attestation.verify_attestations(journey, FEATURE))


def test_proving_uncommitted_code_is_refused_because_the_fingerprint_would_not_describe_it(journey):
    (journey / "web" / "app.py").write_text("x = 99\n")

    with pytest.raises(ValueError, match="Committer d'abord"):
        attestation.prove(journey, FEATURE, "DOD-1", PROUVE_1)


def test_changing_web_invalidates_the_attestation_that_proved_web(journey):
    prove_cycle(journey, "DOD-1", "DOD-2")

    (journey / "web" / "app.py").write_text("x = 99\n")
    commit(journey, "change web")

    problems = attestation.verify_attestations(journey, FEATURE)
    assert [problem.split(" —")[0] for problem in problems] == ["DOD-1", "DOD-2"]
    assert all("périmée, web a changé" in problem for problem in problems)


@pytest.mark.parametrize(
    ("dod", "expected"),
    [("DOD-1", "DOD-2 — non démontré : aucune attestation."), ("DOD-2", "DOD-1 — non démontré : aucune attestation.")],
)
def test_a_criterion_without_attestation_cannot_hide_in_a_global_report(journey, dod, expected):
    prove_cycle(journey, dod)

    assert attestation.verify_attestations(journey, FEATURE) == [expected]


def test_an_attestation_without_a_matching_criterion_is_reported(journey):
    prove_cycle(journey, "DOD-1", "DOD-2")
    (attestation.attestations_dir(journey, FEATURE) / "DOD-9.md").write_text("# DOD-9\n\n**Verdict** — démontré.\n")

    assert attestation.verify_attestations(journey, FEATURE) == ["DOD-9 — attestation sans critère correspondant."]


@pytest.mark.parametrize(
    ("filename", "content", "expected"),
    [
        ("capture.png", b"\x89PNG\r\n\x1a\n", "seul du markdown"),
        ("DOD-1.md", b"\xff\xfe\x00binaire", "contenu binaire"),
        ("DOD-1.md", "![capture](../captures/ecran.png)".encode(), "image ou contenu encodé"),
        ("DOD-1.md", b"data:image/png;base64,iVBORw0KGgo=", "image ou contenu encodé"),
        ("DOD-1.md", b"x" * (attestation.MAX_ATTESTATION_BYTES + 1), "il ne stocke pas"),
    ],
)
def test_the_public_repository_refuses_anything_advance_did_not_produce(journey, filename, content, expected):
    directory = attestation.attestations_dir(journey, FEATURE)
    directory.mkdir(parents=True)
    (directory / filename).write_bytes(content)

    problems = attestation.verify_content(journey)

    assert len(problems) == 1 and expected in problems[0]


def test_a_plain_attestation_passes_the_content_check(journey):
    prove_cycle(journey, "DOD-1")

    assert attestation.verify_content(journey) == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2 passed in 1.5s", "2 passed in 1.5s"),
        ("assert nir == 1 80 01 75 107 068 55", f"assert nir == {NIR_PLACEHOLDER}"),
    ],
)
def test_output_is_bounded_and_stripped_of_personal_identifiers(text, expected):
    assert attestation.truncate(text) == expected


def test_a_long_output_keeps_its_end_where_the_verdict_sits():
    truncated = attestation.truncate("bruit\n" * 5000 + "2 passed in 1.5s")

    assert truncated.startswith("…")
    assert truncated.endswith("2 passed in 1.5s")
    assert len(truncated) == attestation.OUTPUT_LIMIT + 2


@pytest.fixture
def cli(journey, mocker):
    spec = importlib.util.spec_from_file_location(
        "paved_road_cli", Path(__file__).parent.parent / "scripts" / "paved_road_cli.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    mocker.patch.object(module, "REPO", journey)
    return module


def test_start_opens_the_journey_with_a_definition_of_done_to_write(cli, journey, capsys):
    attestation.dod_path(journey, "neuve").parent.mkdir(parents=True, exist_ok=True)

    assert cli.main(["--feature", "neuve", "start"]) == 0
    assert "DOD-1 —" in attestation.dod_path(journey, "neuve").read_text()
    assert "état align" in capsys.readouterr().out


def test_start_never_overwrites_a_validated_definition_of_done(cli, journey):
    cli.main(["--feature", FEATURE, "start"])

    assert attestation.dod_path(journey, FEATURE).read_text() == DOD


def test_status_names_every_criterion_and_its_verdict(cli, journey, capsys):
    prove_cycle(journey, "DOD-1")

    assert cli.main(["--feature", FEATURE, "status"]) == 0

    out = capsys.readouterr().out
    assert "DOD-1 — démontré" in out and "DOD-2 — non démontré" in out


@pytest.mark.parametrize(("which", "expected"), [("content", 0), ("attestations", 1), ("dod", 0)])
def test_each_check_is_invocable_on_its_own_and_exits_with_its_verdict(cli, journey, which, expected):
    assert cli.main(["--feature", FEATURE, "check", which]) == expected


def test_advance_on_a_criterion_requires_the_command_that_demonstrates_it(cli):
    with pytest.raises(SystemExit):
        cli.main(["--feature", FEATURE, "advance", "--dod", "DOD-1"])


def test_advance_reports_uncommitted_code_as_a_repairable_failure(cli, journey, capsys):
    (journey / "web" / "app.py").write_text("x = 99\n")

    assert cli.main(["--feature", FEATURE, "advance", "--dod", "DOD-1", "--command", PROUVE_1]) == 1
    assert "Famille A" in capsys.readouterr().out


def test_the_feature_directory_is_named_after_the_branch_prefix_removed(repo):
    attestation.git(repo, "checkout", "-q", "-b", "paved-road/05-attestation")

    assert attestation.slug(repo) == "05-attestation"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("# Vide\n\n## Questions ouvertes\n\n## Validation\n", "Aucun critère"),
        ("# Sans section\n\nDOD-1 — Un critère.\n", "Section « Questions ouvertes » absente."),
        ("# Doublon\n\nDOD-1 — Un.\n\nDOD-1 — Deux.\n\n## Questions ouvertes\n\n## Validation\n", "double : DOD-1"),
    ],
)
def test_a_malformed_definition_of_done_is_named_line_by_line(journey, text, expected):
    attestation.dod_path(journey, FEATURE).write_text(text)

    assert any(expected in problem for problem in attestation.verify_dod(journey, FEATURE))


def test_a_missing_definition_of_done_is_the_first_thing_reported(journey):
    assert attestation.verify_dod(journey, "inconnue") == [
        f"Definition of done absente : {attestation.dod_path(journey, 'inconnue')}"
    ]


def test_an_attestation_proving_no_content_is_refused(journey):
    prove_cycle(journey, "DOD-1", "DOD-2")
    target = attestation.attestations_dir(journey, FEATURE) / "DOD-1.md"
    target.write_text(attestation.TREE_ROW.sub("", target.read_text()))

    assert attestation.verify_attestations(journey, FEATURE) == [
        "DOD-1 — attestation sans empreinte : elle ne prouve aucun contenu."
    ]


def test_proving_an_unknown_criterion_is_refused(journey):
    with pytest.raises(ValueError, match="DOD-9 ne figure pas"):
        attestation.prove(journey, FEATURE, "DOD-9", prove_command("DOD-9"))


def test_status_says_so_when_no_definition_of_done_exists_yet(cli, journey, capsys):
    assert cli.main(["--feature", "inconnue", "status"]) == 0
    assert "Aucune definition of done" in capsys.readouterr().out


@pytest.mark.parametrize(("argv", "expected"), [(("true",), 0), (("false",), 1)])
def test_checks_report_every_check_of_the_current_state(cli, journey, mocker, capsys, argv, expected):
    mocker.patch.object(attestation, "CHECKS", {"align": (check("dod", "A", argv),)})

    assert cli.main(["--feature", FEATURE, "check"]) == expected
    assert "dod (famille A)" in capsys.readouterr().out


def test_advance_through_the_cli_files_the_attestation_and_moves_the_state(cli, journey, mocker, capsys):
    assert cli.main(["--feature", FEATURE, "advance", "--dod", "DOD-1", "--red", "--command", PROUVE_1_ECHOUE]) == 0
    implement(journey)

    assert cli.main(["--feature", FEATURE, "advance", "--dod", "DOD-1", "--command", PROUVE_1]) == 0
    assert "DOD-1 — démontré" in capsys.readouterr().out

    mocker.patch.object(attestation, "CHECKS", {"align": (check("dod", "A", ("true",)),)})

    assert cli.main(["--feature", FEATURE, "advance"]) == 0
    assert "align → build." in capsys.readouterr().out


def test_the_untouched_template_is_not_a_definition_of_done(cli, journey):
    cli.main(["--feature", "gabarit", "start"])

    problems = attestation.verify_dod(journey, "gabarit")

    assert [problem for problem in problems if problem.startswith("Gabarit non rempli")]
    assert all(problem.startswith(("Gabarit non rempli", "Validation")) for problem in problems)


def validated(mention: str) -> str:
    """La definition of done de test, dont la seule ligne de validation change."""
    return DOD.replace("Validé par test@example.invalid le 2026-08-18.", mention)


@pytest.mark.parametrize(
    ("mention", "accepte"),
    [
        ("Validé par test@example.invalid le 2026-08-18.", True),
        ("Validé par Paul le 2026-08-18", True),
        ("", False),
        ("À valider.", False),
        ("Validé par Paul.", False),
        ("Validé le 2026-08-18.", False),
        ("Validé par Paul le 18/08/2026.", False),
    ],
)
def test_a_validation_section_without_who_and_when_is_not_a_validation(journey, mention, accepte):
    """Seul le titre de section était exigé : son contenu pouvait rester vide."""
    attestation.dod_path(journey, FEATURE).write_text(validated(mention))

    problems = [p for p in attestation.verify_dod(journey, FEATURE) if p.startswith("Validation")]

    assert (problems == []) is accepte


@pytest.mark.parametrize(
    ("command", "attendu"),
    [
        ("uv run --frozen pytest tests/test_x.py -k dod_1", []),
        ("uv run --frozen pytest tests/test_x.py::test_dod_1_rapport", []),
        ("uv run --frozen alembic check", []),
        ("uv run --frozen python outils/preuve.py DOD-1 0", []),
        ("uv run --frozen python scripts/absent.py", ["n'est pas suivi par git"]),
        ("uv run --frozen python /tmp/dehors.py", ["hors du dépôt"]),
        ("uv run --frozen pytest ../ailleurs/test_x.py -k dod_1", ["hors du dépôt"]),
        ("uv run --frozen pytest -c /tmp/pytest.ini -k dod_1", ["hors du dépôt", "détourne la collecte"]),
        ("uv run --frozen pytest -p mon_plugin -k dod_1", ["détourne la collecte"]),
        ("uv run --frozen pytest --deselect tests/x.py::test_dod_1 -k dod_1", ["détourne la collecte"]),
        ('uv run --frozen pytest tests/ -k "not dod_1"', ["ne désigne aucun test nommé d'après"]),
        ("uv run --frozen pytest tests/ -k dod_11", ["ne désigne aucun test nommé d'après"]),
        ("uv run --frozen pytest tests/ --junitxml=/tmp/a::dod_1.xml", ["hors du dépôt", "ne désigne aucun test"]),
        ('uv run --frozen python "pas_ferme.py', ["illisible"]),
        ("uv run --frozen alembic -x db_url=postgresql://u:secret@h/db upgrade head", ["identifiants en clair"]),
        ("make test", ["ne commence par aucune commande de preuve admise"]),
        ("make help", ["ne commence par aucune commande de preuve admise"]),
        ("echo bonjour", ["ne commence par aucune commande de preuve admise"]),
        ("false", ["ne commence par aucune commande de preuve admise"]),
        ("rm -rf /", ["ne commence par aucune commande de preuve admise", "hors du dépôt"]),
        ("uv run --frozen pytest tests/ --collect-only -k dod_1", ["collecte les tests sans les exécuter"]),
        ("uv run --frozen pytest tests/ --co -k dod_1", ["collecte les tests sans les exécuter"]),
        ('uv run --frozen python -c "pass"', ["exécuter un fichier du dépôt"]),
        ("uv run --frozen python --version", ["exécuter un fichier du dépôt"]),
        ("uv run --frozen python", ["exécuter un fichier du dépôt"]),
        ("uv run --frozen python -m pytest -k dod_1", ["exécuter un fichier du dépôt"]),
        ("uv run --frozen pytest tests/test_health.py", ["ne désigne aucun test nommé d'après"]),
        ("uv run --frozen pytest tests/ --junitxml=/tmp/dod-1.xml", ["hors du dépôt", "ne désigne aucun test"]),
        ("uv run --frozen pytest tests/ -k dod_1\nrm -rf /", ["tient sur une ligne", "hors du dépôt"]),
    ],
)
def test_command_refusals(repo, command, attendu):
    refusals = attestation.command_refusals(command, "DOD-1", repo)

    assert len(refusals) == len(attendu)
    for refus, motif in zip(refusals, attendu, strict=True):
        assert motif in refus


@pytest.mark.parametrize(
    ("sortie", "leve"),
    [
        # Sortie réelle de `pytest -k <motif inexistant>` : code 0, et pas un test exécuté.
        ("2129 deselected, 1 warning in 3.42s", True),
        ("no tests ran in 0.01s", True),
        ("1 passed, 2128 deselected in 3.50s", False),
    ],
)
def test_a_pytest_that_runs_no_test_is_refused_even_when_it_exits_zero(journey, mocker, sortie, leve):
    """Un `-k` qui ne désigne rien sort en 0 : sans cette garde, le critère serait « démontré »."""
    attestation.record_red(journey, FEATURE, "DOD-1", prove_command("DOD-1", ok=False))
    implement(journey)
    mocker.patch.object(attestation, "run_command", return_value=(0, sortie))
    commande = "uv run --frozen pytest tests/ -k dod_1"

    if leve:
        with pytest.raises(ValueError, match="aucun test n'ait tourné"):
            attestation.prove(journey, FEATURE, "DOD-1", commande)
    else:
        assert attestation.prove(journey, FEATURE, "DOD-1", commande).proven


@pytest.mark.parametrize(("proven", "attendu"), [(True, "démontré."), (False, "non démontré.")])
def test_a_criterion_carries_one_verdict_and_only_one(proven, attendu):
    """Aucune mention ne nuance plus le verdict : rien ne rejoue les preuves, donc rien n'en dispense."""
    entry = attestation.Attestation(dod="DOD-1", criterion="…", command="…", exit_code=0, output="", proven=proven)

    assert attestation.verdict(entry) == attendu
    assert attestation.parse_attestation(attestation.render_attestation(entry)) == entry


def test_skills_is_fingerprinted():
    """Sans lui, réécrire un SKILL.md après coup ne périmerait aucune preuve."""
    assert "skills" in attestation.DEFAULT_PROVEN_PATHS


@pytest.mark.parametrize(
    ("variable", "valeur"),
    [("GIT_DIR", ".git"), ("GIT_WORK_TREE", ""), ("GIT_INDEX_FILE", ".git/index")],
)
def test_git_ignores_what_a_hook_put_in_the_environment(repo, tmp_path, monkeypatch, variable, valeur):
    """Un hook git exporte GIT_DIR : sans l'écarter, les tests committaient dans le vrai dépôt."""
    ailleurs = make_repo(tmp_path / "ailleurs")
    monkeypatch.setenv(variable, str(ailleurs / valeur) if valeur else str(ailleurs))
    (repo / "web" / "nouveau.py").write_text("n = 1\n")

    commit(repo, "dans le dépôt jetable")

    assert attestation.git(repo, "log", "-1", "--format=%s").stdout.strip() == "dans le dépôt jetable"
    assert attestation.git(ailleurs, "log", "-1", "--format=%s").stdout.strip() == "initial"


def test_git_env_strips_only_the_git_variables(monkeypatch):
    monkeypatch.setenv("GIT_DIR", "/ailleurs/.git")
    monkeypatch.setenv("PATH", "/usr/bin")

    env = attestation.git_env()

    assert "GIT_DIR" not in env
    assert env["PATH"] == "/usr/bin"


@pytest.mark.parametrize(
    ("chemin", "refuse"),
    [
        ("attestations/DOD-1.md", False),
        ("retro.md", False),
        ("relectures/design-coherence.md", False),
        ("retro.pdf", True),
        ("relectures/capture.png", True),
        ("journal/export.csv", True),
    ],
)
def test_verify_content_couvre_tout_le_parcours_pas_seulement_les_attestations(journey, chemin, refuse):
    """La rétro et les relectures citent l'usage réel, sur un dépôt public."""
    cible = attestation.feature_dir(journey, FEATURE) / chemin
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text("texte")

    problems = attestation.verify_content(journey)

    assert any(chemin in problem for problem in problems) is refuse


@pytest.fixture
def branche(journey):
    """Une branche de parcours partant de `main`, sur laquelle la definition of done est committée."""
    attestation.git(journey, "checkout", "-q", "-b", FEATURE)
    return journey


def commit_code_alone(repo: Path) -> None:
    """Committe une modification de `web/` sans emporter la definition of done."""
    (repo / "web" / "app.py").write_text("x = 7\n")
    attestation.git(repo, "add", "web/app.py")
    attestation.git(repo, "commit", "-q", "-m", "code")


def test_a_contract_committed_before_any_code_raises_nothing(branche):
    commit(branche, "contrat")
    commit_code_alone(branche)

    assert attestation.dod_antedates_code(branche, FEATURE, "main") == []


def test_code_committed_before_the_contract_is_refused(branche):
    commit_code_alone(branche)
    commit(branche, "contrat")

    problems = attestation.dod_antedates_code(branche, FEATURE, "main")

    assert len(problems) == 1
    assert "réécriture d'historique" in problems[0]


def test_code_committed_while_the_contract_stays_uncommitted_is_refused(branche):
    commit_code_alone(branche)

    assert len(attestation.dod_antedates_code(branche, FEATURE, "main")) == 1


@pytest.mark.parametrize("base", ["origin/main", "n-existe-pas"])
def test_an_unreachable_base_leaves_the_anteriority_unchecked(branche, base):
    """Sans base, la fenêtre du parcours est indéterminable : le contrôle ne peut pas s'exercer."""
    commit_code_alone(branche)

    assert attestation.dod_antedates_code(branche, FEATURE, base) == []


def test_verify_dod_carries_the_anteriority_check(branche):
    commit_code_alone(branche)
    commit(branche, "contrat")

    assert any("réécriture d'historique" in problem for problem in attestation.verify_dod(branche, FEATURE, "main"))


def test_the_dod_check_takes_the_base_that_delimits_the_journey(cli, branche, capsys):
    commit_code_alone(branche)
    commit(branche, "contrat")

    assert cli.main(["--feature", FEATURE, "check", "dod", "--base", "main"]) == 1
    assert "réécriture d'historique" in capsys.readouterr().out


def test_an_attestation_whose_command_became_unacceptable_is_reported(journey):
    """Les refus ne servaient qu'à l'écriture : une attestation ancienne ou écrite à la main y échappait."""
    prove_cycle(journey, "DOD-1", "DOD-2")
    target = attestation.attestations_dir(journey, FEATURE) / "DOD-1.md"
    target.write_text(target.read_text().replace(prove_command("DOD-1"), "make test"))

    problems = attestation.verify_attestations(journey, FEATURE)

    assert len(problems) == 1
    assert "DOD-1 — commande de preuve irrecevable" in problems[0]


def test_the_command_line_cannot_narrow_the_proven_scope(cli):
    """`PATHS=tests` rangeait une attestation n'engageant que `tests/` : tout `web/` restait réécrivable."""
    with pytest.raises(SystemExit):
        cli.main(["--feature", FEATURE, "advance", "--dod", "DOD-1", "--command", PROUVE_1, "--paths", "tests"])

    assert cli.main(["--feature", FEATURE, "advance", "--dod", "DOD-1", "--red", "--command", PROUVE_1_ECHOUE]) == 0


def test_a_proof_always_covers_the_whole_scope_present_in_the_repository(journey):
    (journey / "tests").mkdir()
    (journey / "tests" / "test_x.py").write_text("def test_x():\n    assert 1 == 1\n")
    commit(journey, "ajoute tests/")

    entry = prove_cycle(journey, "DOD-1")[0]

    assert set(entry.trees) == {"web", "lib", "tests"}


def implement(repo: Path) -> None:
    """Écrit et committe du code sous un chemin prouvé — sans lui, l'empreinte du vert est celle du rouge."""
    (repo / "lib" / "implementation.py").write_text("valeur = 1\n")
    commit(repo, "implémente")


def prove_cycle(repo: Path, *dods: str) -> list[attestation.Attestation]:
    """Le cycle complet : le rouge de chaque critère, le code écrit, puis les verts."""
    for dod in dods:
        attestation.record_red(repo, FEATURE, dod, prove_command(dod, ok=False))
    implement(repo)
    return [attestation.prove(repo, FEATURE, dod, prove_command(dod)) for dod in dods]


def test_a_red_that_exits_zero_is_not_a_red(journey):
    """Un test qui passe avant que le code existe ne démontre rien du cycle."""
    with pytest.raises(ValueError, match="sort en 0"):
        attestation.record_red(journey, FEATURE, "DOD-1", prove_command("DOD-1"))


def test_a_red_records_the_fingerprint_of_the_code_it_was_run_against(journey):
    """L'empreinte doit être celle d'avant l'implémentation, sinon elle ne distingue rien."""
    avant = attestation.scope_fingerprint(journey)

    attestation.record_red(journey, FEATURE, "DOD-1", prove_command("DOD-1", ok=False))
    implement(journey)

    recorded = attestation.events(journey, FEATURE)[-1]
    assert (recorded["Résultat"], recorded["Critère"]) == ("rouge", "DOD-1")
    assert recorded["Empreinte du périmètre"] == avant != attestation.scope_fingerprint(journey)


def test_a_red_is_journaled_on_an_uncommitted_working_tree(journey):
    """Le test rouge ne se commit pas : on l'écrit, on le voit échouer, on code, et on commit le tout."""
    (journey / "web" / "app.py").write_text("x = 99\n")

    code, _ = attestation.record_red(journey, FEATURE, "DOD-1", prove_command("DOD-1", ok=False))

    assert code != 0
    assert [event["Critère"] for event in attestation.reds(journey, FEATURE, "DOD-1")] == ["DOD-1"]


def test_a_green_still_needs_a_clean_tree(journey):
    """Le vert, lui, inscrit une empreinte : elle ne décrirait pas un travail non committé."""
    attestation.record_red(journey, FEATURE, "DOD-1", prove_command("DOD-1", ok=False))
    (journey / "web" / "app.py").write_text("x = 99\n")

    with pytest.raises(ValueError, match="Committer d'abord"):
        attestation.prove(journey, FEATURE, "DOD-1", prove_command("DOD-1"))


def test_a_green_without_any_recorded_red_is_refused(journey):
    with pytest.raises(ValueError, match="aucun rouge journalisé"):
        attestation.prove(journey, FEATURE, "DOD-1", prove_command("DOD-1"))


def test_a_green_on_the_very_code_the_red_ran_against_is_refused(journey):
    """Rien n'a été implémenté entre les deux : le cycle n'a pas eu lieu."""
    attestation.record_red(journey, FEATURE, "DOD-1", prove_command("DOD-1", ok=False))

    with pytest.raises(ValueError, match="même code"):
        attestation.prove(journey, FEATURE, "DOD-1", prove_command("DOD-1"))


def test_the_full_cycle_is_accepted(journey):
    entry = prove_cycle(journey, "DOD-1")[0]

    assert entry.proven
    assert attestation.verify_attestations(journey, FEATURE) == ["DOD-2 — non démontré : aucune attestation."]


def test_a_red_the_command_of_which_is_unacceptable_is_refused(journey):
    with pytest.raises(ValueError, match="ne commence par aucune commande de preuve admise"):
        attestation.record_red(journey, FEATURE, "DOD-1", "make test")


def test_a_failing_command_is_still_attested_without_any_red(journey):
    """La garde porte sur le vert : un critère non démontré se range comme avant."""
    assert not attestation.prove(journey, FEATURE, "DOD-1", prove_command("DOD-1", ok=False)).proven


def test_the_cli_records_a_red(cli, journey, capsys):
    assert cli.main(["--feature", FEATURE, "advance", "--dod", "DOD-1", "--red", "--command", PROUVE_1_ECHOUE]) == 0
    assert "DOD-1 — rouge" in capsys.readouterr().out

    implement(journey)

    assert cli.main(["--feature", FEATURE, "advance", "--dod", "DOD-1", "--command", PROUVE_1]) == 0


def test_the_cli_reports_a_green_without_red_as_a_repairable_failure(cli, journey, capsys):
    assert cli.main(["--feature", FEATURE, "advance", "--dod", "DOD-1", "--command", PROUVE_1]) == 1

    out = capsys.readouterr().out
    assert "aucun rouge journalisé" in out and "Famille A" in out


@pytest.fixture
def contrat(branche):
    """Une definition of done validée et committée — l'état à partir duquel toute retouche se compare."""
    commit(branche, "contrat")
    return branche


ORIGINAL = "DOD-1 — Le premier critère produit un résultat observable."


def test_an_untouched_contract_raises_nothing(contrat):
    assert attestation.frozen_criteria(contrat, FEATURE) == []


def test_a_criterion_rewritten_after_validation_without_a_dated_revision_is_refused(contrat):
    """C'est la règle qui empêche de rétrécir la cible jusqu'à ce que le vert soit atteignable."""
    path = attestation.dod_path(contrat, FEATURE)
    path.write_text(path.read_text().replace(ORIGINAL, "DOD-1 — Le premier critère produit moins."))

    problems = attestation.frozen_criteria(contrat, FEATURE)

    assert len(problems) == 1
    assert "DOD-1 a changé depuis la validation sans porter de révision" in problems[0]


def test_a_dated_revision_under_the_criterion_makes_the_rewrite_acceptable(contrat):
    path = attestation.dod_path(contrat, FEATURE)
    revise = "DOD-1 — Le premier critère produit moins.\nRévision 2026-08-30 — la cible change, et voici pourquoi."
    path.write_text(path.read_text().replace(ORIGINAL, revise))

    assert attestation.frozen_criteria(contrat, FEATURE) == []


def test_a_criterion_deleted_after_validation_is_refused(contrat):
    path = attestation.dod_path(contrat, FEATURE)
    path.write_text(path.read_text().replace("DOD-2 — Le deuxième critère aussi, sur\n  deux lignes.\n", ""))

    problems = attestation.frozen_criteria(contrat, FEATURE)

    assert len(problems) == 1
    assert "DOD-2 a disparu" in problems[0]


def test_a_criterion_added_after_validation_carries_its_revision_too(contrat):
    path = attestation.dod_path(contrat, FEATURE)
    path.write_text(path.read_text().replace(ORIGINAL, f"{ORIGINAL}\n\nDOD-3 — Un critère de plus."))

    assert ["DOD-3" in problem for problem in attestation.frozen_criteria(contrat, FEATURE)] == [True]


def test_a_contract_never_validated_in_history_is_not_frozen(journey):
    assert attestation.frozen_criteria(journey, FEATURE) == []


def test_verify_dod_carries_the_immutability_of_a_validated_contract(contrat):
    path = attestation.dod_path(contrat, FEATURE)
    path.write_text(path.read_text().replace(ORIGINAL, "DOD-1 — Le premier critère produit moins."))

    assert any("sans porter de révision" in problem for problem in attestation.verify_dod(contrat, FEATURE, "main"))


PYTEST_SANS_ECHEC = "2307 deselected, 1 warning in 3.46s"


@pytest.mark.parametrize(
    ("sortie", "code", "leve"),
    [
        (PYTEST_SANS_ECHEC, 5, True),
        ("ERROR: file or directory not found: tests/absent.py", 4, True),
        ("1 failed, 2 passed in 0.50s", 1, False),
        ("1 error in 0.05s", 2, False),
    ],
)
def test_a_red_that_made_no_test_fail_is_refused(journey, mocker, sortie, code, leve):
    """Un `-k` qui ne désigne rien sort en 5 : sans cette garde, on obtient un rouge sans avoir écrit de test."""
    mocker.patch.object(attestation, "run_command", return_value=(code, sortie))
    commande = "uv run --frozen pytest tests/test_x.py -k dod_1"

    if leve:
        with pytest.raises(ValueError, match="aucun test n'a échoué"):
            attestation.record_red(journey, FEATURE, "DOD-1", commande)
    else:
        assert attestation.record_red(journey, FEATURE, "DOD-1", commande)[0] == code


def test_a_contract_committed_before_the_fork_point_raises_nothing(journey):
    """Une branche qui part d'une base portant déjà le contrat n'a rien committé avant lui."""
    commit(journey, "contrat sur main")
    attestation.git(journey, "checkout", "-q", "-b", FEATURE)
    commit_code_alone(journey)

    assert attestation.dod_antedates_code(journey, FEATURE, "main") == []


def test_an_attestation_whose_command_is_unparsable_is_reported_not_crashed(journey):
    prove_cycle(journey, "DOD-1", "DOD-2")
    target = attestation.attestations_dir(journey, FEATURE) / "DOD-1.md"
    target.write_text(target.read_text().replace(prove_command("DOD-1"), 'uv run --frozen python "pas_ferme.py'))

    problems = attestation.verify_attestations(journey, FEATURE)

    assert len(problems) == 1
    assert "DOD-1" in problems[0] and "illisible" in problems[0]


def test_an_attestation_that_drops_a_proven_path_is_reported(journey):
    """Retirer une ligne du tableau d'empreintes rendait tout `web/` réécrivable sans périmer la preuve."""
    prove_cycle(journey, "DOD-1", "DOD-2")
    target = attestation.attestations_dir(journey, FEATURE) / "DOD-1.md"
    kept = [line for line in target.read_text().splitlines(True) if not line.startswith("| `web`")]
    target.write_text("".join(kept))

    problems = attestation.verify_attestations(journey, FEATURE)

    assert len(problems) == 1
    assert "DOD-1 — attestation partielle : web" in problems[0]
