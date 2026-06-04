"""autometa-jobs — proxy endpoints and control-panel pages."""

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse, PlainTextResponse

from lib import jobs
from web.deps import get_current_user, templates
from web.routes.html import get_sidebar_data

logger = logging.getLogger(__name__)

router = APIRouter()

# autometa-jobs ids are UUIDs — reject anything else before it reaches the orchestrator.
JobId = Annotated[
    str, PathParam(pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
]


def _unavailable(exc: httpx.HTTPError) -> JSONResponse:
    logger.warning("autometa-jobs request failed: %s", exc)
    return JSONResponse({"error": "Service de jobs indisponible"}, status_code=502)


@router.post("/api/jobs/pipelines")
async def create_pipeline(request: Request):
    body = await request.json()
    name = (body.get("name") or "").strip()
    system_prompt = (body.get("system_prompt") or "").strip()
    if not name or not system_prompt:
        return JSONResponse({"error": "name et system_prompt requis"}, status_code=400)
    try:
        return jobs.create_pipeline(name, system_prompt, body.get("config"))
    except httpx.HTTPError as exc:
        return _unavailable(exc)


@router.post("/api/jobs/pipelines/{pipeline_id}/runs")
async def trigger_run(pipeline_id: JobId, request: Request):
    raw = await request.body()
    data = (await request.json()) if raw else {}
    try:
        return jobs.trigger_run(
            pipeline_id,
            input_uri=data.get("input_uri"),
            idempotency_key=data.get("idempotency_key"),
        )
    except httpx.HTTPError as exc:
        return _unavailable(exc)


@router.get("/api/jobs/runs/{run_id}")
def run_status(run_id: JobId):
    try:
        return jobs.get_run(run_id)
    except httpx.HTTPError as exc:
        return _unavailable(exc)


@router.get("/api/jobs/runs/{run_id}/events")
def run_events(run_id: JobId):
    try:
        return jobs.get_run_events(run_id)
    except httpx.HTTPError as exc:
        return _unavailable(exc)


@router.post("/api/jobs/runs/{run_id}/cancel")
def cancel_run(run_id: JobId):
    try:
        return jobs.cancel_run(run_id)
    except httpx.HTTPError as exc:
        return _unavailable(exc)


@router.get("/api/jobs/runs/{run_id}/output")
def run_output(run_id: JobId, download: bool = False):
    """Artifact content by default; with ?download=1, a short-lived download URL."""
    try:
        if download:
            return jobs.get_run_output_url(run_id)
        return PlainTextResponse(jobs.get_run_output(run_id))
    except httpx.HTTPError as exc:
        return _unavailable(exc)


@router.get("/jobs")
def jobs_page(request: Request, user_email: str = Depends(get_current_user)):
    data = get_sidebar_data(user_email)
    pipelines: list = []
    runs: list = []
    jobs_error = None
    try:
        pipelines = jobs.list_pipelines()
        runs = jobs.list_runs(limit=50)
    except httpx.HTTPError as exc:
        logger.warning("autometa-jobs unavailable: %s", exc)
        jobs_error = "Service de jobs indisponible"
    return templates.TemplateResponse(
        request,
        "jobs.html",
        {"section": "jobs", "pipelines": pipelines, "runs": runs, "jobs_error": jobs_error, **data},
    )


@router.get("/jobs/runs/{run_id}")
def job_run_page(run_id: JobId, request: Request, user_email: str = Depends(get_current_user)):
    data = get_sidebar_data(user_email)
    return templates.TemplateResponse(
        request,
        "job_run.html",
        {"section": "jobs", "run_id": run_id, **data},
    )
