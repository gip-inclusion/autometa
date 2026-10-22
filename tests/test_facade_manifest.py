"""Inventaire des symboles utilisés par les tableaux de bord, et contrôle CI qui le confronte à l'arbre."""

import json
from datetime import timedelta

import pytest

from web import facade_manifest
from web.environment import Environment
from web.helpers import utcnow

FILES = {
    "tdb-a/cron.py": b"from lib.dashboard_api import query_matomo\nimport helpers\n",
    "tdb-a/helpers.py": b"from lib.query import CallerType\nCallerType.APP\n",
    "tdb-a/index.html": b"<html></html>",
    "tdb-b/cron.py": b"from lib.dashboard_api import query_matomo\n",
    "tdb-c/cron.py": b"def main(\n",
}


def make_task(slug, source="s3"):
    return {"slug": slug, "source": source}


def mock_interactive_store(mocker):
    mocker.patch(
        "web.s3.interactive.list_files",
        side_effect=lambda prefix, raise_errors: [{"path": path} for path in FILES if path.startswith(prefix)],
    )
    mocker.patch("web.s3.interactive.download", side_effect=FILES.get)


def test_build_manifest_lists_each_symbol_with_the_dashboards_using_it(mocker):
    mock_interactive_store(mocker)

    manifest = facade_manifest.build_manifest([make_task("tdb-a"), make_task("tdb-b"), make_task("tdb-c")])

    assert manifest["symbols"] == {
        "lib.dashboard_api.query_matomo": ["tdb-a", "tdb-b"],
        "lib.query.CallerType": ["tdb-a"],
        "lib.query.CallerType.APP": ["tdb-a"],
    }


def test_build_manifest_ignores_system_crons(mocker):
    list_files = mocker.patch("web.s3.interactive.list_files")

    assert facade_manifest.build_manifest([make_task("sync-matomo", source="local")])["symbols"] == {}
    list_files.assert_not_called()


@pytest.mark.parametrize(("env", "published"), [(Environment.PROD, True), (Environment.STAGING, False)])
def test_publish_manifest_writes_to_the_public_bucket_in_production_only(mocker, env, published):
    mocker.patch("web.config.ENV", env)
    put = mocker.patch("web.s3.put_object", return_value=True)

    assert facade_manifest.publish_manifest({"symbols": {}}) is published
    assert put.called is published
    if published:
        assert put.call_args.args[:2] == ("test-prod-bucket", "contrat-tdb/manifest.json")


@pytest.mark.parametrize(
    ("symbol", "present"),
    [
        ("lib.dashboard_api.query_matomo", True),
        ("lib.query.CallerType.APP", True),
        ("web.s3.interactive.download", True),
        ("lib.dashboard_api", True),
        ("lib.dashboard_api.disparu", False),
        ("lib.query.CallerType.DISPARU", False),
        ("lib.module_disparu.Client", False),
    ],
)
def test_resolves_tells_whether_a_symbol_still_exists_in_the_tree(symbol, present):
    assert facade_manifest.resolves(symbol) is present


def write_manifest(tmp_path, symbols, age=timedelta(0)):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"generated_at": (utcnow() - age).isoformat(), "symbols": symbols}))
    return str(path)


def test_check_fails_when_a_used_symbol_has_disappeared(tmp_path, capsys):
    location = write_manifest(
        tmp_path, {"lib.dashboard_api.query_matomo": ["tdb-a"], "lib.rpe.RpeClient": ["rpeiae", "tdb-b"]}
    )

    assert facade_manifest.check(location) == 1
    assert "::error::lib.rpe.RpeClient a disparu, or il est utilisé par : rpeiae, tdb-b" in capsys.readouterr().out


def test_check_passes_when_every_used_symbol_is_present(tmp_path, capsys):
    assert facade_manifest.check(write_manifest(tmp_path, {"lib.dashboard_api.query_matomo": ["tdb-a"]})) == 0
    assert "::" not in capsys.readouterr().out


def test_check_warns_without_failing_when_the_manifest_is_unreadable(tmp_path, capsys):
    assert facade_manifest.check(str(tmp_path / "absent.json")) == 0
    assert "::warning::inventaire des tableaux de bord illisible" in capsys.readouterr().out


def test_check_warns_when_the_manifest_is_stale(tmp_path, capsys):
    assert facade_manifest.check(write_manifest(tmp_path, {}, age=timedelta(days=4))) == 0
    assert "::warning::inventaire des tableaux de bord vieux de 4 jours" in capsys.readouterr().out
