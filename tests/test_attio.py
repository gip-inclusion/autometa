import json
import sys
from pathlib import Path

import httpx
import pytest

from lib import dashboard_api, knowledge_lint
from lib.attio import (
    PAGE_SIZE,
    AttioClient,
    AttioError,
    AttioInvalidRequest,
    attributes,
    entries,
    flatten,
    lists,
    objects,
    options,
    run,
)
from lib.query import CallerType, execute_query
from skills.attio.scripts import query as attio_script
from web.routes.query import validate_query_request
from web.source_checks import check_attio
from web.sources_registry import all_sources

REPO = Path(__file__).parent.parent


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
    """Le CRM simulé derrière `run()` : clé présente, aucun attribut email ou téléphone personnalisé, aucun appel réseau."""
    mocker.patch("lib.attio.get_source_config", return_value={"api_key": "k"})
    mocker.patch("lib.attio.emit_api_signal")
    mocker.patch("lib.attio.AttioClient.list_attributes", return_value=[])
    mocker.patch("lib.attio.AttioClient.get_list", return_value={"parent_object": ["people"]})
    return mocker


CUSTOM_CONTACT_ATTRIBUTES = [
    {"api_slug": "telephone", "type": "phone-number"},
    {"api_slug": "email_pro", "type": "email-address"},
    {"api_slug": "role", "type": "select"},
]


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


def test_the_agent_reads_attio_only_when_the_request_names_it():
    rules = knowledge_lint.section((REPO / "AGENT.md").read_text(), "Sources de données")
    [entry] = [line for _, line in rules if line.startswith("- **Attio**")]
    assert "Seulement si la demande nomme Attio ou le CRM" in entry
    assert "jamais avec Attio" in entry
    description = knowledge_lint.front_matter((REPO / "skills/attio/SKILL.md").read_text())["description"]
    assert "seulement quand la demande nomme Attio ou le CRM" in description
    assert "AGENT.md" in description


@pytest.mark.parametrize("value,expected", [(None, "ATTIO_API_KEY"), ("", "clé absente")])
def test_the_key_comes_from_sources_yaml_and_its_absence_is_an_attio_error(monkeypatch, value, expected):
    monkeypatch.setattr("lib.sources.config_cache", None)
    if value is None:
        monkeypatch.delenv("ATTIO_API_KEY", raising=False)
    else:
        monkeypatch.setenv("ATTIO_API_KEY", value)
    with pytest.raises(AttioError, match=expected):
        AttioClient()


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


def entries_page(mocker, size):
    return json_resp(mocker, {"data": [{"id": {"entry_id": str(i)}, "entry_values": {}} for i in range(size)]})


@pytest.mark.parametrize(
    "sizes,read,complete",
    [((PAGE_SIZE, 3), PAGE_SIZE + 3, True), ((PAGE_SIZE, PAGE_SIZE, PAGE_SIZE), 2 * PAGE_SIZE, False)],
)
def test_entries_page_through_the_list_route_until_a_short_page_or_the_cap(mocker, client, sizes, read, complete):
    mocker.patch("lib.attio.MAX_PAGES", 2)
    request = mocker.patch.object(
        client._session, "request", side_effect=[entries_page(mocker, size) for size in sizes]
    )
    out = entries(client, "sales", filter={"stage": "Contacté"})
    assert (len(out["entries"]), out["complete"]) == (read, complete)
    assert [call.args for call in request.call_args_list] == [("POST", "/lists/sales/entries/query")] * 2
    assert [call.kwargs["json"] for call in request.call_args_list] == [
        {"limit": PAGE_SIZE, "offset": 0, "filter": {"stage": "Contacté"}},
        {"limit": PAGE_SIZE, "offset": PAGE_SIZE, "filter": {"stage": "Contacté"}},
    ]


@pytest.mark.parametrize(
    "method,args,path,data,expected",
    [
        (
            objects,
            (),
            "/objects",
            [{"api_slug": "companies", "plural_noun": "Companies", "object_id": "o1"}],
            [{"slug": "companies", "name": "Companies"}],
        ),
        (
            attributes,
            ("companies",),
            "/objects/companies/attributes",
            [
                {"api_slug": "type_de_compte", "title": "Type", "type": "select", "is_multiselect": False},
                {"api_slug": "ancien", "title": "Ancien", "type": "text", "is_archived": True},
            ],
            [{"slug": "type_de_compte", "name": "Type", "type": "select", "multiple": False}],
        ),
        (
            options,
            ("companies", "type_de_compte"),
            "/objects/companies/attributes/type_de_compte/options",
            [{"title": "CCAS"}, {"title": "Ancien type", "is_archived": True}],
            ["CCAS"],
        ),
        (
            lists,
            (),
            "/lists",
            [{"api_slug": "sales", "name": "Sales", "parent_object": ["companies"], "id": {"list_id": "l1"}}],
            [{"slug": "sales", "name": "Sales", "object": "companies", "id": "l1"}],
        ),
    ],
)
def test_catalogue_methods_return_their_documented_shape(mocker, client, method, args, path, data, expected):
    request = mocker.patch.object(client._session, "request", return_value=json_resp(mocker, {"data": data}))
    assert method(client, *args) == expected
    assert request.call_args.args == ("GET", path)


