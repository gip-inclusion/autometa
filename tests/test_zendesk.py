import httpx
import pytest

from lib import sources
from lib.zendesk import (
    TicketResult,
    ZendeskAPI,
    ZendeskError,
    _parse_retry_after,
)


def _mock_response(mocker, *, status_code=200, json_data=None, headers=None, url="https://x/api/v2/x"):
    resp = mocker.MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.json.return_value = json_data or {}
    resp.headers = headers or {}
    resp.text = "" if json_data else "error body"
    resp.url = url
    return resp


@pytest.fixture
def api(mocker):
    mocker.patch("lib.zendesk.time.sleep")
    return ZendeskAPI(subdomain="emplois", email="bot@example.com", token="tk")


@pytest.fixture
def api_no_signal(api, mocker):
    mocker.patch("lib.zendesk.emit_api_signal")
    return api


def test_init_builds_base_url_and_basic_auth(api):
    assert api.base_url == "https://emplois.zendesk.com/api/v2"
    assert api._client.auth is not None
    assert api.instance == "emplois"


def test_close_releases_underlying_client(api, mocker):
    spy = mocker.spy(api._client, "close")
    api.close()
    assert spy.call_count == 1


def test_context_manager_closes_client(mocker):
    mocker.patch("lib.zendesk.time.sleep")
    with ZendeskAPI(subdomain="x", email="e", token="t") as zd:
        spy = mocker.spy(zd._client, "close")
    assert spy.call_count == 1


def test_get_ticket_parses_payload(api_no_signal, mocker):
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
    mocker.patch.object(api_no_signal._client, "get", return_value=_mock_response(mocker, json_data=payload))

    ticket = api_no_signal.get_ticket(42)

    assert ticket.id == 42
    assert ticket.subject == "Bug"
    assert ticket.assignee_id is None
    assert ticket.tags == ["bug", "emplois"]


@pytest.mark.parametrize("status", [400, 403, 404, 500, 502])
def test_get_raises_zendesk_error_on_http_error(api_no_signal, mocker, status):
    mocker.patch.object(api_no_signal._client, "get", return_value=_mock_response(mocker, status_code=status))

    with pytest.raises(ZendeskError) as exc:
        api_no_signal.get_ticket(999)
    assert exc.value.status_code == status
    assert "error body" in exc.value.message
    assert exc.value.args
    assert "Zendesk" in str(exc.value)


def test_get_ticket_comments_uses_sideloaded_roles(api_no_signal, mocker):
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
    mocker.patch.object(api_no_signal._client, "get", return_value=_mock_response(mocker, json_data=payload))

    comments = api_no_signal.get_ticket_comments(42)

    assert [c.author_role for c in comments] == ["end-user", "agent"]
    assert comments[0].body == "Hello"


def test_first_user_reply_returns_user_after_agent(api_no_signal, mocker):
    """End-user message that comes BEFORE any agent message must be skipped."""
    payload = {
        "users": [
            {"id": 1, "role": "end-user"},
            {"id": 2, "role": "agent"},
        ],
        "comments": [
            {"id": 1, "author_id": 1, "plain_body": "Initial", "html_body": "", "public": True, "created_at": "t1"},
            {"id": 2, "author_id": 2, "plain_body": "Agent", "html_body": "", "public": True, "created_at": "t2"},
            {"id": 3, "author_id": 1, "plain_body": "Clarif", "html_body": "", "public": True, "created_at": "t3"},
        ],
    }
    mocker.patch.object(api_no_signal._client, "get", return_value=_mock_response(mocker, json_data=payload))

    reply = api_no_signal.first_user_reply(42)

    assert reply is not None
    assert reply.body == "Clarif"


def test_first_user_reply_returns_none_when_no_agent(api_no_signal, mocker):
    payload = {
        "users": [{"id": 1, "role": "end-user"}],
        "comments": [
            {"id": 1, "author_id": 1, "plain_body": "Hello", "html_body": "", "public": True, "created_at": "t1"},
        ],
    }
    mocker.patch.object(api_no_signal._client, "get", return_value=_mock_response(mocker, json_data=payload))

    assert api_no_signal.first_user_reply(42) is None


def _ticket_payload(tid=1):
    return {
        "ticket": {
            "id": tid,
            "subject": "OK",
            "status": "open",
            "created_at": "t",
            "updated_at": "t",
            "requester_id": 1,
            "assignee_id": None,
            "tags": [],
        }
    }


def _comments_payload():
    return {
        "users": [{"id": 1, "role": "agent"}],
        "comments": [
            {"id": 99, "author_id": 1, "plain_body": "ok", "html_body": "", "public": True, "created_at": "t"},
        ],
    }


