"""Thin HTTP client for the autometa-jobs orchestrator."""

import httpx

from web import config


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
    return _request("POST", "/pipelines", json=payload)


def trigger_run(pipeline_id: str, input_uri: str | None = None, idempotency_key: str | None = None) -> dict:
    body: dict = {}
    if input_uri:
        body["input_uri"] = input_uri
    if idempotency_key:
        body["idempotency_key"] = idempotency_key
    return _request("POST", f"/pipelines/{pipeline_id}/runs", json=body)


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
