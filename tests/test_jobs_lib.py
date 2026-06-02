"""Tests for the pipometa orchestrator HTTP client."""

import httpx
import pytest

from lib import jobs


@pytest.fixture(autouse=True)
def _pipometa_config(mocker):
    mocker.patch("lib.jobs.config.PIPOMETA_URL", "https://orch.example")
    mocker.patch("lib.jobs.config.PIPOMETA_API_KEY", "pmk_test")
    mocker.patch("lib.jobs.config.PIPOMETA_JOB_DEFINITION_ID", "jobdef-123")


def _fake_response(payload, status=200):
    return httpx.Response(status, json=payload, request=httpx.Request("GET", "https://orch.example"))


def test_list_pipelines_uses_bearer_and_url(mocker):
    req = mocker.patch("httpx.request", return_value=_fake_response([{"id": "p1"}]))
    result = jobs.list_pipelines()
    assert result == [{"id": "p1"}]
    args, kwargs = req.call_args
    assert args == ("GET", "https://orch.example/pipelines")
    assert kwargs["headers"]["Authorization"] == "Bearer pmk_test"
    assert kwargs["timeout"] == 15


def test_create_pipeline_injects_job_definition_id(mocker):
    req = mocker.patch("httpx.request", return_value=_fake_response({"id": "p2"}))
    jobs.create_pipeline("weekly", "Tu es analyste.", {"max_turns": 20})
    payload = req.call_args.kwargs["json"]
    assert payload["name"] == "weekly"
    assert payload["system_prompt"] == "Tu es analyste."
    assert payload["config"]["scaleway_job_definition_id"] == "jobdef-123"
    assert payload["config"]["max_turns"] == 20


def test_trigger_run_one_shot_sends_empty_body(mocker):
    req = mocker.patch("httpx.request", return_value=_fake_response({"id": "r1", "status": "queued"}))
    jobs.trigger_run("p1")
    assert req.call_args.args == ("POST", "https://orch.example/pipelines/p1/runs")
    assert req.call_args.kwargs["json"] == {}


def test_trigger_run_with_input_uri_and_key(mocker):
    req = mocker.patch("httpx.request", return_value=_fake_response({"id": "r1"}))
    jobs.trigger_run("p1", input_uri="s3://pipometa/inputs/x.json", idempotency_key="conv:1")
    assert req.call_args.kwargs["json"] == {
        "input_uri": "s3://pipometa/inputs/x.json",
        "idempotency_key": "conv:1",
    }


def test_list_runs_passes_filters(mocker):
    req = mocker.patch("httpx.request", return_value=_fake_response([]))
    jobs.list_runs(pipeline_id="p1", status="running", limit=10)
    assert req.call_args.kwargs["params"] == {"limit": 10, "pipeline_id": "p1", "status": "running"}


@pytest.mark.parametrize(
    "fn,method,path",
    [
        ("get_run", "GET", "https://orch.example/runs/r1"),
        ("get_run_events", "GET", "https://orch.example/runs/r1/events"),
        ("cancel_run", "POST", "https://orch.example/runs/r1/cancel"),
    ],
)
def test_run_endpoints_route_correctly(mocker, fn, method, path):
    req = mocker.patch("httpx.request", return_value=_fake_response({"id": "r1"}))
    getattr(jobs, fn)("r1")
    assert req.call_args.args == (method, path)


def test_http_error_propagates(mocker):
    mocker.patch("httpx.request", return_value=_fake_response({"detail": "nope"}, status=404))
    with pytest.raises(httpx.HTTPStatusError):
        jobs.get_run("missing")
