"""autometa-jobs — proxy endpoints and control-panel pages."""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse, PlainTextResponse

from lib import jobs
from web.deps import get_current_user, templates
from web.helpers import format_relative_date
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


def _run_date(iso: str | None) -> str:
    """ISO timestamp → friendly local string, tolerant of nulls and odd formats."""
    if not iso:
        return ""
    try:
        return format_relative_date(datetime.fromisoformat(iso))
    except ValueError:
        return iso


def _load_pipelines() -> tuple[list, str | None]:
    """Pipelines enriched with their runs, run count, and friendly dates, newest-active first."""
    try:
        pipelines = jobs.list_pipelines()
        runs = jobs.list_runs(limit=200)
    except httpx.HTTPError as exc:
        logger.warning("autometa-jobs unavailable: %s", exc)
        return [], "Service de jobs indisponible"
    by_pipeline: dict[str, list] = defaultdict(list)
    for r in runs:
        by_pipeline[r["pipeline_id"]].append(r)
    for p in pipelines:
        p_runs = sorted(by_pipeline.get(p["id"], []), key=lambda r: r.get("created_at") or "", reverse=True)
        for r in p_runs:
            r["created_at_display"] = _run_date(r.get("created_at"))
        p["runs"] = p_runs
        p["run_count"] = len(p_runs)
        # Order pipelines by latest activity (most recent run, else creation).
        p["last_activity"] = (p_runs[0].get("created_at") if p_runs else p.get("created_at")) or ""
        p["last_activity_display"] = _run_date(p["last_activity"])
    pipelines.sort(key=lambda p: p["last_activity"], reverse=True)
    return pipelines, None


def _render_jobs(request: Request, user_email: str, selected_id: str | None):
    data = get_sidebar_data(user_email)
    pipelines, jobs_error = _load_pipelines()
    selected = None
    if pipelines:
        if selected_id:
            selected = next((p for p in pipelines if p["id"] == selected_id), None)
        else:
            selected = pipelines[0]  # most recently active
    return templates.TemplateResponse(
        request,
        "jobs.html",
        {"section": "jobs", "pipelines": pipelines, "selected": selected, "jobs_error": jobs_error, **data},
    )


@router.get("/jobs")
def jobs_page(request: Request, user_email: str = Depends(get_current_user)):
    return _render_jobs(request, user_email, selected_id=None)


@router.get("/jobs/pipelines/{pipeline_id}")
def jobs_pipeline_page(pipeline_id: JobId, request: Request, user_email: str = Depends(get_current_user)):
    return _render_jobs(request, user_email, selected_id=pipeline_id)


@router.get("/jobs/runs/{run_id}")
def job_run_page(run_id: JobId, request: Request, user_email: str = Depends(get_current_user)):
    data = get_sidebar_data(user_email)
    return templates.TemplateResponse(
        request,
        "job_run.html",
        {"section": "jobs", "run_id": run_id, **data},
    )