def test_dod_1_count_gives_total_and_breakdown(crm):
    rows = [company("1", "CCAS"), company("2", "CCAS"), company("3", "Mission locale"), {"id": {"record_id": "4"}}]
    crm.patch("lib.attio.AttioClient.query", return_value=rows)
    assert run("count", {"object": "companies", "by": "type_de_compte"}) == {
        "total": 4,
        "complete": True,
        "by_type_de_compte": {"CCAS": 2, "Mission locale": 1, None: 1},
    }


def test_dod_1_count_says_when_it_stopped_at_the_page_cap(crm):
    crm.patch("lib.attio.MAX_PAGES", 2)
    full = [company(str(i), "CCAS") for i in range(PAGE_SIZE)]
    crm.patch("lib.attio.AttioClient.query", return_value=full)
    out = run("count", {"object": "companies"})
    assert out["total"] == 2 * PAGE_SIZE
    assert out["complete"] is False


def test_dod_1_agent_script_prints_the_count(crm, capsys, monkeypatch):
    crm.patch("lib.attio.AttioClient.query", return_value=[company("1", "CCAS")])
    monkeypatch.setattr(sys, "argv", ["query.py", "--count", "companies", "--by", "type_de_compte"])
    attio_script.main()
    assert json.loads(capsys.readouterr().out) == {"total": 1, "complete": True, "by_type_de_compte": {"CCAS": 1}}


def test_dod_2_search_sends_the_filter_and_caps_the_limit(crm):
    query = crm.patch("lib.attio.AttioClient.query", return_value=[company("1", "CCAS")])
    rows = run("records", {"object": "companies", "filter": {"type_de_compte": "CCAS"}, "limit": 9999})
    assert rows == [{"id": "1", "type_de_compte": "CCAS"}]
    assert query.call_args.kwargs == {"filter": {"type_de_compte": "CCAS"}, "limit": PAGE_SIZE}


def test_dod_2_query_posts_filter_and_pagination(mocker, client):
    req = mocker.patch.object(client._session, "request", return_value=json_resp(mocker, {"data": []}))
    client.query("/objects/companies/records/query", filter={"type_de_compte": "CCAS"}, limit=10, offset=20)
    assert req.call_args.args == ("POST", "/objects/companies/records/query")
    assert req.call_args.kwargs["json"] == {"limit": 10, "offset": 20, "filter": {"type_de_compte": "CCAS"}}


def test_dod_2_flatten_reads_each_value_type():
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
    assert flatten(record) == {
        "id": "r1",
        "name": "Prénom Nom",
        "role": "Pilote",
        "company": "c1",
        "primary_location": "Lille, FR",
    }
    assert flatten(record, ["role"]) == {"id": "r1", "role": "Pilote"}


def test_dod_3_dashboard_reads_the_entries_of_a_pipe(crm):
    entry = {
        "id": {"entry_id": "e1"},
        "parent_record_id": "c1",
        "entry_values": {"stage": [{"attribute_type": "status", "status": {"title": "Contacté"}}]},
    }
    crm.patch("lib.attio.AttioClient.query", return_value=[entry])
    result = execute_query(
        source="attio", instance="", caller=CallerType.APP, method="entries", params={"list": "sales"}
    )
    assert result.success is True
    assert result.data == {"entries": [{"id": "e1", "parent_record_id": "c1", "stage": "Contacté"}], "complete": True}


def test_dod_3_entries_say_when_they_stopped_at_the_page_cap(crm):
    crm.patch("lib.attio.MAX_PAGES", 2)
    full = [{"id": {"entry_id": str(i)}, "entry_values": {}} for i in range(PAGE_SIZE)]
    crm.patch("lib.attio.AttioClient.query", return_value=full)
    out = run("entries", {"list": "sales"})
    assert len(out["entries"]) == 2 * PAGE_SIZE
    assert out["complete"] is False


def test_dod_3_cron_facade_reaches_attio(mocker):
    execute = mocker.patch("lib.dashboard_api.query.execute_attio_query")
    dashboard_api.query_attio("entries", {"list": "sales"})
    assert execute.call_args.kwargs == {
        "method": "entries",
        "caller": CallerType.APP,
        "params": {"list": "sales"},
        "timeout": 60,
    }


@pytest.mark.parametrize("payload", [{"data": None}, {"data": [{"id": None, "values": {}}]}])
def test_dod_3_an_unexpected_answer_fails_the_query_without_raising(crm, payload):
    crm.patch("httpx.Client.request", return_value=json_resp(crm, payload))
    assert dashboard_api.query_attio("records", {"object": "people"}).success is False


