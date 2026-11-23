import itertools
import json
import sys

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib import brevo, dashboard_api
from lib.brevo import EVENT_PAGE, BrevoClient, BrevoError, BrevoInvalidRequest
from lib.query import CallerType, execute_query
from web.routes import query as query_route
from web.routes.query import validate_query_request
from web.source_checks import check_brevo
from web.sources_registry import all_sources


def json_resp(mocker, payload):
    resp = mocker.MagicMock(status_code=200, content=b"{}")
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def client(mocker):
    mocker.patch("lib.brevo.emit_api_signal")
    return BrevoClient("emplois", api_key="xkeysib-test")


@pytest.fixture
def account(mocker):
    """Un compte Brevo configuré, sans appel réseau tant que le test ne répond pas à la place de Brevo."""
    mocker.patch("lib.brevo.emit_api_signal")
    mocker.patch("lib.brevo.get_source_config", return_value={"api_key": "k"})
    return mocker


def answer(mocker, client, *payloads):
    return mocker.patch.object(client._session, "get", side_effect=[json_resp(mocker, p) for p in payloads])


def event(tid, subject, date):
    return {"email": "x@exemple.fr", "messageId": "<m@exemple.fr>", "templateId": tid, "subject": subject, "date": date}


def test_missing_key_raises(mocker):
    mocker.patch("lib.brevo.get_source_config", side_effect=ValueError("Environment variable X not set"))
    with pytest.raises(BrevoError, match="emplois"):
        BrevoClient("emplois")


def test_dod_1_templates_keep_name_subject_and_state(mocker, client):
    template = {
        "id": 101,
        "name": "Le saviez-vous",
        "subject": "Le saviez-vous ?",
        "isActive": True,
        "tag": "onboarding",
        "sender": {"name": "La plateforme", "email": "noreply@exemple.fr"},
        "replyTo": "support@exemple.fr",
        "toField": "{{contact.EMAIL}}",
        "htmlContent": "<p>Bonjour</p>",
        "createdAt": "2026-01-01",
        "modifiedAt": "2026-02-01",
    }
    answer(mocker, client, {"templates": [template], "count": 1})
    assert client.list_templates() == [
        {
            "id": 101,
            "name": "Le saviez-vous",
            "subject": "Le saviez-vous ?",
            "isActive": True,
            "tag": "onboarding",
            "sender": "La plateforme",
            "createdAt": "2026-01-01",
            "modifiedAt": "2026-02-01",
        }
    ]


def test_dod_1_cron_facade_reaches_brevo(mocker):
    execute = mocker.patch("lib.dashboard_api.query.execute_brevo_query")
    dashboard_api.query_brevo("emplois", "templates")
    assert execute.call_args.kwargs == {
        "instance": "emplois",
        "method": "templates",
        "caller": CallerType.APP,
        "params": None,
        "timeout": 60,
    }


@pytest.mark.parametrize(
    "data,refused",
    [
        ({"source": "brevo", "instance": "emplois", "method": "templates"}, False),
        ({"source": "brevo", "instance": "emplois"}, True),
        ({"source": "brevo", "method": "templates"}, True),
    ],
)
def test_dod_1_api_query_requires_instance_and_method(data, refused):
    error = validate_query_request(data)
    assert (error or "").startswith("instance and method are required for brevo") is refused


def test_dod_1_api_query_lists_templates(account):
    account.patch("lib.brevo.BrevoClient.list_templates", return_value=[{"id": 1}])
    result = execute_query(source="brevo", instance="dora", caller=CallerType.APP, method="templates")
    assert result.success is True
    assert result.data == [{"id": 1}]


