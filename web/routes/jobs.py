"""autometa-jobs — proxy endpoints and control-panel pages."""

import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Query, Request
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse, PlainTextResponse

from lib import job_tags, jobs
from web.deps import get_current_user, templates
from web.helpers import format_relative_date, sanitize_for_log
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


def unknown_pipeline(pipeline_id: str) -> JSONResponse | None:
    """Réponse d'erreur si le service de jobs ne connaît pas le pipeline ou ne répond pas."""
    try:
        known = {p["id"] for p in jobs.list_pipelines()}
    except httpx.HTTPError as exc:
        return _unavailable(exc)
    if pipeline_id not in known:
        return JSONResponse({"error": "Pipeline inconnu"}, status_code=404)
    return None


def render_job_tags(request: Request, pipeline_id: str):
    return templates.TemplateResponse(request, "_job_tags.html", {**job_tags.editor_context(pipeline_id), "oob": True})


@router.post("/api/jobs/pipelines/{pipeline_id}/tags")
async def toggle_pipeline_tag(pipeline_id: JobId, request: Request, user_email: str = Depends(get_current_user)):
    form = await request.form()
    name = (form.get("tag") or "").strip()
    if error := unknown_pipeline(pipeline_id):
        return error
    if not job_tags.toggle_tag(pipeline_id, name):
        return JSONResponse({"error": f"Terme inconnu ou désactivé : {name}"}, status_code=400)
    logger.info(
        "job %s : tag %s basculé par %s",
        sanitize_for_log(pipeline_id),
        sanitize_for_log(name),
        sanitize_for_log(user_email),
    )
    return render_job_tags(request, pipeline_id)


@router.post("/api/jobs/pipelines/{pipeline_id}/tags/new")
async def create_pipeline_tag(pipeline_id: JobId, request: Request, user_email: str = Depends(get_current_user)):
    form = await request.form()
    label = (form.get("label") or "").strip()[:80]
    if error := unknown_pipeline(pipeline_id):
        return error
    if refusal := job_tags.propose_term(pipeline_id, label):
        return JSONResponse({"error": refusal}, status_code=400)
    logger.info(
        "job %s : terme proposé %s par %s",
        sanitize_for_log(pipeline_id),
        sanitize_for_log(label),
        sanitize_for_log(user_email),
    )
    return render_job_tags(request, pipeline_id)


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


SORTS = {
    "activite": "Activité récente",
    "nom": "Nom",
    "tag": "Tag",
}


def query_string(tags: list[str], sort: str) -> str:
    """Filtre et tri courants, à reporter sur chaque lien de la page."""
    params = [("tag", t) for t in tags] + ([("tri", sort)] if sort != "activite" else [])
    return f"?{urlencode(params)}" if params else ""


def sort_pipelines(pipelines: list[dict], sort: str) -> list[dict]:
    """Tri stable : à clé égale, l'activité récente départage."""
    if sort == "nom":
        return sorted(pipelines, key=lambda p: (p.get("name") or "").casefold())
    if sort == "tag":
        return sorted(pipelines, key=lambda p: (not p["tags"], p["tags"][0].label.casefold() if p["tags"] else ""))
    return pipelines


def tag_filters(pipelines: list[dict], active: list[str], sort: str) -> list[dict]:
    """Tags portés, avec le nombre de pipelines et le lien qui bascule le filtre."""
    counts = Counter(t.name for p in pipelines for t in p["tags"])
    labels = {t.name: t.label for p in pipelines for t in p["tags"]}
    return [
        {
            "name": name,
            "label": labels[name],
            "count": counts[name],
            "active": name in active,
            "href": "/jobs"
            + query_string([t for t in active if t != name] if name in active else [*active, name], sort),
        }
        for name in sorted(counts, key=lambda n: (-counts[n], labels[n].casefold()))
    ]


def _render_jobs(request: Request, user_email: str, selected_id: str | None, tags: list[str], sort: str):
    data = get_sidebar_data(user_email, request)
    pipelines, jobs_error = _load_pipelines()
    by_pipeline = job_tags.tags_by_pipeline([p["id"] for p in pipelines])
    for p in pipelines:
        p["tags"] = by_pipeline[p["id"]]
    sort = sort if sort in SORTS else "activite"
    active = [t for t in tags if t]
    filters = tag_filters(pipelines, active, sort)
    listed = pipelines
    if active:
        matching = job_tags.pipelines_with_tags(active)
        listed = [p for p in pipelines if p["id"] in matching]
    listed = sort_pipelines(listed, sort)
    if selected_id:
        selected = next((p for p in pipelines if p["id"] == selected_id), None)
    else:
        selected = listed[0] if listed else None
    return templates.TemplateResponse(
        request,
        "jobs.html",
        {
            "section": "jobs",
            "pipelines": listed,
            "selected": selected,
            "jobs_error": jobs_error,
            "tag_filters": filters,
            "active_tags": active,
            "sort": sort,
            "sorts": {key: ("/jobs" + query_string(active, key), label) for key, label in SORTS.items()},
            "qs": query_string(active, sort),
            **(job_tags.editor_context(selected["id"]) if selected else {}),
            **data,
        },
    )


@router.get("/jobs")
def jobs_page(
    request: Request,
    user_email: str = Depends(get_current_user),
    tag: list[str] = Query(default=[]),
    tri: str = Query(default="activite"),
):
    return _render_jobs(request, user_email, selected_id=None, tags=tag, sort=tri)


@router.get("/jobs/pipelines/{pipeline_id}")
def jobs_pipeline_page(
    pipeline_id: JobId,
    request: Request,
    user_email: str = Depends(get_current_user),
    tag: list[str] = Query(default=[]),
    tri: str = Query(default="activite"),
):
    return _render_jobs(request, user_email, selected_id=pipeline_id, tags=tag, sort=tri)


@router.get("/jobs/runs/{run_id}")
def job_run_page(run_id: JobId, request: Request, user_email: str = Depends(get_current_user)):
    data = get_sidebar_data(user_email, request)
    # Resolve the parent pipeline so "← Jobs" returns to it with that row selected.
    pipeline_id = None
    try:
        pipeline_id = jobs.get_run(run_id).get("pipeline_id")
    except httpx.HTTPError as exc:
        # Non-fatal: the page still renders; the back link just falls back to /jobs.
        logger.warning("could not resolve parent pipeline for run %s: %s", sanitize_for_log(run_id), exc)
    back_url = f"/jobs/pipelines/{pipeline_id}" if pipeline_id else "/jobs"
    return templates.TemplateResponse(
        request,
        "job_run.html",
        {"section": "jobs", "run_id": run_id, "back_url": back_url, **data},
    )
