"""Tests for the autometa-jobs proxy + page routes."""

import httpx
import pytest

BAD_IDS = ["not-a-uuid", "..etc", "x" * 40, "short"]
GOOD_ID = "11111111-1111-1111-1111-111111111111"


def test_create_pipeline_proxies_to_lib(client, mocker):
    create = mocker.patch("web.routes.jobs.jobs.create_pipeline", return_value={"id": "p1", "name": "weekly"})
    r = client.post("/api/jobs/pipelines", json={"name": "weekly", "system_prompt": "Tu es analyste."})
    assert r.status_code == 200
    assert r.json()["id"] == "p1"
    create.assert_called_once_with("weekly", "Tu es analyste.", None)


def test_create_pipeline_requires_name_and_prompt(client, mocker):
    mocker.patch("web.routes.jobs.jobs.create_pipeline")
    r = client.post("/api/jobs/pipelines", json={"name": "", "system_prompt": ""})
    assert r.status_code == 400


def test_trigger_run_one_shot(client, mocker):
    trig = mocker.patch("web.routes.jobs.jobs.trigger_run", return_value={"id": "r1", "status": "queued"})
    r = client.post(f"/api/jobs/pipelines/{GOOD_ID}/runs", json={})
    assert r.status_code == 200
    trig.assert_called_once_with(GOOD_ID, input_uri=None, idempotency_key=None)


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/jobs/runs/{id}"),
        ("get", "/api/jobs/runs/{id}/events"),
        ("get", "/api/jobs/runs/{id}/output"),
        ("post", "/api/jobs/runs/{id}/cancel"),
        ("post", "/api/jobs/pipelines/{id}/runs"),
        ("get", "/jobs/pipelines/{id}"),
    ],
)
@pytest.mark.parametrize("bad", BAD_IDS)
def test_id_routes_reject_bad_id(client, method, path, bad):
    assert getattr(client, method)(path.format(id=bad)).status_code == 422


def test_run_status_proxies(client, mocker):
    mocker.patch("web.routes.jobs.jobs.get_run", return_value={"id": "r1", "status": "running"})
    r = client.get(f"/api/jobs/runs/{GOOD_ID}")
    assert r.status_code == 200
    assert r.json()["status"] == "running"


def test_run_events_proxies(client, mocker):
    mocker.patch("web.routes.jobs.jobs.get_run_events", return_value=[{"seq": 0, "event_type": "dispatched"}])
    r = client.get(f"/api/jobs/runs/{GOOD_ID}/events")
    assert r.status_code == 200
    assert r.json()[0]["event_type"] == "dispatched"


