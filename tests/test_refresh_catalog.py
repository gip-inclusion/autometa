"""Régénération des instantanés du catalogue — scripts/refresh_catalog.py, bases simulées."""

import importlib.util
from datetime import date
from pathlib import Path

import pytest

from lib import knowledge_lint
from lib.query import QueryResult

_spec = importlib.util.spec_from_file_location(
    "refresh_catalog", Path(__file__).parent.parent / "scripts/refresh_catalog.py"
)
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)

TODAY = date(2026, 10, 16)
COLUMNS = [["public.structures", '["id", "nom"]'], ["monrecap.Contacts", '["id"]'], ["public.candidats", '["id"]']]
DOCUMENTED = [["candidats"], ["int_imer"], ["vue__mbarchiv__1"], ["nom_prenom__mbarchiv__2"]]


def answering(columns, documented=()):
    def run(sql, **kwargs):
        return QueryResult(success=True, data={"rows": documented if sql == cli.DOCUMENTED else columns})

    return run


def test_l_instantane_regenere_est_trie_et_date_du_jour(mocker):
    mocker.patch.object(cli, "execute_autometa_tables_query", side_effect=answering(COLUMNS, DOCUMENTED))
    previous = {"documented_tables": ["candidats", "vue__mbarchiv__1"]}
    assert cli.snapshot("autometa_tables_db", previous, TODAY) == {
        "source": "autometa_tables_db",
        "extracted_at": "2026-10-16",
        "documented_tables": ["candidats", "int_imer", "vue__mbarchiv__1"],
        "tables": {"monrecap.Contacts": ["id"], "public.candidats": ["id"], "public.structures": ["id", "nom"]},
    }


def test_une_source_metabase_garde_ses_tables_documentees(mocker):
    run = mocker.patch.object(cli, "execute_metabase_query", side_effect=answering(COLUMNS))
    found = cli.snapshot("metabase:dora", {"documented_tables": ["int_archive"]}, TODAY)
    assert (found["source"], found["documented_tables"]) == ("metabase_dora", ["int_archive"])
    assert run.call_args.kwargs["instance"] == "dora"


def test_l_instantane_regenere_se_lit_comme_le_catalogue(mocker, tmp_path):
    mocker.patch.object(cli, "ROOT", tmp_path)
    mocker.patch.object(cli, "execute_autometa_tables_query", side_effect=answering(COLUMNS, DOCUMENTED))
    (tmp_path / "knowledge" / "catalog").mkdir(parents=True)
    assert cli.main(["autometa_tables_db"]) == 0
    tables, unverifiable = knowledge_lint.load_catalog(tmp_path, ["autometa_tables_db"])
    assert (tables["public.structures"], unverifiable) == (["id", "nom"], {"int_imer"})


@pytest.mark.parametrize(
    ("source", "patched", "credential"),
    [
        ("autometa_tables_db", "execute_autometa_tables_query", "AUTOMETA_TABLES_DATABASE_URL"),
        ("metabase:dora", "execute_metabase_query", "METABASE_DORA_API_KEY"),
    ],
)
def test_une_source_injoignable_echoue_sans_toucher_l_instantane(mocker, tmp_path, capsys, source, patched, credential):
    mocker.patch.object(cli, "ROOT", tmp_path)
    mocker.patch.object(cli, patched, return_value=QueryResult(success=False, data=None, error="connexion refusée"))
    path = knowledge_lint.catalog_path(tmp_path, source)
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    assert cli.main([source]) == 1
    assert path.read_text() == "{}"
    assert f"{source} injoignable : connexion refusée — définir {credential}" in capsys.readouterr().err
