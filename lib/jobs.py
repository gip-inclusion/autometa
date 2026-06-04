"""Thin HTTP client for the autometa-jobs orchestrator."""

import httpx

from web import config
from web.alerts import notify_alert_channel


def _request(method: str, path: str, *, json: dict | None = None, params: dict | None = None):
    resp = httpx.request(
        method,
        f"{config.AUTOMETA_JOBS_URL}{path}",
        headers={"Authorization": f"Bearer {config.AUTOMETA_JOBS_API_KEY}"},
        timeout=15,
        json=json,
        params=params,
    )
    resp.raise_for_status()
    return resp.json()


def list_pipelines() -> list[dict]:
    return _request("GET", "/pipelines")


def create_pipeline(name: str, system_prompt: str, config_overrides: dict | None = None) -> dict:
    payload = {
        "name": name,
        "system_prompt": system_prompt,
        "config": {
            "scaleway_job_definition_id": config.AUTOMETA_JOBS_DEFINITION_ID,
            **(config_overrides or {}),
        },
    }
    pipeline = _request("POST", "/pipelines", json=payload)
    notify_alert_channel(f"🆕 Pipeline de job créé : *{name}* (`{pipeline.get('id', '?')}`)")
    return pipeline


def trigger_run(pipeline_id: str, input_uri: str | None = None, idempotency_key: str | None = None) -> dict:
    body: dict = {}
    if input_uri:
        body["input_uri"] = input_uri
    if idempotency_key:
        body["idempotency_key"] = idempotency_key
    run = _request("POST", f"/pipelines/{pipeline_id}/runs", json=body)
    run_id = run.get("id", "?")
    notify_alert_channel(f"🚀 Job lancé : run `{run_id}` — statut {run.get('status', '?')}\n{run_url(run_id)}")
    return run


def list_runs(pipeline_id: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
    params: dict = {"limit": limit}
    if pipeline_id:
        params["pipeline_id"] = pipeline_id
    if status:
        params["status"] = status
    return _request("GET", "/runs", params=params)


def get_run(run_id: str) -> dict:
    return _request("GET", f"/runs/{run_id}")


def get_run_events(run_id: str) -> list[dict]:
    return _request("GET", f"/runs/{run_id}/events")


def cancel_run(run_id: str) -> dict:
    return _request("POST", f"/runs/{run_id}/cancel")


def get_run_output(run_id: str) -> str:
    """The run's full artifact text — what the agent reads to work with results."""
    resp = httpx.get(
        f"{config.AUTOMETA_JOBS_URL}/runs/{run_id}/output",
        headers={"Authorization": f"Bearer {config.AUTOMETA_JOBS_API_KEY}"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.text


def get_run_output_url(run_id: str, expires_in: int = 3600) -> dict:
    """A short-lived download URL for the artifact — for the UI to link."""
    return _request("GET", f"/runs/{run_id}/output", params={"presign": 1, "expires_in": expires_in})


def run_url(run_id: str) -> str:
    return f"{config.BASE_URL}/jobs/runs/{run_id}"


def create_and_run(
    name: str, system_prompt: str, config_overrides: dict | None = None, input_uri: str | None = None
) -> dict:
    """Create a one-shot pipeline and immediately trigger a run — the composer's launch primitive."""
    pipeline = create_pipeline(name, system_prompt, config_overrides)
    run = trigger_run(pipeline["id"], input_uri=input_uri)
    return {
        "pipeline_id": pipeline["id"],
        "run_id": run["id"],
        "status": run["status"],
        "run_url": run_url(run["id"]),
    }