def test_dod_2_campaigns_carry_their_statistics(mocker, client):
    campaign = {
        "id": 201,
        "name": "Invitation",
        "status": "sent",
        "recipients": {"lists": [301]},
        "sender": {"name": "Expéditeur", "email": "expediteur@exemple.fr"},
        "statistics": {"globalStats": {"sent": 994, "delivered": 992, "uniqueClicks": 83, "appleMppOpens": 7}},
    }
    get = answer(mocker, client, {"campaigns": [campaign]})
    [row] = client.list_campaigns(status="sent")
    assert row["listIds"] == [301]
    assert row["stats"] == {"sent": 994, "delivered": 992, "uniqueClicks": 83}
    params = get.call_args.kwargs["params"]
    assert params["status"] == "sent" and params["sort"] == "desc" and params["excludeHtmlContent"] == "true"


def test_dod_3_sends_are_counted_by_template(mocker, client):
    page = [event(102, "Traiter les candidatures", "2026-11-21T02:46")] * (EVENT_PAGE - 1) + [
        event(101, "Le saviez-vous ?", "2026-11-21T02:35")
    ]
    get = answer(mocker, client, {"events": page}, {"events": [event(101, "Ancien objet", "2026-11-01T10:00")]})
    out = client.sends_by_template(days=30)
    assert out["truncated"] is False
    assert out["templates"] == [
        {"templateId": 102, "count": EVENT_PAGE - 1, "lastDate": "2026-11-21T02:46"},
        {"templateId": 101, "count": 2, "lastDate": "2026-11-21T02:35"},
    ]
    assert get.call_args.kwargs["params"]["days"] == 30
    assert get.call_args.kwargs["params"]["event"] == "requests"


def test_dod_3_window_is_capped_at_ninety_days(mocker, client):
    get = answer(mocker, client, {"events": []})
    assert client.sends_by_template(days=500)["days"] == 90
    assert get.call_args.kwargs["params"]["days"] == 90
    with pytest.raises(BrevoInvalidRequest):
        client.sends_by_template(days="trente")


def test_dod_3_page_cap_is_flagged(mocker, client):
    mocker.patch("lib.brevo.MAX_PAGES", 2)
    full = {"events": [{"templateId": 1, "date": "d"}] * EVENT_PAGE}
    answer(mocker, client, full, full)
    assert client.sends_by_template()["truncated"] is True


def test_dod_3_slow_brevo_stops_at_the_time_budget(mocker, client):
    mocker.patch("lib.brevo.time.monotonic", side_effect=itertools.count(step=client.timeout + 1))
    full = {"events": [{"templateId": 1, "date": "d"}] * EVENT_PAGE}
    get = answer(mocker, client, full, full)
    out = client.sends_by_template()
    assert out["truncated"] is True
    assert out["templates"] == [{"templateId": 1, "count": EVENT_PAGE, "lastDate": "d"}]
    assert get.call_count == 1


def test_dod_4_no_address_ever_comes_out(mocker, client):
    answer(mocker, client, {"events": [event(102, "Traiter les candidatures", "1")] * 5})
    assert "@" not in json.dumps(client.sends_by_template())


def test_dod_4_rendered_subject_of_a_template_never_comes_out(mocker, client):
    answer(mocker, client, {"events": [event(102, "Rejoindre STRUCTURE A, invité par a@exemple.fr", "1")] * 6})
    out = json.dumps(client.sends_by_template())
    assert "STRUCTURE" not in out and "@" not in out


def test_dod_4_frequent_subject_with_an_address_is_merged(mocker, client):
    answer(mocker, client, {"events": [event(None, "Relance pour b@exemple.fr", "1")] * 6})
    rows = client.sends_by_template()["templates"]
    assert rows == [{"templateId": None, "count": 6, "subject": None, "lastDate": "1", "subjects": 1}]


def test_dod_4_addresses_are_masked_in_html_content(mocker, client):
    template = {"id": 1, "htmlContent": '<a href="mailto:support@exemple.fr">support@exemple.fr</a>'}
    answer(mocker, client, {"templates": [template]})
    [row] = client.list_templates(with_content=True)
    assert "@" not in row["htmlContent"]
    assert "[adresse masquée]" in row["htmlContent"]


