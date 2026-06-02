"""Tests for the pipometa jobs proxy + page routes."""

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


@pytest.mark.parametrize("bad", BAD_IDS)
def test_trigger_run_rejects_bad_pipeline_id(client, bad):
    r = client.post(f"/api/jobs/pipelines/{bad}/runs", json={})
    assert r.status_code == 422


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


@pytest.mark.parametrize("bad", BAD_IDS)
def test_run_status_rejects_bad_id(client, bad):
    assert client.get(f"/api/jobs/runs/{bad}").status_code == 422


def test_orchestrator_unreachable_returns_502(client, mocker):
    mocker.patch(
        "web.routes.jobs.jobs.get_run",
        side_effect=httpx.ConnectError("down", request=httpx.Request("GET", "http://x")),
    )
    r = client.get(f"/api/jobs/runs/{GOOD_ID}")
    assert r.status_code == 502
