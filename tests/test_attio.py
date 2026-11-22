import json
import sys

import httpx
import pytest

from lib import dashboard_api
from lib.attio import PAGE_SIZE, AttioClient, AttioError, AttioInvalidRequest, aplatir, run
from lib.query import CallerType, execute_query
from web.routes.query import validate_query_request
from web.source_checks import check_attio
from web.sources_registry import all_sources


def json_resp(mocker, payload):
    resp = mocker.MagicMock(status_code=200)
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def client(mocker):
    mocker.patch("lib.attio.emit_api_signal")
    return AttioClient(api_key="attio-test")


@pytest.fixture
def crm(mocker):
    """Le CRM simulé derrière `run()` : clé présente, aucun appel réseau."""
    mocker.patch("lib.attio.config.ATTIO_API_KEY", "k")
    mocker.patch("lib.attio.emit_api_signal")
    return mocker


def person(rid, role=None, email="a@exemple.fr"):
    values = {
        "name": [{"attribute_type": "personal-name", "full_name": "Prénom Nom"}],
        "email_addresses": [{"attribute_type": "email-address", "email_address": email}],
        "phone_numbers": [{"attribute_type": "phone-number", "original_phone_number": "+33600000000"}],
    }
    if role:
        values["role"] = [{"attribute_type": "select", "option": {"title": role}}]
    return {"id": {"record_id": rid}, "values": values}


def company(rid, kind):
    return {
        "id": {"record_id": rid},
        "values": {"type_de_compte": [{"attribute_type": "select", "option": {"title": kind}}]},
    }


def test_missing_api_key_raises(mocker):
    mocker.patch("lib.attio.config.ATTIO_API_KEY", None)
    with pytest.raises(AttioError):
        AttioClient(api_key=None)


def test_http_error_raises_attio_error(mocker, client):
    req = httpx.Request("GET", "https://api.attio.com/v2/objects")
    resp = mocker.MagicMock()
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "forbidden", request=req, response=httpx.Response(403, request=req)
    )
    mocker.patch.object(client._session, "request", return_value=resp)
    with pytest.raises(AttioError, match="403"):
        client.list_objects()


def test_a_non_json_answer_is_an_attio_error(mocker, client):
    resp = mocker.MagicMock(status_code=200)
    resp.raise_for_status.return_value = None
    resp.json.side_effect = ValueError("not json")
    mocker.patch.object(client._session, "request", return_value=resp)
    with pytest.raises(AttioError):
        client.list_objects()


def test_iter_records_stops_on_short_page_and_respects_cap(mocker, client):
    full = [{"id": {"record_id": str(i)}} for i in range(PAGE_SIZE)]
    q = mocker.patch.object(client, "query_records", side_effect=[full, full[:3]])
    assert len(list(client.iter_records("people"))) == PAGE_SIZE + 3
    assert q.call_count == 2
    mocker.patch.object(client, "query_records", return_value=full)
    assert len(list(client.iter_records("people", max_pages=2))) == 2 * PAGE_SIZE


def test_dod_1_count_gives_total_and_breakdown(crm):
    rows = [company("1", "CCAS"), company("2", "CCAS"), company("3", "Mission locale"), {"id": {"record_id": "4"}}]
    crm.patch("lib.attio.AttioClient.iter_records", return_value=iter(rows))
    assert run("count", {"object": "companies", "by": "type_de_compte"}) == {
        "total": 4,
        "complet": True,
        "par_type_de_compte": {"CCAS": 2, "Mission locale": 1, "(vide)": 1},
    }


def test_dod_1_count_says_when_it_stopped_at_the_page_cap(crm):
    crm.patch("lib.attio.MAX_PAGES", 2)
    full = [company(str(i), "CCAS") for i in range(PAGE_SIZE)]
    crm.patch("lib.attio.AttioClient.query_records", return_value=full)
    out = run("count", {"object": "companies"})
    assert out["total"] == 2 * PAGE_SIZE
    assert out["complet"] is False


def test_dod_1_agent_script_prints_the_count(crm, capsys, monkeypatch):
    from skills.attio.scripts import query as script

    crm.patch("lib.attio.AttioClient.iter_records", return_value=iter([company("1", "CCAS")]))
    monkeypatch.setattr(sys, "argv", ["query.py", "--count", "companies", "--by", "type_de_compte"])
    script.main()
    assert json.loads(capsys.readouterr().out) == {"total": 1, "complet": True, "par_type_de_compte": {"CCAS": 1}}


