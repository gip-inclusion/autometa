"""Les scripts des skills create_dashboard et update_dashboard : options des déclinaisons."""

import importlib.util
import json
from pathlib import Path

import pytest

SKILLS = Path(__file__).parent.parent / "skills"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_cli", SKILLS / name / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def runtime(monkeypatch):
    monkeypatch.setenv("AUTOMETA_CONVERSATION_ID", "conv-1")
    monkeypatch.setenv("AUTOMETA_USER_EMAIL", "bob@x")


def _run(module, argv, monkeypatch):
    monkeypatch.setattr("sys.argv", ["x", *argv])
    module.main()


def _updated(mocker, cli):
    return mocker.patch.object(
        cli,
        "update_dashboard",
        return_value=mocker.Mock(slug="multi", originating_user_email="a@x", updater_email="bob@x", fields_changed=[]),
    )


def test_dod_7_add_variant_declares_key_and_label(runtime, monkeypatch, mocker, capsys):
    cli = _load("update_dashboard")
    _updated(mocker, cli)
    add = mocker.patch.object(cli, "add_variant", return_value={"key": "67", "label": "Bas-Rhin", "token": "t"})
    mocker.patch.object(cli, "list_variants", side_effect=[[], [{"key": "67", "label": "Bas-Rhin", "token": "t"}]])

    _run(cli, ["--slug", "multi", "--add-variant", "67=Bas-Rhin"], monkeypatch)

    add.assert_called_once_with("multi", "67", "Bas-Rhin")
    out = json.loads(capsys.readouterr().out)
    assert out["variants"] == [{"key": "67", "label": "Bas-Rhin", "token": "t"}]


def test_dod_7_remove_variant_by_key(runtime, monkeypatch, mocker, capsys):
    cli = _load("update_dashboard")
    _updated(mocker, cli)
    remove = mocker.patch.object(cli, "remove_variant", return_value=True)
    mocker.patch.object(cli, "list_variants", return_value=[])
    mocker.patch.object(cli, "list_publications", return_value=[])

    _run(cli, ["--slug", "multi", "--remove-variant", "67"], monkeypatch)

    remove.assert_called_once_with("multi", "67")
    assert json.loads(capsys.readouterr().out)["variants"] == []


@pytest.mark.parametrize("bad", ["67", "=Bas-Rhin", "67="], ids=["no-equal", "empty-key", "empty-label"])
def test_dod_7_malformed_add_variant_is_refused(runtime, monkeypatch, mocker, bad):
    cli = _load("update_dashboard")
    mocker.patch.object(cli, "update_dashboard")
    with pytest.raises(SystemExit) as exc:
        _run(cli, ["--slug", "multi", "--add-variant", bad], monkeypatch)
    assert exc.value.code != 0


def test_dod_7_duplicate_key_error_is_reported_with_exit_1(runtime, monkeypatch, mocker, capsys):
    cli = _load("update_dashboard")
    _updated(mocker, cli)
    mocker.patch.object(cli, "list_variants", return_value=[])
    mocker.patch.object(cli, "add_variant", side_effect=ValueError("déclinaison déjà déclarée : 67"))
    with pytest.raises(SystemExit) as exc:
        _run(cli, ["--slug", "multi", "--add-variant", "67=Bas-Rhin"], monkeypatch)
    assert exc.value.code == 1
    assert "déjà déclarée" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("declared", "argv"),
    [
        (
            [{"key": "67", "label": "Bas-Rhin", "token": "t"}],
            ["--add-variant", "68=Haut-Rhin", "--add-variant", "67=Bis"],
        ),
        ([], ["--add-variant", "67=Bas-Rhin", "--add-variant", "67=Bis"]),
    ],
    ids=["already in base", "twice in the arguments"],
)
def test_dod_12_a_duplicate_key_is_refused_before_any_declaration(runtime, monkeypatch, mocker, capsys, declared, argv):
    cli = _load("update_dashboard")
    _updated(mocker, cli)
    mocker.patch.object(cli, "list_variants", return_value=declared)
    add = mocker.patch.object(cli, "add_variant")

    with pytest.raises(SystemExit) as exc:
        _run(cli, ["--slug", "multi", *argv], monkeypatch)

    assert exc.value.code == 1
    assert "déjà déclarée : 67" in capsys.readouterr().err
    add.assert_not_called()


def test_dod_9_create_dashboard_multi_source_flag(runtime, monkeypatch, mocker, capsys):
    cli = _load("create_dashboard")
    from datetime import datetime, timezone

    dashboard = mocker.Mock(
        slug="multi",
        first_author_email="bob@x",
        created_in_conversation_id="conv-1",
        created_at=datetime.now(timezone.utc),
    )
    create = mocker.patch.object(cli, "create_dashboard", return_value=dashboard)

    _run(cli, ["--slug", "multi", "--title", "T", "--description", "D", "--has-cron", "--multi-source"], monkeypatch)

    assert create.call_args.kwargs["multi_source"] is True
    assert json.loads(capsys.readouterr().out)["slug"] == "multi"


@pytest.mark.parametrize(
    ("publications", "announced", "unbounded"),
    [
        ([{"url": "https://statistiques.inclusion.gouv.fr/dashboards/multi", "refresh_paused_at": None}], True, False),
        (
            [{"url": "https://statistiques.inclusion.gouv.fr/dashboards/multi", "refresh_paused_at": "2026-09-01"}],
            True,
            True,
        ),
        ([], False, False),
    ],
    ids=["published", "published-refresh-paused", "not-published"],
)
def test_dod_7_remove_variant_announces_a_public_link_still_online(
    runtime, monkeypatch, mocker, capsys, publications, announced, unbounded
):
    cli = _load("update_dashboard")
    _updated(mocker, cli)
    mocker.patch.object(cli, "remove_variant", return_value=True)
    mocker.patch.object(cli, "list_variants", return_value=[])
    mocker.patch.object(cli, "list_publications", return_value=publications)

    _run(cli, ["--slug", "multi", "--remove-variant", "67"], monkeypatch)

    captured = capsys.readouterr()
    assert ("reste en ligne jusqu'au prochain rafraîchissement" in captured.err) is announced
    assert ("sans borne" in captured.err) is unbounded
    assert (json.loads(captured.out)["notices"] != []) is announced


def test_dod_12_every_add_variant_pair_is_checked_before_any_is_declared(runtime, monkeypatch, mocker, capsys):
    cli = _load("update_dashboard")
    _updated(mocker, cli)
    mocker.patch.object(cli, "list_variants", return_value=[])
    add = mocker.patch.object(cli, "add_variant")

    with pytest.raises(SystemExit) as exc:
        _run(cli, ["--slug", "multi", "--add-variant", "67=Bas-Rhin", "--add-variant", "Bad Key=X"], monkeypatch)

    assert exc.value.code == 1
    assert "Bad Key" in capsys.readouterr().err
    add.assert_not_called()
