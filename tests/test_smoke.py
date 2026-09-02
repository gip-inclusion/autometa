import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("smoke", Path(__file__).parent.parent / "scripts" / "smoke.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


DOD = """# Une fonctionnalité

## Ce qui devra marcher

DOD-1 — Quand je clique sur le bouton, alors un fichier se télécharge.

DOD-2 — Le fichier porte le titre du rapport, et l'extension `.md`.
  La suite du critère tient sur une seconde ligne.

## Sources lues

DOD-9 — cette ligne n'est pas un critère, elle est hors de la section.
"""


@pytest.mark.parametrize(
    ("changed", "expected"),
    [
        (["web/templates/rapports.html"], ["web/templates/rapports.html"]),
        (["web/static/app.css"], ["web/static/app.css"]),
        (["web/routes/reports.py"], ["web/routes/reports.py"]),
        (["lib/query.py", "web/models.py"], []),
        ([], []),
        (["docs/x.md", "web/routes/x.py"], ["web/routes/x.py"]),
    ],
)
def test_interface_changes_keeps_only_what_a_browser_could_reveal(mocker, changed, expected):
    mocker.patch.object(_module, "changed_since", return_value=changed)
    assert _module.interface_changes("main") == expected


def test_criteria_reads_the_numbered_criteria_of_the_dod(tmp_path):
    path = tmp_path / "definition-of-done.md"
    path.write_text(DOD)
    assert _module.criteria(path) == [
        "DOD-1 — Quand je clique sur le bouton, alors un fichier se télécharge.",
        "DOD-2 — Le fichier porte le titre du rapport, et l'extension `.md`. "
        "La suite du critère tient sur une seconde ligne.",
    ]


def test_criteria_is_empty_when_the_dod_is_missing(tmp_path):
    assert _module.criteria(tmp_path / "absent.md") == []


@pytest.mark.parametrize(
    ("status", "tracked", "expected"),
    [
        ("", "", []),
        ("?? paved-road/x/capture.png", "", ["paved-road/x/capture.png"]),
        (" M web/routes/reports.py", "", []),
        ("A  docs/schema.pdf", "", ["docs/schema.pdf"]),
        ("?? notes.txt", "", []),
        ("", "paved-road/x/attestations/vue.png", ["paved-road/x/attestations/vue.png"]),
        ("?? a.gif\n?? b.webm", "", ["a.gif", "b.webm"]),
    ],
)
def test_stray_captures_catches_binaries_the_public_repo_must_not_receive(mocker, status, tracked, expected):
    mocker.patch.object(_module, "git", side_effect=[status, tracked])
    assert _module.stray_captures() == expected


def test_stray_captures_scans_everything_pending_but_only_paved_road_among_tracked_files(mocker):
    """Une image déjà committée ailleurs (favicon, logo) est légitime ; sous `paved-road/`, jamais."""
    spy = mocker.patch.object(_module, "git", side_effect=["", ""])
    _module.stray_captures()
    assert [call.args for call in spy.call_args_list] == [
        ("status", "--porcelain", "-uall"),
        ("ls-files", "paved-road"),
    ]


def test_stray_captures_reads_renames_from_their_destination(mocker):
    mocker.patch.object(_module, "git", side_effect=["R  ancien.md -> capture.png", ""])
    assert _module.stray_captures() == ["capture.png"]


def test_plan_declines_when_no_interface_path_is_touched(mocker, capsys):
    mocker.patch.object(_module, "interface_changes", return_value=[])
    assert _module.plan("main", None) == 0
    assert "smoke non requis" in capsys.readouterr().out


def test_plan_opens_a_directory_outside_the_repository(mocker, tmp_path, capsys):
    mocker.patch.object(_module, "OUTPUT_ROOT", tmp_path / "cache")
    mocker.patch.object(_module, "interface_changes", return_value=["web/templates/x.html"])
    mocker.patch.object(_module, "branch", return_value="paved-road/08-smoke")
    mocker.patch.object(_module, "fingerprint", return_value="abc1234")
    mocker.patch.object(_module, "criteria", return_value=["DOD-1 — Ça marche."])

    assert _module.plan("main", None) == 0

    directory = tmp_path / "cache" / "paved-road-08-smoke" / "abc1234"
    assert directory.is_dir()
    output = capsys.readouterr().out
    assert str(directory) in output
    assert "DOD-1 — Ça marche." in output


def test_plan_refuses_a_second_pass_on_the_same_interface_state(mocker, tmp_path, capsys):
    mocker.patch.object(_module, "OUTPUT_ROOT", tmp_path / "cache")
    mocker.patch.object(_module, "interface_changes", return_value=["web/templates/x.html"])
    mocker.patch.object(_module, "branch", return_value="paved-road/08-smoke")
    mocker.patch.object(_module, "fingerprint", return_value="abc1234")
    mocker.patch.object(_module, "criteria", return_value=[])
    done = tmp_path / "cache" / "paved-road-08-smoke" / "abc1234"
    done.mkdir(parents=True)
    (done / "passe.json").write_text("{}")

    assert _module.plan("main", None) == 1
    assert "déjà" in capsys.readouterr().out


def test_verify_refuses_to_record_a_pass_that_left_an_image_behind(mocker, tmp_path, capsys):
    mocker.patch.object(_module, "stray_captures", return_value=["paved-road/x/capture.png"])
    assert _module.verify(tmp_path) == 1
    assert "capture.png" in capsys.readouterr().out
    assert not (tmp_path / "passe.json").exists()


def test_verify_records_the_pass_with_what_it_produced(mocker, tmp_path):
    mocker.patch.object(_module, "stray_captures", return_value=[])
    mocker.patch.object(_module, "branch", return_value="paved-road/08-smoke")
    mocker.patch.object(_module, "fingerprint", return_value="abc1234")
    (tmp_path / "01-accueil.png").write_bytes(b"")
    (tmp_path / "rapport.md").write_text("Ce que j'ai vu.")

    assert _module.verify(tmp_path) == 0

    recorded = json.loads((tmp_path / "passe.json").read_text())
    assert recorded == {
        "branche": "paved-road/08-smoke",
        "empreinte": "abc1234",
        "captures": ["01-accueil.png"],
    }


def test_verify_refuses_a_pass_without_a_written_report(mocker, tmp_path, capsys):
    mocker.patch.object(_module, "stray_captures", return_value=[])
    (tmp_path / "01-accueil.png").write_bytes(b"")
    assert _module.verify(tmp_path) == 1
    assert "rapport.md" in capsys.readouterr().out


def interface_note(mocker, tmp_path, changed, recorded):
    """Prépare le cache de smoke et rend la ligne que la description de PR doit porter."""
    mocker.patch.object(_module, "OUTPUT_ROOT", tmp_path / "cache")
    mocker.patch.object(_module, "interface_changes", return_value=changed)
    mocker.patch.object(_module, "branch", return_value="paved-road/08-smoke")
    mocker.patch.object(_module, "fingerprint", return_value="abc1234")
    if recorded is not None:
        directory = tmp_path / "cache" / "paved-road-08-smoke" / "abc1234"
        directory.mkdir(parents=True)
        (directory / "passe.json").write_text(json.dumps(recorded, ensure_ascii=False))
    return _module.note("main")


def test_note_says_nothing_to_signal_when_the_interface_was_left_alone(mocker, tmp_path, capsys):
    assert interface_note(mocker, tmp_path, [], None) == 0
    assert "rien à signaler" in capsys.readouterr().out


def test_note_says_the_interface_changed_without_anyone_seeing_it(mocker, tmp_path, capsys):
    """« Quinze critères démontrés » se lit « ça marche » ; en réalité quinze tests passent."""
    assert interface_note(mocker, tmp_path, ["web/templates/x.html"], None) == 0

    output = capsys.readouterr().out
    assert "Aucune passe de smoke" in output
    assert "personne n'a vu cet écran dans un navigateur" in output


def test_note_says_so_when_a_pass_was_recorded_on_this_state_of_the_interface(mocker, tmp_path, capsys):
    recorded = {"branche": "paved-road/08-smoke", "empreinte": "abc1234", "captures": ["01.png", "02.png"]}

    assert interface_note(mocker, tmp_path, ["web/templates/x.html"], recorded) == 0
    assert "2 capture(s)" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("given", "recorded", "expected"),
    [
        ("main", "chantier", "main"),
        (None, "chantier", "chantier"),
        (None, "origin/main", "origin/main"),
    ],
)
def test_the_base_falls_back_to_the_one_the_journey_recorded(mocker, given, recorded, expected):
    """Sans base explicite, `main` était supposé — faux dès qu'un parcours part d'une autre branche."""
    mocker.patch.object(_module, "branch", return_value="cdarnispro/feat/son")
    mocker.patch.object(_module.attestation, "journey_base", return_value=recorded)

    assert _module.resolved_base(given) == expected


@pytest.mark.parametrize("command", ["plan", "note"])
def test_an_unresolvable_base_says_what_to_do_instead_of_crashing(mocker, capsys, command):
    """Le contrôle d'antériorité a eu ce défaut ; `smoke.py` le portait encore."""
    mocker.patch.object(_module, "branch", return_value="cdarnispro/feat/son")
    mocker.patch.object(_module.attestation, "journey_base", return_value="n-existe-pas")
    mocker.patch.object(_module, "changed_since", return_value=None)

    code = _module.plan(None, None) if command == "plan" else _module.note(None)

    assert code == 1
    assert "n-existe-pas" in capsys.readouterr().out


def test_changed_since_reports_an_unresolvable_base_as_none(mocker):
    failed = subprocess.CompletedProcess(args=[], returncode=128, stdout="", stderr="")
    mocker.patch.object(_module.subprocess, "run", return_value=failed)

    assert _module.changed_since("n-existe-pas") is None