def test_dod_2_search_sends_the_filter_and_caps_the_limit(crm):
    query = crm.patch("lib.attio.AttioClient.query_records", return_value=[company("1", "CCAS")])
    rows = run("records", {"object": "companies", "filter": {"type_de_compte": "CCAS"}, "limit": 9999})
    assert rows == [{"id": "1", "type_de_compte": "CCAS"}]
    assert query.call_args.kwargs == {"filter": {"type_de_compte": "CCAS"}, "limit": PAGE_SIZE}


def test_dod_2_query_records_posts_filter_and_pagination(mocker, client):
    req = mocker.patch.object(client._session, "request", return_value=json_resp(mocker, {"data": []}))
    client.query_records("companies", filter={"type_de_compte": "CCAS"}, limit=10, offset=20)
    assert req.call_args.args == ("POST", "/objects/companies/records/query")
    assert req.call_args.kwargs["json"] == {"limit": 10, "offset": 20, "filter": {"type_de_compte": "CCAS"}}


def test_dod_2_aplatir_reads_each_value_type():
    record = {
        "id": {"record_id": "r1"},
        "values": {
            "name": [{"attribute_type": "personal-name", "full_name": "Prénom Nom"}],
            "role": [{"attribute_type": "select", "option": {"title": "Pilote"}}],
            "company": [{"attribute_type": "record-reference", "target_record_id": "c1"}],
            "job_title": [],
            "primary_location": [
                {"attribute_type": "location", "locality": "Lille", "region": None, "country_code": "FR"}
            ],
        },
    }
    assert aplatir(record) == {
        "id": "r1",
        "name": "Prénom Nom",
        "role": "Pilote",
        "company": "c1",
        "primary_location": "Lille, FR",
    }
    assert aplatir(record, ["role"]) == {"id": "r1", "role": "Pilote"}


def test_dod_3_dashboard_reads_the_entries_of_a_pipe(crm):
    entry = {
        "id": {"entry_id": "e1"},
        "parent_record_id": "c1",
        "entry_values": {"stage": [{"attribute_type": "status", "status": {"title": "Contacté"}}]},
    }
    crm.patch("lib.attio.AttioClient.iter_entries", return_value=iter([entry]))
    result = execute_query(
        source="attio", instance="", caller=CallerType.APP, method="entries", params={"list": "sales"}
    )
    assert result.success is True
    assert result.data == [{"id": "e1", "parent_record_id": "c1", "stage": "Contacté"}]


def test_dod_3_cron_facade_reaches_attio(mocker):
    execute = mocker.patch("lib.dashboard_api.query.execute_attio_query")
    dashboard_api.query_attio("entries", {"list": "sales"})
    assert execute.call_args.kwargs == {
        "method": "entries",
        "caller": CallerType.APP,
        "params": {"list": "sales"},
        "timeout": 60,
    }


def test_dod_3_api_query_requires_a_method_for_attio():
    assert validate_query_request({"source": "attio", "method": "lists"}) is None
    error = validate_query_request({"source": "attio"})
    assert error.startswith("method is required for attio")
    assert "records" in error and "entries" in error


@pytest.mark.parametrize("method", ["records", "entries"])
def test_dod_4_dashboard_never_receives_emails_or_phones(crm, method):
    crm.patch("lib.attio.AttioClient.query_records", return_value=[person("r1", "Pilote")])
    crm.patch("lib.attio.AttioClient.iter_entries", return_value=iter([person("r1", "Pilote")]))
    params = {"object": "people"} if method == "records" else {"list": "sales"}
    rows = run(method, params)
    assert rows == [{"id": "r1", "name": "Prénom Nom", "role": "Pilote"}]
    assert "@" not in json.dumps(rows) and "+33" not in json.dumps(rows)


def test_dod_4_count_by_email_reveals_nothing(crm):
    crm.patch("lib.attio.AttioClient.iter_records", return_value=iter([person("1"), person("2", email="b@exemple.fr")]))
    out = run("count", {"object": "people", "by": "email_addresses"})
    assert out == {"total": 2, "complet": True, "par_email_addresses": {"(vide)": 2}}


