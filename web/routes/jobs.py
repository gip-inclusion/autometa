"""pipometa jobs — proxy endpoints."""

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Request
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse

from lib import jobs

logger = logging.getLogger(__name__)

router = APIRouter()

# pipometa ids are UUIDs — reject anything else before it reaches the orchestrator.
JobId = Annotated[
    str, PathParam(pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
]


def _unavailable(exc: httpx.HTTPError) -> JSONResponse:
    logger.warning("pipometa request failed: %s", exc)
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