def test_cancel_proxies(client, mocker):
    mocker.patch("web.routes.jobs.jobs.cancel_run", return_value={"id": "r1", "status": "cancelled"})
    r = client.post(f"/api/jobs/runs/{GOOD_ID}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_run_output_proxies_content(client, mocker):
    mocker.patch("web.routes.jobs.jobs.get_run_output", return_value="# artefact\nbonjour")
    r = client.get(f"/api/jobs/runs/{GOOD_ID}/output")
    assert r.status_code == 200
    assert r.text == "# artefact\nbonjour"


def test_run_output_download_returns_url(client, mocker):
    mocker.patch(
        "web.routes.jobs.jobs.get_run_output_url", return_value={"url": "https://s3/x", "expires_in": 3600}
    )
    r = client.get(f"/api/jobs/runs/{GOOD_ID}/output?download=1")
    assert r.status_code == 200
    assert r.json()["url"] == "https://s3/x"


def test_orchestrator_unreachable_returns_502(client, mocker):
    mocker.patch(
        "web.routes.jobs.jobs.get_run",
        side_effect=httpx.ConnectError("down", request=httpx.Request("GET", "http://x")),
    )
    r = client.get(f"/api/jobs/runs/{GOOD_ID}")
    assert r.status_code == 502


def test_jobs_page_renders(client, mocker):
    mocker.patch(
        "web.routes.jobs.jobs.list_pipelines", return_value=[{"id": "p1", "name": "weekly", "system_prompt": "x"}]
    )
    mocker.patch(
        "web.routes.jobs.jobs.list_runs", return_value=[{"id": "r1", "status": "completed", "pipeline_id": "p1"}]
    )
    r = client.get("/jobs")
    assert r.status_code == 200
    assert "weekly" in r.text


def test_jobs_page_nests_runs_and_shows_download(client, mocker):
    mocker.patch(
        "web.routes.jobs.jobs.list_pipelines",
        return_value=[{"id": "p1", "name": "weekly", "system_prompt": "Tu es analyste.", "created_at": "2026-06-01T10:00:00+00:00"}],
    )
    mocker.patch(
        "web.routes.jobs.jobs.list_runs",
        return_value=[
            {"id": "aaaaaaaa-0000-0000-0000-000000000001", "status": "completed", "pipeline_id": "p1", "created_at": "2026-06-03T15:14:00+00:00"},
            {"id": "bbbbbbbb-0000-0000-0000-000000000002", "status": "running", "pipeline_id": "p1", "created_at": "2026-06-03T16:00:00+00:00"},
        ],
    )
    r = client.get("/jobs")
    assert r.status_code == 200
    assert "2 runs" in r.text  # run count badge on the pipeline
    assert "aaaaaaaa" in r.text  # nested run, short id
    assert "Télécharger" in r.text
    # download button only on the completed run, not the running one
    assert r.text.count("data-run=") == 1


def test_jobs_page_selects_most_recent_by_default(client, mocker):
    mocker.patch(
        "web.routes.jobs.jobs.list_pipelines",
        return_value=[
            {"id": "11111111-1111-1111-1111-111111111111", "name": "alpha", "system_prompt": "PROMPT_ALPHA", "created_at": "2026-06-01T00:00:00+00:00"},
            {"id": "22222222-2222-2222-2222-222222222222", "name": "beta", "system_prompt": "PROMPT_BETA", "created_at": "2026-06-02T00:00:00+00:00"},
        ],
    )
    mocker.patch("web.routes.jobs.jobs.list_runs", return_value=[])
    r = client.get("/jobs")
    assert r.status_code == 200
    # beta is newer → selected → its prompt rendered in the detail pane; alpha's is not
    assert "PROMPT_BETA" in r.text
    assert "PROMPT_ALPHA" not in r.text


def test_jobs_pipeline_page_selects_that_pipeline(client, mocker):
    mocker.patch(
        "web.routes.jobs.jobs.list_pipelines",
        return_value=[
            {"id": "11111111-1111-1111-1111-111111111111", "name": "alpha", "system_prompt": "PROMPT_ALPHA", "created_at": "2026-06-01T00:00:00+00:00"},
            {"id": "22222222-2222-2222-2222-222222222222", "name": "beta", "system_prompt": "PROMPT_BETA", "created_at": "2026-06-02T00:00:00+00:00"},
        ],
    )
    mocker.patch("web.routes.jobs.jobs.list_runs", return_value=[])
    r = client.get("/jobs/pipelines/11111111-1111-1111-1111-111111111111")
    assert r.status_code == 200
    assert "PROMPT_ALPHA" in r.text  # explicitly selected pipeline's prompt
    assert "PROMPT_BETA" not in r.text
    assert "tm-list-item active" in r.text  # selected row highlighted


def test_jobs_page_survives_orchestrator_down(client, mocker):
    mocker.patch(
        "web.routes.jobs.jobs.list_pipelines",
        side_effect=httpx.ConnectError("down", request=httpx.Request("GET", "http://x")),
    )
    r = client.get("/jobs")
    assert r.status_code == 200
    assert "indisponible" in r.text


def test_run_detail_page_renders(client):
    r = client.get(f"/jobs/runs/{GOOD_ID}")
    assert r.status_code == 200
    assert GOOD_ID in r.text


@pytest.mark.parametrize("bad", BAD_IDS)
def test_run_detail_rejects_bad_id(client, bad):
    assert client.get(f"/jobs/runs/{bad}").status_code == 422