def test_dod_4_an_email_typed_into_a_text_attribute_is_dropped(crm):
    record = {
        "id": {"record_id": "r1"},
        "values": {
            "description": [{"attribute_type": "text", "value": "Joindre la directrice : d@exemple.fr"}],
            "job_title": [{"attribute_type": "text", "value": "Directrice"}],
        },
    }
    crm.patch("lib.attio.AttioClient.query_records", return_value=[record])
    assert run("records", {"object": "people"}) == [{"id": "r1", "job_title": "Directrice"}]


@pytest.mark.parametrize("phone", ["06 12 34 56 78", "+33 6 12 34 56 78", "01.23.45.67.89", "0612345678"])
def test_dod_4_a_phone_typed_into_a_text_attribute_is_dropped(crm, phone):
    record = {
        "id": {"record_id": "r1"},
        "values": {"description": [{"attribute_type": "text", "value": f"Tél. {phone}"}]},
    }
    crm.patch("lib.attio.AttioClient.query_records", return_value=[record])
    assert run("records", {"object": "people"}) == [{"id": "r1"}]


@pytest.mark.parametrize(
    "filter",
    [{"email_addresses": "x@exemple.fr"}, {"phone_numbers": "+33600000000"}, {"name": {"$contains": "a@b.fr"}}],
)
def test_dod_4_a_filter_cannot_probe_an_email_or_a_phone(crm, filter):
    session = crm.patch("httpx.Client.request")
    with pytest.raises(AttioInvalidRequest):
        run("count", {"object": "people", "filter": filter})
    session.assert_not_called()


@pytest.mark.parametrize(
    "method,params",
    [
        ("create_record", {}),
        ("delete_record", {"object": "people"}),
        ("records", {}),
        ("records", {"object": "people", "sorts": []}),
        ("records", {"object": "people", "limit": "beaucoup"}),
        ("records", {"object": "people/records?x="}),
        ("entries", {"list": "sales/entries?x="}),
        ("attributes", {"object": "people/records/abc?x="}),
        ("options", {"object": "companies", "attribute": "../lists"}),
        ("count", {"object": "people", "by": ["role"]}),
        ("records", {"object": "people", "fields": "name"}),
        ("records", {"object": "people", "filter": "role=Pilote"}),
        ("attributes", {"object": "people\n"}),
    ],
)
def test_dod_5_unplanned_requests_are_refused_before_any_call(crm, method, params):
    session = crm.patch("httpx.Client.request")
    with pytest.raises(AttioInvalidRequest):
        run(method, params)
    session.assert_not_called()


def test_dod_5_refusal_says_what_is_allowed_through_api_query():
    result = execute_query(source="attio", instance="", caller=CallerType.APP, method="delete_record")
    assert result.success is False
    assert result.invalid_request is True
    assert "records" in result.error and "entries" in result.error


def test_dod_5_refused_parameter_lists_the_allowed_ones(crm):
    with pytest.raises(AttioInvalidRequest) as refus:
        run("records", {"object": "people", "sorts": []})
    for allowed in ("object", "filter", "fields", "limit"):
        assert allowed in str(refus.value)


@pytest.mark.parametrize(
    "params,expected",
    [
        ({"object": "people", "limit": "beaucoup"}, "un entier"),
        ({"object": "people/records?x="}, "lettres, chiffres"),
        ({"object": "people", "filter": "role=Pilote"}, "un objet JSON"),
        ({"object": "people", "fields": "name"}, "une liste"),
    ],
)
def test_dod_5_refused_value_says_what_is_expected(crm, params, expected):
    with pytest.raises(AttioInvalidRequest) as refus:
        run("records", params)
    assert expected in str(refus.value)


def test_dod_6_probe_counts_objects(mocker):
    mocker.patch("web.source_checks.config.ATTIO_API_KEY", "k")
    resp = mocker.MagicMock(status_code=200)
    resp.json.return_value = {"data": [{}, {}, {}]}
    mocker.patch("web.source_checks.httpx.get", return_value=resp)
    assert check_attio() == (True, "3 objets")


def test_dod_6_sources_page_lists_attio():
    [source] = [s for s in all_sources() if s.slug == "attio"]
    assert source.skill == "attio"
    assert source.check is check_attio
