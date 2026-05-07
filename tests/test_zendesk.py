import httpx
import pytest

from lib.zendesk import ZendeskAPI, ZendeskError


def _mock_response(mocker, *, status_code=200, json_data=None, headers=None):
    resp = mocker.MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.json.return_value = json_data or {}
    resp.headers = headers or {}
    resp.text = "" if json_data else "error body"
    return resp


@pytest.fixture
def api(mocker):
    mocker.patch("lib.zendesk.time.sleep")
    return ZendeskAPI(subdomain="emplois", email="bot@example.com", token="tk")


def test_init_builds_base_url_and_basic_auth(api):
    assert api.base_url == "https://emplois.zendesk.com/api/v2"
    assert api._client.auth is not None


def test_get_ticket_parses_payload(api, mocker):
    payload = {
        "ticket": {
            "id": 42,
            "subject": "Bug",
            "status": "open",
            "created_at": "2026-01-01T10:00:00Z",
            "updated_at": "2026-01-02T10:00:00Z",
            "requester_id": 7,
            "assignee_id": None,
            "tags": ["bug", "emplois"],
        }
    }
    mocker.patch.object(api._client, "get", return_value=_mock_response(mocker, json_data=payload))

    ticket = api.get_ticket(42)

    assert ticket.id == 42
    assert ticket.subject == "Bug"
    assert ticket.assignee_id is None
    assert ticket.tags == ["bug", "emplois"]


def test_get_ticket_raises_on_http_error(api, mocker):
    mocker.patch.object(api._client, "get", return_value=_mock_response(mocker, status_code=404))

    with pytest.raises(ZendeskError) as exc:
        api.get_ticket(999)
    assert exc.value.status_code == 404


def test_get_ticket_comments_uses_sideloaded_roles(api, mocker):
    payload = {
        "users": [
            {"id": 1, "role": "agent"},
            {"id": 2, "role": "end-user"},
        ],
        "comments": [
            {
                "id": 100,
                "author_id": 2,
                "plain_body": "Hello",
                "html_body": "<p>Hello</p>",
                "public": True,
                "created_at": "2026-01-01T10:00:00Z",
            },
            {
                "id": 101,
                "author_id": 1,
                "plain_body": "Hi back",
                "html_body": "<p>Hi back</p>",
                "public": True,
                "created_at": "2026-01-01T11:00:00Z",
            },
        ],
    }
    mocker.patch.object(api._client, "get", return_value=_mock_response(mocker, json_data=payload))

    comments = api.get_ticket_comments(42)

    assert [c.author_role for c in comments] == ["end-user", "agent"]
    assert comments[0].body == "Hello"


def test_first_user_reply_returns_user_after_agent(api, mocker):
    """End-user message that comes BEFORE any agent message must be skipped."""
    payload = {
        "users": [
            {"id": 1, "role": "end-user"},
            {"id": 2, "role": "agent"},
        ],
        "comments": [
            {
                "id": 1,
                "author_id": 1,
                "plain_body": "Initial request",
                "html_body": "",
                "public": True,
                "created_at": "t1",
            },
            {
                "id": 2,
                "author_id": 2,
                "plain_body": "Agent question",
                "html_body": "",
                "public": True,
                "created_at": "t2",
            },
            {
                "id": 3,
                "author_id": 1,
                "plain_body": "Clarification",
                "html_body": "",
                "public": True,
                "created_at": "t3",
            },
        ],
    }
    mocker.patch.object(api._client, "get", return_value=_mock_response(mocker, json_data=payload))

    reply = api.first_user_reply(42)

    assert reply is not None
    assert reply.body == "Clarification"


def test_first_user_reply_returns_none_when_no_agent(api, mocker):
    payload = {
        "users": [{"id": 1, "role": "end-user"}],
        "comments": [
            {"id": 1, "author_id": 1, "plain_body": "Hello", "html_body": "", "public": True, "created_at": "t1"},
        ],
    }
    mocker.patch.object(api._client, "get", return_value=_mock_response(mocker, json_data=payload))

    assert api.first_user_reply(42) is None


def test_iter_tickets_continues_on_per_ticket_error(api, mocker):
    ticket_payload = {
        "ticket": {
            "id": 1,
            "subject": "OK",
            "status": "open",
            "created_at": "t",
            "updated_at": "t",
            "requester_id": 1,
            "assignee_id": None,
            "tags": [],
        }
    }
    responses = [
        _mock_response(mocker, json_data=ticket_payload),
        _mock_response(mocker, status_code=404),
    ]
    mocker.patch.object(api._client, "get", side_effect=responses)

    results = list(api.iter_tickets([1, 2]))

    assert results[0]["ticket"].id == 1
    assert results[1]["ticket_id"] == 2
    assert "Zendesk 404" in results[1]["error"]


def test_get_retries_on_rate_limit(api, mocker):
    ticket_payload = {
        "ticket": {
            "id": 1,
            "subject": "OK",
            "status": "open",
            "created_at": "t",
            "updated_at": "t",
            "requester_id": 1,
            "assignee_id": None,
            "tags": [],
        }
    }
    responses = [
        _mock_response(mocker, status_code=429, headers={"Retry-After": "1"}),
        _mock_response(mocker, json_data=ticket_payload),
    ]
    mocker.patch.object(api._client, "get", side_effect=responses)

    ticket = api.get_ticket(1)

    assert ticket.id == 1
    assert api._client.get.call_count == 2


def test_get_zendesk_factory_reads_config(mocker):
    from lib import sources

    mocker.patch.object(
        sources,
        "get_source_config",
        return_value={"subdomain": "emplois", "email": "bot@x.com", "token": "tk"},
    )

    api = sources.get_zendesk()

    assert isinstance(api, ZendeskAPI)
    assert api.base_url == "https://emplois.zendesk.com/api/v2"
    sources.get_source_config.assert_called_once_with("zendesk")
