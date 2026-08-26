import httpx
import pytest

from lib.tally import TallyClient, TallyError, workspaces_summary
from web.selftest import _check_tally


def make_client(mocker, api_key="tly-test"):
    client = TallyClient(api_key=api_key)
    mocker.patch("lib.tally.emit_api_signal")
    return client


def json_resp(mocker, payload, status=200):
    resp = mocker.MagicMock(status_code=status)
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_missing_api_key_raises(mocker):
    mocker.patch("lib.tally.config.TALLY_API_KEY", None)
    with pytest.raises(TallyError):
        TallyClient(api_key=None)


def test_get_returns_json_and_emits_signal(mocker):
    client = make_client(mocker)
    emit = mocker.patch("lib.tally.emit_api_signal")
    mocker.patch.object(client._session, "get", return_value=json_resp(mocker, {"items": [{"id": "f1"}]}))

    data = client.list_forms()

    assert data == {"items": [{"id": "f1"}]}
    emit.assert_called_once()
    assert emit.call_args.kwargs["source"] == "tally"


def test_http_error_raises_tally_error(mocker):
    client = make_client(mocker)
    resp = mocker.MagicMock()
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "forbidden",
        request=httpx.Request("GET", "https://api.tally.so/forms"),
        response=httpx.Response(403, request=httpx.Request("GET", "https://api.tally.so/forms")),
    )
    mocker.patch.object(client._session, "get", return_value=resp)
    with pytest.raises(TallyError, match="403"):
        client.list_forms()


def test_request_error_raises_tally_error(mocker):
    client = make_client(mocker)
    mocker.patch.object(client._session, "get", side_effect=httpx.ConnectError("boom"))
    with pytest.raises(TallyError):
        client.get_form("f1")


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({}, {"page": 1, "limit": 50}),
        ({"filter": "completed"}, {"page": 1, "limit": 50, "filter": "completed"}),
        (
            {"start_date": "2026-01-01", "end_date": "2026-06-30"},
            {"page": 1, "limit": 50, "startDate": "2026-01-01", "endDate": "2026-06-30"},
        ),
        ({"after_id": "s9", "page": 2, "limit": 500}, {"page": 2, "limit": 500, "afterId": "s9"}),
    ],
)
def test_list_submissions_param_mapping(mocker, kwargs, expected):
    client = make_client(mocker)
    get = mocker.patch.object(client, "_get", return_value={})
    client.list_submissions("f1", **kwargs)
    get.assert_called_once_with("/forms/f1/submissions", params=expected)


def test_iter_submissions_follows_has_more(mocker):
    client = make_client(mocker)
    mocker.patch.object(
        client,
        "list_submissions",
        side_effect=[
            {"submissions": [{"id": "a"}], "hasMore": True},
            {"submissions": [{"id": "b"}], "hasMore": False},
        ],
    )
    rows = list(client.iter_submissions("f1"))
    assert [r["id"] for r in rows] == ["a", "b"]


def test_iter_submissions_caps_pages(mocker):
    client = make_client(mocker)
    ls = mocker.patch.object(client, "list_submissions", return_value={"submissions": [{"id": "x"}], "hasMore": True})
    warn = mocker.patch("lib.tally.logger.warning")
    rows = list(client.iter_submissions("f1", max_pages=3))
    assert len(rows) == 3
    assert ls.call_count == 3
    warn.assert_called_once()


def test_list_workspaces_calls_endpoint(mocker):
    client = make_client(mocker)
    get = mocker.patch.object(client, "_get", return_value={"items": [{"id": "w1", "name": "GPS"}]})

    assert client.list_workspaces() == {"items": [{"id": "w1", "name": "GPS"}]}
    get.assert_called_once_with("/workspaces")


def test_workspaces_summary_keeps_name_and_member_count(mocker):
    client = make_client(mocker)
    mocker.patch.object(
        client,
        "list_workspaces",
        return_value={"items": [{"id": "w1", "name": "GPS", "members": [{"id": "u1"}, {"id": "u2"}]}, {"id": "w2"}]},
    )

    assert workspaces_summary(client) == [
        {"id": "w1", "name": "GPS", "members": 2},
        {"id": "w2", "name": None, "members": 0},
    ]


def test_check_tally_not_set(mocker):
    mocker.patch("web.selftest.config.TALLY_API_KEY", None)
    ok, msg = _check_tally()
    assert ok is False and "not set" in msg


def test_check_tally_reachable(mocker):
    mocker.patch("web.selftest.config.TALLY_API_KEY", "tly-x")
    resp = mocker.MagicMock(status_code=200)
    resp.json.return_value = {"total": 3}
    mocker.patch("web.selftest.httpx.get", return_value=resp)
    ok, msg = _check_tally()
    assert ok is True and "3 forms" in msg


def test_check_tally_http_error(mocker):
    mocker.patch("web.selftest.config.TALLY_API_KEY", "tly-x")
    mocker.patch("web.selftest.httpx.get", return_value=mocker.MagicMock(status_code=503))

    ok, msg = _check_tally()
    assert ok is False and msg == "HTTP 503"


def test_client_context_manager_closes_session(mocker):
    client = make_client(mocker)
    mocker.patch.object(client._session, "close")

    with client as entered:
        assert entered is client
    client._session.close.assert_called_once()
