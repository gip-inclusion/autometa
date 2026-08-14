"""Retry du client Metabase sur les statuts passerelle transitoires (502/503/504) et erreurs réseau."""

import httpx
import pytest

from lib.metabase import MAX_ATTEMPTS, RETRY_DEADLINE_S, MetabaseError
from lib.sources import get_metabase

OK_BODY = {"data": {"cols": [{"name": "n"}], "rows": [[1]]}}


def make_api(mocker):
    mocker.patch("lib.sources.get_source_config", return_value={"url": "http://mb.test", "api_key": "k"})
    mocker.patch("lib.sources.get_default_instance", return_value="stats")
    mocker.patch("lib.metabase.emit_api_signal")
    mocker.patch("lib.metabase.time.sleep")
    return get_metabase(instance="stats")


def response(status, json_body=None, text=""):
    req = httpx.Request("POST", "http://mb.test/api/dataset")
    if json_body is not None:
        return httpx.Response(status, json=json_body, request=req)
    return httpx.Response(status, text=text, request=req)


@pytest.mark.parametrize("status", [502, 503, 504])
def test_retries_on_gateway_status_then_succeeds(mocker, status):
    api = make_api(mocker)
    api._session.request = mocker.Mock(side_effect=[response(status, text="timeout"), response(200, json_body=OK_BODY)])
    result = api.execute_sql("SELECT 1")
    assert result.row_count == 1
    assert api._session.request.call_count == 2


def test_exhausts_retries_on_persistent_504(mocker):
    api = make_api(mocker)
    sleep = mocker.patch("lib.metabase.time.sleep")
    api._session.request = mocker.Mock(return_value=response(504, text="Application Timeout"))
    with pytest.raises(MetabaseError, match="HTTP 504"):
        api.execute_sql("SELECT 1")
    assert api._session.request.call_count == MAX_ATTEMPTS
    assert sleep.call_count == MAX_ATTEMPTS - 1


@pytest.mark.parametrize(
    ("timeout", "expected_attempts"),
    [(60, MAX_ATTEMPTS), (int(RETRY_DEADLINE_S), 1)],
)
def test_does_not_start_an_attempt_that_would_blow_the_deadline(mocker, timeout, expected_attempts):
    # Why: un cron a 300s de budget ; retenter au-delà le fait tuer en plein vol et l'erreur
    # d'origine (le 504) est remplacée par un timeout bien moins diagnosticable.
    api = make_api(mocker)
    api._session.request = mocker.Mock(return_value=response(504, text="Application Timeout"))
    with pytest.raises(MetabaseError, match="HTTP 504"):
        api.execute_sql("SELECT 1", timeout=timeout)
    assert api._session.request.call_count == expected_attempts


@pytest.mark.parametrize("status", [400, 404, 500])
def test_no_retry_on_non_gateway_status(mocker, status):
    api = make_api(mocker)
    api._session.request = mocker.Mock(return_value=response(status, text="err"))
    with pytest.raises(MetabaseError):
        api.get_card(1)
    assert api._session.request.call_count == 1


def test_retries_on_request_error_then_succeeds(mocker):
    api = make_api(mocker)
    req = httpx.Request("POST", "http://mb.test/api/dataset")
    api._session.request = mocker.Mock(
        side_effect=[httpx.ReadTimeout("slow", request=req), response(200, json_body=OK_BODY)]
    )
    result = api.execute_sql("SELECT 1")
    assert result.row_count == 1
    assert api._session.request.call_count == 2
