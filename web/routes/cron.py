"""Cron task management routes."""

import logging
from typing import Annotated

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, Query, Request
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse, PlainTextResponse

from web import scalingo
from web.cron import (
    BATCH_START,
    discover_cron_tasks,
    discover_system_tasks,
    displayed_status,
    find_task,
    get_app_runs,
    get_last_batch_runs,
    get_last_runs,
    next_cron_run,
    read_cron_script,
    set_cron_enabled,
)
from web.deps import get_current_user, templates
from web.helpers import format_future_date, format_relative_date, sanitize_for_log

from .html import get_sidebar_data

logger = logging.getLogger(__name__)

router = APIRouter()

# Why: slug feeds tempfile.mkdtemp and S3 keys downstream, and now a shell command run remotely by
# Scalingo (`python -m web.cron --app <slug>`) — reject anything that could traverse paths or break
# out of that command.
Slug = Annotated[str, PathParam(pattern=r"^[a-z0-9_-]+$", max_length=100)]


@router.get("/cron")
def cron_page(request: Request, user_email: str = Depends(get_current_user)):
    """Cron task dashboard — shows all cron-eligible tasks with status."""
    data = get_sidebar_data(user_email, request)
    try:
        tasks = discover_cron_tasks()
        s3_unavailable = False
    except ClientError, BotoCoreError:
        # Why: la page reste l'outil de diagnostic quand S3 tombe — la priver de tout serait
        # la rendre inutile au moment où on en a le plus besoin.
        logger.exception("cron : découverte S3 impossible, page limitée aux tâches système")
        tasks = discover_system_tasks()
        s3_unavailable = True
    last_runs = get_last_runs()

    for task in tasks:
        task["next_run"] = format_future_date(next_cron_run(task["schedule"], task["batch"]))
        task["last_run"] = last_runs.get(task["slug"])
        if task["last_run"] and task["last_run"]["started_at"]:
            task["last_run"]["formatted_date"] = format_relative_date(task["last_run"]["started_at"])
            task["last_run"]["status"] = displayed_status(task["last_run"], task["timeout"])

    last_batch_runs = get_last_batch_runs()
    batches = []
    for batch in BATCH_START:
        run = last_batch_runs.get(batch)
        if run:
            # Why: chaque lot repart tous les jours ; encore ouvert au bout de 24 h, il ne se fermera plus.
            run["status"] = displayed_status(run, 24 * 3600)
            run["formatted_date"] = format_relative_date(run["started_at"])
        batches.append({"batch": batch, "last_run": run})

    return templates.TemplateResponse(
        request,
        "cron.html",
        {
            "section": "cron",
            "tasks": tasks,
            "batches": batches,
            "s3_unavailable": s3_unavailable,
            **data,
        },
    )


def resolve_task(slug: str) -> tuple[dict | None, JSONResponse | None]:
    """La tâche cherchée, ou la réponse à rendre : 404 si elle est inconnue, 503 si S3 est muet."""
    try:
        task = find_task(slug)
    except ClientError, BotoCoreError:
        # Why: résoudre un slug liste S3 — une secousse rendait un 500 avec traceback là où la
        # page /cron sait déjà se replier.
        logger.exception("cron %s : découverte S3 impossible", sanitize_for_log(slug))
        return None, JSONResponse({"error": "S3 est injoignable, la tâche est introuvable"}, status_code=503)
    if not task:
        return None, JSONResponse({"error": "Task not found"}, status_code=404)
    return task, None


@router.post("/api/cron/{slug}/run", status_code=202)
def run_task(slug: Slug):
    """Déclenche un run manuel dans un conteneur dédié — jamais dans le process web."""
    _, error = resolve_task(slug)
    if error:
        return error

    if not scalingo.is_configured():
        return JSONResponse(
            {"error": "Run manuel indisponible ici : lancer `python -m web.cron --app <slug>` en ligne de commande."},
            status_code=503,
        )

    try:
        container = scalingo.start_one_off(f"python -m web.cron --app {slug}")
    except scalingo.ScalingoError as e:
        logger.warning("cron %s : conteneur refusé (%s)", sanitize_for_log(slug), e)
        return JSONResponse({"error": "Scalingo a refusé le lancement"}, status_code=502)

    return {"slug": slug, "status": "queued", "container": container}


@router.post("/api/cron/{slug}/toggle")
async def toggle_task(slug: Slug, request: Request):
    """Enable or disable a cron task; the state lives in the database, not in the image."""
    body = await request.body()
    data = (await request.json()) if body else {}
    enabled = data.get("enabled", True)

    if not set_cron_enabled(slug, enabled):
        return JSONResponse({"error": "Task not found"}, status_code=404)

    return {"slug": slug, "enabled": enabled}


@router.get("/api/cron/{slug}/script")
def view_script(slug: Slug):
    task, error = resolve_task(slug)
    if error:
        return error

    content = read_cron_script(task)
    if content is None:
        return JSONResponse({"error": "Script not found"}, status_code=404)

    return PlainTextResponse(content, media_type="text/plain; charset=utf-8")


@router.get("/api/cron/{slug}/logs")
def task_logs(slug: Slug, limit: int = Query(default=20)):
    runs = get_app_runs(slug, limit=limit)
    return runs