def test_dod_4_addresses_are_masked_in_text_fields(mocker, client):
    campaign = {
        "id": 2,
        "name": "Relance a@exemple.fr",
        "subject": "Écrivez à b@exemple.fr",
        "previewText": "Contact : c@exemple.fr",
        "tag": "d@exemple.fr",
    }
    answer(mocker, client, {"campaigns": [campaign]})
    [row] = client.list_campaigns()
    assert "@" not in json.dumps(row)
    assert row["subject"] == "Écrivez à [adresse masquée]"


def test_dod_4_rare_subjects_are_merged_into_one_line(mocker, client):
    events = [{"templateId": None, "subject": "Votre demande a été acceptée", "date": "3"}] * 5 + [
        {"subject": "Rappel : rejoindre STRUCTURE A sur DORA", "date": "2"},
        {"subject": "Rappel : rejoindre STRUCTURE B sur DORA", "date": "1"},
        {"subject": "Rappel : rejoindre STRUCTURE B sur DORA", "date": "1"},
    ]
    answer(mocker, client, {"events": events})
    rows = client.sends_by_template()["templates"]
    assert [(r["templateId"], r["subject"], r["count"]) for r in rows] == [
        (None, "Votre demande a été acceptée", 5),
        (None, None, 3),
    ]
    assert rows[1]["subjects"] == 2 and rows[1]["lastDate"] == "2"
    assert "STRUCTURE" not in json.dumps(rows)


def test_dod_4_emails_without_subject_join_the_merged_line(mocker, client):
    events = [{"templateId": None, "date": "2"}] * 5 + [{"subject": "Rappel : rejoindre STRUCTURE A", "date": "1"}]
    answer(mocker, client, {"events": events})
    rows = client.sends_by_template()["templates"]
    assert rows == [{"templateId": None, "count": 6, "subject": None, "lastDate": "2", "subjects": 2}]


@pytest.mark.parametrize(
    "method,params",
    [
        ("contacts", {}),
        ("lists", {}),
        ("report", {}),
        ("templates", {"limit": 5}),
        ("sends_by_template", {"event": "delivered"}),
        ("sends_by_template", {"days": "trente"}),
        ("templates", {"with_content": "false"}),
        ("campaigns", {"status": 3}),
        ("templates", ["with_content"]),
        (["templates"], {}),
    ],
)
def test_dod_5_unplanned_reads_are_refused_before_any_call(account, method, params):
    get = account.patch("httpx.Client.get")
    with pytest.raises(BrevoInvalidRequest):
        brevo.run("emplois", method, params)
    get.assert_not_called()


def test_a_non_json_answer_is_a_brevo_error(mocker, client):
    resp = json_resp(mocker, None)
    resp.json.side_effect = ValueError("not json")
    mocker.patch.object(client._session, "get", return_value=resp)
    with pytest.raises(BrevoError, match="JSON"):
        client.list_templates()


@pytest.mark.parametrize(
    "status,message",
    [
        (401, "unrecognised IP address 192.0.2.1"),
        (401, "Key not found"),
        (429, "Too many requests"),
        (500, "Internal error"),
    ],
)
def test_an_http_error_keeps_the_brevo_message(mocker, client, status, message):
    request = httpx.Request("GET", f"{brevo.BASE_URL}/smtp/templates")
    resp = httpx.Response(status, json={"code": "error", "message": message}, request=request)
    mocker.patch.object(client._session, "get", return_value=resp)
    with pytest.raises(BrevoError, match=f"HTTP {status}.*{message}"):
        client.list_templates()


def test_dod_5_refusal_says_what_is_allowed_through_api_query():
    result = execute_query(source="brevo", instance="emplois", caller=CallerType.APP, method="contacts")
    assert result.success is False
    assert result.invalid_request is True
    assert "templates" in result.error and "campaigns" in result.error


