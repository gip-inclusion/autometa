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


def test_dod_7_add_variant_declares_key_and_label(runtime, monkeypatch, mocker, capsys):
    cli = _load("update_dashboard")
    mocker.patch.object(
        cli,
        "update_dashboard",
        return_value=mocker.Mock(slug="multi", originating_user_email="a@x", updater_email="bob@x", fields_changed=[]),
    )
    add = mocker.patch.object(cli, "add_variant", return_value={"key": "67", "label": "Bas-Rhin", "token": "t"})
    mocker.patch.object(cli, "list_variants", return_value=[{"key": "67", "label": "Bas-Rhin", "token": "t"}])

    _run(cli, ["--slug", "multi", "--add-variant", "67=Bas-Rhin"], monkeypatch)

    add.assert_called_once_with("multi", "67", "Bas-Rhin")
    out = json.loads(capsys.readouterr().out)
    assert out["variants"] == [{"key": "67", "label": "Bas-Rhin", "token": "t"}]


def test_dod_7_remove_variant_by_key(runtime, monkeypatch, mocker, capsys):
    cli = _load("update_dashboard")
    mocker.patch.object(
        cli,
        "update_dashboard",
        return_value=mocker.Mock(slug="multi", originating_user_email="a@x", updater_email="bob@x", fields_changed=[]),
    )
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
    mocker.patch.object(
        cli,
        "update_dashboard",
        return_value=mocker.Mock(slug="multi", originating_user_email="a@x", updater_email="bob@x", fields_changed=[]),
    )
    mocker.patch.object(cli, "add_variant", side_effect=ValueError("déclinaison déjà déclarée : 67"))
    with pytest.raises(SystemExit) as exc:
        _run(cli, ["--slug", "multi", "--add-variant", "67=Bas-Rhin"], monkeypatch)
    assert exc.value.code == 1
    assert "déjà déclarée" in capsys.readouterr().err


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


def test_dod_7_remove_variant_announces_a_public_link_still_online(runtime, monkeypatch, mocker, capsys):
    cli = _load("update_dashboard")
    mocker.patch.object(
        cli,
        "update_dashboard",
        return_value=mocker.Mock(slug="multi", originating_user_email="a@x", updater_email="bob@x", fields_changed=[]),
    )
    mocker.patch.object(cli, "remove_variant", return_value=True)
    mocker.patch.object(cli, "list_variants", return_value=[])
    mocker.patch.object(
        cli, "list_publications", return_value=[{"url": "https://statistiques.inclusion.gouv.fr/dashboards/multi"}]
    )

    _run(cli, ["--slug", "multi", "--remove-variant", "67"], monkeypatch)

    captured = capsys.readouterr()
    assert "reste en ligne jusqu'au prochain rafraîchissement" in captured.err
    assert "reste en ligne" in json.loads(captured.out)["notices"][0]


def test_dod_7_remove_variant_is_silent_without_publication(runtime, monkeypatch, mocker, capsys):
    cli = _load("update_dashboard")
    mocker.patch.object(
        cli,
        "update_dashboard",
        return_value=mocker.Mock(slug="multi", originating_user_email="a@x", updater_email="bob@x", fields_changed=[]),
    )
    mocker.patch.object(cli, "remove_variant", return_value=True)
    mocker.patch.object(cli, "list_variants", return_value=[])
    mocker.patch.object(cli, "list_publications", return_value=[])

    _run(cli, ["--slug", "multi", "--remove-variant", "67"], monkeypatch)

    assert json.loads(capsys.readouterr().out)["notices"] == []