def test_dod_3_api_query_requires_a_method_for_attio():
    assert validate_query_request({"source": "attio", "method": "lists"}) is None
    error = validate_query_request({"source": "attio"})
    assert error.startswith("method is required for attio")
    assert "records" in error and "entries" in error


@pytest.mark.parametrize("method", ["records", "entries"])
def test_dod_4_dashboard_never_receives_emails_or_phones(crm, method):
    crm.patch("lib.attio.AttioClient.query", return_value=[person("r1", "Pilote")])
    params = {"object": "people"} if method == "records" else {"list": "sales"}
    out = run(method, params)
    rows = out["entries"] if method == "entries" else out
    assert rows == [{"id": "r1", "name": "Prénom Nom", "role": "Pilote"}]
    assert "@" not in json.dumps(rows) and "+33" not in json.dumps(rows)


def test_dod_4_count_by_email_reveals_nothing(crm):
    crm.patch("lib.attio.AttioClient.query", return_value=[person("1"), person("2", email="b@exemple.fr")])
    out = run("count", {"object": "people", "by": "email_addresses"})
    assert out == {"total": 2, "complete": True, "by_email_addresses": {None: 2}}


def test_dod_4_an_email_typed_into_a_text_attribute_is_dropped(crm):
    record = {
        "id": {"record_id": "r1"},
        "values": {
            "description": [{"attribute_type": "text", "value": "Joindre la directrice : d@exemple.fr"}],
            "job_title": [{"attribute_type": "text", "value": "Directrice"}],
        },
    }
    crm.patch("lib.attio.AttioClient.query", return_value=[record])
    assert run("records", {"object": "people"}) == [{"id": "r1", "job_title": "Directrice"}]


@pytest.mark.parametrize(
    "phone",
    [
        "06 12 34 56 78",
        "+33 6 12 34 56 78",
        "01.23.45.67.89",
        "0612345678",
        "+33 (0)6 12 34 56 78",
        "0033 6 12 34 56 78",
    ],
)
def test_dod_4_a_phone_typed_into_a_text_attribute_is_dropped(crm, phone):
    record = {
        "id": {"record_id": "r1"},
        "values": {"description": [{"attribute_type": "text", "value": f"Tél. {phone}"}]},
    }
    crm.patch("lib.attio.AttioClient.query", return_value=[record])
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
        ("count", {"object": "people", "filter": {"telephone": {"$starts_with": "0612"}}}),
        ("records", {"object": "people", "filter": {"email_pro": {"$ends_with": "exemple.fr"}}}),
        ("count", {"object": "people", "filter": {"$and": [{"role": "Pilote"}, {"$not": {"email_pro": "x"}}]}}),
        (
            "entries",
            {
                "list": "sales",
                "filter": {
                    "path": [["sales", "parent_record"], ["people", "telephone"]],
                    "constraints": {"value": "0"},
                },
            },
        ),
    ],
)
def test_dod_4_a_filter_cannot_probe_a_custom_email_or_phone_attribute(crm, method, params):
    attributes = crm.patch("lib.attio.AttioClient.list_attributes")
    attributes.side_effect = lambda target, _: CUSTOM_CONTACT_ATTRIBUTES if target == "objects" else []
    query = crm.patch("lib.attio.AttioClient.query")
    with pytest.raises(AttioInvalidRequest, match="ni sur un email ni sur un téléphone"):
        run(method, params)
    query.assert_not_called()


def test_dod_4_a_filter_on_another_attribute_reaches_attio(crm):
    crm.patch("lib.attio.AttioClient.list_attributes", return_value=CUSTOM_CONTACT_ATTRIBUTES)
    query = crm.patch("lib.attio.AttioClient.query", return_value=[])
    assert run("count", {"object": "people", "filter": {"role": "Pilote"}})["total"] == 0
    assert query.call_args.kwargs["filter"] == {"role": "Pilote"}


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
        ("records", ["object"]),
        (["records"], {}),
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


@pytest.mark.parametrize("status,expected", [(200, (True, "3 objets")), (401, (False, "HTTP 401"))])
def test_dod_6_probe_counts_objects_or_says_the_http_status(mocker, status, expected):
    mocker.patch("web.source_checks.get_source_config", return_value={"api_key": "k"})
    resp = mocker.MagicMock(status_code=status)
    resp.json.return_value = {"data": [{}, {}, {}]}
    mocker.patch("web.source_checks.httpx.get", return_value=resp)
    assert check_attio() == expected


@pytest.mark.parametrize("key,configured", [("k", True), ("${env.ATTIO_API_KEY}", False)])
def test_dod_6_sources_page_lists_attio(mocker, key, configured):
    mocker.patch("web.sources_registry.load_config", return_value={"attio": {"crm": {"api_key": key}}})
    [source] = [s for s in all_sources() if s.slug == "attio"]
    assert source.skill == "attio"
    assert source.check is check_attio
    assert source.configured() is configured
