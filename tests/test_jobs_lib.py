"""Tests for the autometa-jobs orchestrator HTTP client."""

import httpx
import pytest

from lib import jobs

RUN_ID = "11111111-1111-1111-1111-111111111111"
PIPELINE_ID = "22222222-2222-2222-2222-222222222222"


@pytest.fixture(autouse=True)
def _autometa_jobs_config(mocker):
    mocker.patch("lib.jobs.config.AUTOMETA_JOBS_URL", "https://orch.example")
    mocker.patch("lib.jobs.config.AUTOMETA_JOBS_API_KEY", "pmk_test")
    mocker.patch("lib.jobs.config.AUTOMETA_JOBS_DEFINITION_ID", "jobdef-123")


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
    jobs.trigger_run(PIPELINE_ID)
    assert req.call_args.args == ("POST", f"https://orch.example/pipelines/{PIPELINE_ID}/runs")
    assert req.call_args.kwargs["json"] == {}


def test_trigger_run_with_input_uri_and_key(mocker):
    req = mocker.patch("httpx.request", return_value=_fake_response({"id": "r1"}))
    jobs.trigger_run(PIPELINE_ID, input_uri="s3://pipometa/inputs/x.json", idempotency_key="conv:1")
    assert req.call_args.kwargs["json"] == {
        "input_uri": "s3://pipometa/inputs/x.json",
        "idempotency_key": "conv:1",
    }


def test_list_runs_passes_filters(mocker):
    req = mocker.patch("httpx.request", return_value=_fake_response([]))
    jobs.list_runs(pipeline_id="p1", status="running", limit=10)
    assert req.call_args.kwargs["params"] == {"limit": 10, "pipeline_id": "p1", "status": "running"}


@pytest.mark.parametrize(
    "fn,method,suffix",
    [
        ("get_run", "GET", ""),
        ("get_run_events", "GET", "/events"),
        ("cancel_run", "POST", "/cancel"),
    ],
)
def test_run_endpoints_route_correctly(mocker, fn, method, suffix):
    req = mocker.patch("httpx.request", return_value=_fake_response({"id": "r1"}))
    getattr(jobs, fn)(RUN_ID)
    assert req.call_args.args == (method, f"https://orch.example/runs/{RUN_ID}{suffix}")


def test_get_run_output_returns_text(mocker):
    resp = httpx.Response(200, text="# artefact\nbonjour", request=httpx.Request("GET", "https://orch.example"))
    get = mocker.patch("httpx.get", return_value=resp)
    assert jobs.get_run_output(RUN_ID) == "# artefact\nbonjour"
    assert get.call_args.args == (f"https://orch.example/runs/{RUN_ID}/output",)
    assert get.call_args.kwargs["headers"]["Authorization"] == "Bearer pmk_test"


def test_get_run_output_url_presigns(mocker):
    req = mocker.patch("httpx.request", return_value=_fake_response({"url": "https://s3/x", "expires_in": 120}))
    out = jobs.get_run_output_url(RUN_ID, expires_in=120)
    assert out == {"url": "https://s3/x", "expires_in": 120}
    assert req.call_args.args == ("GET", f"https://orch.example/runs/{RUN_ID}/output")
    assert req.call_args.kwargs["params"] == {"presign": 1, "expires_in": 120}


def test_invalid_id_rejected_before_request(mocker):
    req = mocker.patch("httpx.request")
    with pytest.raises(ValueError):
        jobs.get_run("not-a-uuid")
    req.assert_not_called()


def test_http_error_propagates(mocker):
    mocker.patch("httpx.request", return_value=_fake_response({"detail": "nope"}, status=404))
    with pytest.raises(httpx.HTTPStatusError):
        jobs.get_run(RUN_ID)


def test_create_pipeline_notifies_slack(mocker):
    mocker.patch("httpx.request", return_value=_fake_response({"id": "p1", "name": "weekly"}))
    notify = mocker.patch("lib.jobs.notify_alert_channel")
    jobs.create_pipeline("weekly", "prompt")
    notify.assert_called_once()
    assert "weekly" in notify.call_args.args[0]


def test_trigger_run_notifies_slack(mocker):
    mocker.patch("httpx.request", return_value=_fake_response({"id": "r1", "status": "queued"}))
    mocker.patch("lib.jobs.config.BASE_URL", "https://a.example")
    notify = mocker.patch("lib.jobs.notify_alert_channel")
    jobs.trigger_run(PIPELINE_ID)
    notify.assert_called_once()
    msg = notify.call_args.args[0]
    assert "r1" in msg
    assert "queued" in msg
    assert "https://a.example/jobs/runs/r1" in msg


def test_run_url(mocker):
    mocker.patch("lib.jobs.config.BASE_URL", "https://autometa.example")
    assert jobs.run_url("r1") == "https://autometa.example/jobs/runs/r1"


def test_create_and_run_composes_create_then_trigger(mocker):
    cp = mocker.patch("lib.jobs.create_pipeline", return_value={"id": "p1"})
    tr = mocker.patch("lib.jobs.trigger_run", return_value={"id": "r1", "status": "queued"})
    mocker.patch("lib.jobs.config.BASE_URL", "https://a.example")
    out = jobs.create_and_run("weekly-dora", "You are an analyst.", {"max_turns": 30}, input_uri="s3://x")
    cp.assert_called_once_with("weekly-dora", "You are an analyst.", {"max_turns": 30})
    tr.assert_called_once_with("p1", input_uri="s3://x")
    assert out == {
        "pipeline_id": "p1",
        "run_id": "r1",
        "status": "queued",
        "run_url": "https://a.example/jobs/runs/r1",
    }


def _load_launch_cli():
    import importlib.util
    from pathlib import Path

    path = Path("skills/compose_and_launch_job/scripts/launch_job.py")
    spec = importlib.util.spec_from_file_location("launch_job_cli", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_launch_cli_reads_prompt_and_launches(mocker, tmp_path, capsys):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("You are a Dora analyst. Download the data and answer X.")
    car = mocker.patch("lib.jobs.create_and_run", return_value={"run_url": "https://a/jobs/runs/r1", "run_id": "r1"})
    rc = _load_launch_cli().main([
        "--name",
        "dora-weekly",
        "--system-prompt-file",
        str(prompt_file),
        "--max-turns",
        "30",
        "--allowed-tools",
        "Bash,Read",
    ])
    assert rc == 0
    assert car.call_args.args[0] == "dora-weekly"
    assert car.call_args.args[1] == "You are a Dora analyst. Download the data and answer X."
    assert car.call_args.args[2] == {"max_turns": 30, "allowed_tools": ["Bash", "Read"]}
    assert "r1" in capsys.readouterr().out


def test_launch_cli_passes_output_format(mocker, tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Emit a CSV.")
    car = mocker.patch("lib.jobs.create_and_run", return_value={"run_url": "u", "run_id": "r1"})
    rc = _load_launch_cli().main([
        "--name",
        "dora-csv",
        "--system-prompt-file",
        str(prompt_file),
        "--output-format",
        "csv",
    ])
    assert rc == 0
    assert car.call_args.args[2] == {"output_format": "csv"}


def test_launch_cli_orchestrator_error_returns_1(mocker, tmp_path, capsys):
    prompt_file = tmp_path / "p.txt"
    prompt_file.write_text("x")
    mocker.patch(
        "lib.jobs.create_and_run",
        side_effect=httpx.ConnectError("down", request=httpx.Request("POST", "http://x")),
    )
    rc = _load_launch_cli().main(["--name", "n", "--system-prompt-file", str(prompt_file)])
    assert rc == 1
    assert "orchestrator error" in capsys.readouterr().err