def test_iter_tickets_continues_on_per_ticket_error(api_no_signal, mocker):
    responses = [
        _mock_response(mocker, json_data=_ticket_payload(1)),
        _mock_response(mocker, status_code=404),
    ]
    mocker.patch.object(api_no_signal._client, "get", side_effect=responses)

    results = list(api_no_signal.iter_tickets([1, 2]))

    assert isinstance(results[0], TicketResult)
    assert results[0].ticket_id == 1
    assert results[0].ticket.id == 1
    assert results[0].error is None
    assert results[1].ticket_id == 2
    assert results[1].ticket is None
    assert "Zendesk 404" in results[1].error


def test_iter_tickets_with_comments_returns_both(api_no_signal, mocker):
    responses = [
        _mock_response(mocker, json_data=_ticket_payload(1)),
        _mock_response(mocker, json_data=_comments_payload()),
    ]
    mocker.patch.object(api_no_signal._client, "get", side_effect=responses)

    results = list(api_no_signal.iter_tickets([1], with_comments=True))

    assert len(results) == 1
    assert results[0].ticket is not None
    assert results[0].ticket.id == 1
    assert results[0].comments is not None
    assert len(results[0].comments) == 1


def test_get_retries_on_rate_limit(api_no_signal, mocker):
    responses = [
        _mock_response(mocker, status_code=429, headers={"Retry-After": "1"}),
        _mock_response(mocker, json_data=_ticket_payload(1)),
    ]
    mocker.patch.object(api_no_signal._client, "get", side_effect=responses)

    ticket = api_no_signal.get_ticket(1)

    assert ticket.id == 1
    assert api_no_signal._client.get.call_count == 2


def test_get_raises_after_max_429_retries(api_no_signal, mocker):
    """After _MAX_429_RETRIES persistent 429s, the client must give up — no infinite recursion."""
    responses = [
        _mock_response(mocker, status_code=429, headers={"Retry-After": "1"})
        for _ in range(10)
    ]
    mocker.patch.object(api_no_signal._client, "get", side_effect=responses)

    with pytest.raises(ZendeskError) as exc:
        api_no_signal.get_ticket(1)

    assert exc.value.status_code == 429
    assert api_no_signal._client.get.call_count == 4


def test_429_uses_retry_after_value(api_no_signal, mocker):
    sleep = mocker.patch("lib.zendesk.time.sleep")
    responses = [
        _mock_response(mocker, status_code=429, headers={"Retry-After": "7"}),
        _mock_response(mocker, json_data=_ticket_payload(1)),
    ]
    mocker.patch.object(api_no_signal._client, "get", side_effect=responses)

    api_no_signal.get_ticket(1)

    assert any(call.args == (7,) for call in sleep.call_args_list)


@pytest.mark.parametrize(
    "header_value,expected",
    [
        ("30", 30),
        ("0", 0),
        ("-5", 0),
        ("not-a-number", 60),
        (None, 60),
        ("", 60),
        ("Sat, 01 Jan 2026 00:00:00 GMT", 60),
    ],
)
def test_parse_retry_after(header_value, expected):
    assert _parse_retry_after(header_value) == expected


def test_get_emits_api_signal_on_success(api, mocker):
    emit = mocker.patch("lib.zendesk.emit_api_signal")
    mocker.patch.object(
        api._client,
        "get",
        return_value=_mock_response(
            mocker,
            json_data=_ticket_payload(1),
            url="https://emplois.zendesk.com/api/v2/tickets/1",
        ),
    )

    api.get_ticket(1)

    emit.assert_called_once_with(
        source="zendesk",
        instance="emplois",
        url="https://emplois.zendesk.com/api/v2/tickets/1",
    )


def test_get_does_not_emit_signal_on_error(api, mocker):
    emit = mocker.patch("lib.zendesk.emit_api_signal")
    mocker.patch.object(api._client, "get", return_value=_mock_response(mocker, status_code=500))

    with pytest.raises(ZendeskError):
        api.get_ticket(1)

    emit.assert_not_called()


def test_check_auth_returns_user(api_no_signal, mocker):
    payload = {"user": {"id": 1, "role": "agent", "email": "bot@example.com"}}
    mocker.patch.object(api_no_signal._client, "get", return_value=_mock_response(mocker, json_data=payload))

    user = api_no_signal.check_auth()

    assert user["id"] == 1
    assert user["role"] == "agent"


def test_zendesk_error_is_proper_exception():
    err = ZendeskError(404, "Not found")
    assert err.status_code == 404
    assert err.message == "Not found"
    assert str(err) == "Zendesk 404: Not found"
    assert err.args == ("Zendesk 404: Not found",)


def test_get_zendesk_factory_reads_config(mocker):
    mocker.patch.object(
        sources,
        "get_source_config",
        return_value={"subdomain": "emplois", "email": "bot@x.com", "token": "tk"},
    )
    mocker.patch.object(sources, "get_default_instance", return_value="emplois")

    api = sources.get_zendesk()

    assert isinstance(api, ZendeskAPI)
    assert api.base_url == "https://emplois.zendesk.com/api/v2"
    assert api.instance == "emplois"
    sources.get_source_config.assert_called_once_with("zendesk")
