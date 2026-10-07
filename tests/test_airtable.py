import importlib.util
from argparse import Namespace
from pathlib import Path

import httpx
import pytest

from lib.airtable import AirtableClient, AirtableError

spec = importlib.util.spec_from_file_location(
    "airtable_query_cli", Path(__file__).parent.parent / "skills/airtable/scripts/query.py"
)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def make_client(mocker, token="pat-test"):
    mocker.patch("lib.airtable.emit_api_signal")
    mocker.patch("lib.airtable.time.sleep")
    return AirtableClient(token=token)


def json_resp(mocker, payload):
    resp = mocker.MagicMock(status_code=200)
    resp.json.return_value = payload
    return resp


def http_error(mocker, status):
    request = httpx.Request("GET", "https://api.airtable.com/v0/app1/tbl1")
    resp = mocker.MagicMock(status_code=status)
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "error", request=request, response=httpx.Response(status, request=request)
    )
    return resp


def test_missing_token_raises(mocker):
    mocker.patch("lib.airtable.config.AIRTABLE_TOKEN", None)
    with pytest.raises(AirtableError, match="AIRTABLE_TOKEN"):
        AirtableClient()


def test_get_returns_json_and_emits_signal(mocker):
    client = make_client(mocker)
    emit = mocker.patch("lib.airtable.emit_api_signal")
    mocker.patch.object(client._session, "get", return_value=json_resp(mocker, {"tables": [{"id": "tbl1"}]}))

    assert client.list_tables("app1") == [{"id": "tbl1"}]
    client._session.get.assert_called_once_with("/meta/bases/app1/tables", params=None)
    emit.assert_called_once()
    assert emit.call_args.kwargs["source"] == "airtable"
    assert "pat-test" not in str(emit.call_args)


@pytest.mark.parametrize("status", [403, 404, 429])
def test_http_error_raises_airtable_error_without_token(mocker, status):
    client = make_client(mocker)
    mocker.patch.object(client._session, "get", return_value=http_error(mocker, status))

    with pytest.raises(AirtableError, match=str(status)) as exc:
        client.list_records("app1", "tbl1")
    assert "pat-test" not in str(exc.value)


def test_rate_limit_waits_out_the_penalty_then_retries_once(mocker):
    client = make_client(mocker)
    sleep = mocker.patch("lib.airtable.time.sleep")
    get = mocker.patch.object(
        client._session, "get", side_effect=[http_error(mocker, 429), json_resp(mocker, {"records": [{"id": "a"}]})]
    )

    assert client.list_records("app1", "tbl1") == [{"id": "a"}]
    assert get.call_count == 2
    sleep.assert_called_once_with(30)


def test_forbidden_explains_missing_scope(mocker):
    client = make_client(mocker)
    mocker.patch.object(client._session, "get", return_value=http_error(mocker, 403))

    with pytest.raises(AirtableError, match="schema.bases:read"):
        client.list_tables("app1")


def test_request_error_raises_airtable_error(mocker):
    client = make_client(mocker)
    mocker.patch.object(client._session, "get", side_effect=httpx.ConnectError("boom"))

    with pytest.raises(AirtableError):
        client.list_records("app1", "tbl1")


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({}, {"pageSize": 100}),
        ({"view": "viw1"}, {"pageSize": 100, "view": "viw1"}),
        ({"fields": ["Nom", "Statut"]}, {"pageSize": 100, "fields[]": ["Nom", "Statut"]}),
        ({"formula": "{Statut} = 'ok'"}, {"pageSize": 100, "filterByFormula": "{Statut} = 'ok'"}),
    ],
)
def test_list_records_param_mapping(mocker, kwargs, expected):
    client = make_client(mocker)
    get = mocker.patch.object(client, "_get", return_value={"records": []})

    client.list_records("app1", "tbl1", **kwargs)

    get.assert_called_once_with("/app1/tbl1", params=expected)


