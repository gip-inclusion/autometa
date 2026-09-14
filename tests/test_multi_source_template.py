"""Le cron du gabarit multi-sources : un fichier par déclinaison déclarée, rien d'autre."""

import importlib.util
import json
from pathlib import Path

import pytest

from lib.query import QueryResult

TEMPLATE = Path(__file__).parent.parent / "docs" / "dashboard-template-multi"
TOKENS = {"117": "00000000-0000-4000-8000-000000000067", "211": "00000000-0000-4000-8000-000000000211"}


def _load_cron():
    spec = importlib.util.spec_from_file_location("multi_source_cron", TEMPLATE / "cron.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _variant(key, label):
    return {"key": key, "label": label, "token": TOKENS[key], "path": f"data/{TOKENS[key]}.json", "url": ""}


@pytest.fixture
def cron(tmp_path, monkeypatch, mocker):
    monkeypatch.chdir(tmp_path)
    module = _load_cron()
    mocker.patch.object(module, "list_variants", return_value=[_variant("117", "Emplois"), _variant("211", "Dora")])
    mocker.patch.object(
        module,
        "query_matomo",
        return_value=QueryResult(success=True, data={"117": {"nb_visits": 10}, "211": {"nb_visits": 3}}),
    )
    return module


def test_dod_6_one_file_per_declared_variant_and_nothing_else(cron, tmp_path):
    cron.main()

    written = sorted(p.name for p in (tmp_path / "data").iterdir())
    assert written == sorted(f"{t}.json" for t in TOKENS.values())
    assert [p.name for p in tmp_path.iterdir()] == ["data"]
    emplois = json.loads((tmp_path / "data" / f"{TOKENS['117']}.json").read_text())
    assert emplois["metadata"]["key"] == "117"
    assert emplois["metadata"]["label"] == "Emplois"
    assert emplois["visites"] == {"nb_visits": 10}


def test_dod_6_a_single_batch_query_feeds_every_variant(cron):
    cron.main()
    assert cron.query_matomo.call_count == 1


def test_dod_10_the_data_file_never_carries_its_own_token(cron, tmp_path):
    cron.main()
    for key, token in TOKENS.items():
        assert token not in (tmp_path / "data" / f"{token}.json").read_text(), key


def test_dod_11_no_declared_variant_writes_nothing(cron, tmp_path):
    cron.list_variants.return_value = []
    cron.main()
    assert not (tmp_path / "data").exists()
    cron.query_matomo.assert_not_called()


def test_dod_15_a_failing_variant_keeps_its_old_file_and_fails_the_run_by_name(cron, tmp_path):
    cron.query_matomo.return_value = QueryResult(success=True, data={"117": {"nb_visits": 10}})
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / f"{TOKENS['211']}.json").write_text('{"old": true}')

    with pytest.raises(SystemExit, match="211"):
        cron.main()

    assert (tmp_path / "data" / f"{TOKENS['117']}.json").exists()
    assert json.loads((tmp_path / "data" / f"{TOKENS['211']}.json").read_text()) == {"old": True}


def _raise_for_117(original):
    def assemble(variant, payload):
        if variant["key"] == "117":
            raise KeyError("champ manquant")
        return original(variant, payload)

    return assemble


def test_dod_15_an_assembly_error_on_one_variant_does_not_block_the_others(cron, tmp_path, mocker):
    mocker.patch.object(cron, "assemble", side_effect=_raise_for_117(cron.assemble))

    with pytest.raises(SystemExit, match="117"):
        cron.main()

    assert not (tmp_path / "data" / f"{TOKENS['117']}.json").exists()
    assert (tmp_path / "data" / f"{TOKENS['211']}.json").exists()