def test_dod_5_refused_parameter_lists_the_allowed_ones(account):
    with pytest.raises(BrevoInvalidRequest) as refus:
        brevo.run("emplois", "campaigns", {"limit": 5})
    assert "status" in str(refus.value) and "with_content" in str(refus.value)


@pytest.mark.parametrize("instance", ["_default", "inconnu", None])
def test_dod_5_unknown_account_is_refused_with_the_declared_ones(account, mocker, instance):
    mocker.patch("lib.brevo.get_default_instance", return_value=None)
    get = account.patch("httpx.Client.get")
    with pytest.raises(BrevoInvalidRequest, match="marketing, emplois, dora"):
        brevo.run(instance, "templates")
    get.assert_not_called()


def test_dod_5_unknown_account_does_not_raise_through_the_facade():
    result = dashboard_api.query_brevo("_default", "templates")
    assert (result.success, result.invalid_request) == (False, True)
    assert "marketing, emplois, dora" in result.error


def test_dod_5_unknown_account_is_a_400_on_api_query():
    app = FastAPI()
    app.include_router(query_route.router)
    response = TestClient(app).post(
        "/api/query", json={"source": "brevo", "instance": "_default", "method": "templates"}
    )
    assert response.status_code == 400
    assert "marketing, emplois, dora" in response.json()["error"]


def test_dod_5_api_query_without_method_lists_the_methods():
    error = validate_query_request({"source": "brevo", "instance": "emplois"})
    assert "templates" in error and "sends_by_template" in error


@pytest.mark.parametrize(
    "args,method,kwargs",
    [
        (["--templates"], "list_templates", {"with_content": False}),
        (["--campaigns"], "list_campaigns", {}),
        (["--campaigns", "--status", "sent"], "list_campaigns", {"status": "sent"}),
        (["--sends"], "sends_by_template", {"days": 30}),
    ],
)
def test_dod_6_agent_script_runs_each_command(account, capsys, monkeypatch, args, method, kwargs):
    from skills.brevo.scripts import query as script

    read = account.patch(f"lib.brevo.BrevoClient.{method}", return_value=[{"id": 1, "name": "Bienvenue"}])
    monkeypatch.setattr(sys, "argv", ["query.py", "--instance", "emplois", *args])
    script.main()
    assert json.loads(capsys.readouterr().out) == [{"id": 1, "name": "Bienvenue"}]
    read.assert_called_once_with(**kwargs)


def test_dod_6_agent_script_reads_the_default_account_of_the_config(account, monkeypatch):
    from skills.brevo.scripts import query as script

    account.patch("lib.brevo.get_default_instance", return_value="dora")
    read = account.patch.object(BrevoClient, "list_templates", autospec=True, return_value=[])
    monkeypatch.setattr(sys, "argv", ["query.py", "--templates"])
    script.main()
    assert read.call_args.args[0].instance == "dora"


@pytest.mark.parametrize(
    "status,payload,expected",
    [
        (200, {"count": 41, "templates": [{}]}, (True, "41 modèles")),
        (401, {"code": "unauthorized", "message": "Key not found"}, (False, "HTTP 401")),
    ],
)
def test_dod_6_probe_counts_templates_or_says_it_failed(mocker, status, payload, expected):
    mocker.patch("web.source_checks.get_source_config", return_value={"api_key": "k"})
    resp = mocker.MagicMock(status_code=status)
    resp.json.return_value = payload
    get = mocker.patch("web.source_checks.httpx.get", return_value=resp)
    assert check_brevo("emplois") == expected
    assert get.call_args.kwargs["headers"]["api-key"] == "k"


def test_dod_6_sources_page_lists_each_account(mocker):
    mocker.patch(
        "web.sources_registry.list_instances",
        side_effect=lambda s: ["marketing", "emplois", "dora"] if s == "brevo" else [],
    )
    slugs = {s.slug: s for s in all_sources()}
    assert {"brevo-marketing", "brevo-emplois", "brevo-dora"} <= set(slugs)
    assert slugs["brevo-dora"].skill == "brevo"