@pytest.mark.parametrize(
    "table,path",
    [
        ("tbl1", "/app1/tbl1"),
        ("Devis clients", "/app1/Devis%20clients"),
        ("Devis #2", "/app1/Devis%20%232"),
        ("Devis/Commandes", "/app1/Devis%2FCommandes"),
    ],
)
def test_list_records_encodes_table_name_in_path(mocker, table, path):
    client = make_client(mocker)
    get = mocker.patch.object(client, "_get", return_value={"records": []})

    client.list_records("app1", table)

    assert get.call_args.args[0] == path


def test_list_records_follows_offset_and_paces_requests(mocker):
    client = make_client(mocker)
    sleep = mocker.patch("lib.airtable.time.sleep")
    get = mocker.patch.object(
        client, "_get", side_effect=[{"records": [{"id": "a"}], "offset": "o1"}, {"records": [{"id": "b"}]}]
    )

    records = client.list_records("app1", "tbl1", view="viw1")

    assert [r["id"] for r in records] == ["a", "b"]
    assert get.call_args_list[1].kwargs["params"] == {"pageSize": 100, "view": "viw1", "offset": "o1"}
    assert "offset" not in get.call_args_list[0].kwargs["params"]
    sleep.assert_called_once()


def test_list_records_caps_pages(mocker):
    client = make_client(mocker)
    get = mocker.patch.object(client, "_get", return_value={"records": [{"id": "x"}], "offset": "o"})
    warn = mocker.patch("lib.airtable.logger.warning")

    assert len(client.list_records("app1", "tbl1", max_pages=3)) == 3
    assert get.call_count == 3
    warn.assert_called_once()


def test_client_context_manager_closes_session(mocker):
    client = make_client(mocker)
    mocker.patch.object(client._session, "close")

    with client as entered:
        assert entered is client
    client._session.close.assert_called_once()


def test_cli_tables_summarizes_fields_and_views(mocker):
    client = mocker.MagicMock()
    client.__enter__.return_value = client
    client.list_tables.return_value = [
        {
            "id": "tbl1",
            "name": "Devis",
            "primaryFieldId": "fld1",
            "fields": [{"id": "fld1", "name": "Nom", "type": "singleLineText", "options": {}}],
            "views": [{"id": "viw1", "name": "À valider", "type": "grid"}],
        }
    ]
    mocker.patch.object(cli, "AirtableClient", return_value=client)

    assert cli.run(Namespace(command="tables", base_id="app1")) == [
        {
            "id": "tbl1",
            "name": "Devis",
            "fields": [{"id": "fld1", "name": "Nom", "type": "singleLineText"}],
            "views": [{"id": "viw1", "name": "À valider"}],
        }
    ]


def test_cli_records_counts_records(mocker):
    client = mocker.MagicMock()
    client.__enter__.return_value = client
    client.list_records.return_value = [{"id": "a"}, {"id": "b"}]
    mocker.patch.object(cli, "AirtableClient", return_value=client)
    args = Namespace(
        command="records", base_id="app1", table="tbl1", view="viw1", field=None, formula=None, max_pages=5
    )

    assert cli.run(args) == {"count": 2, "records": [{"id": "a"}, {"id": "b"}]}
    client.list_records.assert_called_once_with("app1", "tbl1", view="viw1", fields=None, formula=None, max_pages=5)


def test_cli_exits_with_a_clear_message_without_token(mocker):
    mocker.patch("lib.airtable.config.AIRTABLE_TOKEN", None)
    mocker.patch("sys.argv", ["query.py", "tables", "app1"])

    with pytest.raises(SystemExit, match="AIRTABLE_TOKEN"):
        cli.main()


@pytest.mark.external
def test_real_api_reads_monrecap_devis_view():
    with AirtableClient() as client:
        records = client.list_records("apppGMTgMw5lav2d1", "tblMe0DsXWKTAZN1d", view="viwizmpNR5XNOT59s")
    assert all("id" in r for r in records)
