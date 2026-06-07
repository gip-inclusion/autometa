"""Dashboard management screen routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select

from lib.dashboards import DashboardNotFound, update_dashboard
from web.config import ADMIN_USERS
from web.cron import cadence, get_last_runs, get_schedule_for_app, next_cron_run
from web.database import store
from web.db import get_db
from web.deps import get_current_user, templates
from web.helpers import format_future_date, format_relative_date
from web.models import DashboardPublication
from web.publications import (
    BLOCKED_CODES,
    ENVIRONMENTS,
    PublicationBlocked,
    list_publications,
    pause_refresh,
    publish,
    resume_refresh,
    unpublish,
)

from .html import get_sidebar_data, group_items_by_date

router = APIRouter()

VIEWS = ("latest", "mine", "archived")

Slug = Annotated[str, PathParam(pattern=r"^[a-z0-9_-]+$", max_length=100)]
PublicationId = Annotated[str, PathParam(pattern=r"^[a-z0-9]{6}$")]


@router.get("/dashboards")
def dashboards_page(
    request: Request,
    user_email: str = Depends(get_current_user),
    view: str = Query(default="latest"),
    q: str = Query(default=""),
):
    if view not in VIEWS:
        view = "latest"

    active = store.list_dashboards()

    if view == "archived":
        items = store.list_archived_dashboards()
    elif view == "mine":
        items = [d for d in active if d["first_author_email"] == user_email]
    else:
        items = active

    pinned_cards = []
    if view == "latest":
        active_by_slug = {d["slug"]: d for d in active}
        pinned_cards = [
            active_by_slug[p.item_id] for p in store.list_pinned_items("app") if p.item_id in active_by_slug
        ]

    last_runs = get_last_runs(limit_per_app=1)
    for d in items:
        run = next(iter(last_runs.get(d["slug"], [])), None)
        d["cron_status"] = run["status"] if run else None
        d["cron_run_date"] = format_relative_date(run["started_at"]) if run and run.get("started_at") else None
        d["updated_date"] = format_relative_date(d["updated"]) if d.get("updated") else ""
        d["sort_date"] = d["updated"]

    grouped_items = group_items_by_date(items)

    data = get_sidebar_data(user_email)
    return templates.TemplateResponse(
        request,
        "dashboards.html",
        {
            "section": "dashboards",
            "current_conv": None,
            "view": view,
            "q": q,
            "grouped_items": grouped_items,
            "pinned_cards": pinned_cards,
            **data,
        },
    )


@router.get("/dashboards/{slug}")
def dashboard_redirect(slug: Slug, user_email: str = Depends(get_current_user)):
    return RedirectResponse(f"/dashboards/{slug}/edit", status_code=301)


@router.get("/dashboards/{slug}/edit")
def dashboard_detail(slug: Slug, request: Request, user_email: str = Depends(get_current_user)):
    dashboard = store.get_dashboard(slug)
    if dashboard is None:
        return RedirectResponse("/dashboards", status_code=302)

    cron_cadence = cadence(dashboard["cron_schedule"])
    dashboard["formatted_date"] = format_relative_date(dashboard["updated"]) if dashboard.get("updated") else ""
    dashboard_publications = list_publications(slug)
    can_publish = not (dashboard["has_api_access"] or dashboard["has_persistence"])

    last_published_at = max(
        (p["published_at"] for p in dashboard_publications if p.get("published_at")),
        default=None,
    )
    dashboard_drifted = (
        last_published_at is not None
        and dashboard.get("updated") is not None
        and dashboard["updated"] > last_published_at
    )
    has_active_production = any(p["environment"] == "production" for p in dashboard_publications)
    relative_updated = dashboard["formatted_date"]

    for p in dashboard_publications:
        p["last_refresh_relative"] = (
            format_relative_date(p["last_successful_refresh_at"]) if p.get("last_successful_refresh_at") else ""
        )
        p["paused_relative"] = format_relative_date(p["refresh_paused_at"]) if p.get("refresh_paused_at") else ""

    last_run = None
    next_run_label = ""
    if dashboard["has_cron"]:
        runs = get_last_runs(limit_per_app=1).get(slug, [])
        last_run = runs[0] if runs else None
        if last_run and last_run["started_at"]:
            last_run["formatted_date"] = format_relative_date(last_run["started_at"])
        next_run_label = format_future_date(next_cron_run(get_schedule_for_app(slug)))

    is_pinned = ("app", slug) in store.get_pinned_ids()
    data = get_sidebar_data(user_email)
    return templates.TemplateResponse(
        request,
        "dashboard_detail.html",
        {
            "section": "dashboards",
            "current_conv": None,
            "dashboard": dashboard,
            "publications": dashboard_publications,
            "can_publish": can_publish,
            "dashboard_drifted": dashboard_drifted,
            "has_active_production": has_active_production,
            "relative_updated": relative_updated,
            "cron_cadence": cron_cadence,
            "last_run": last_run,
            "next_run_label": next_run_label,
            "is_pinned": is_pinned,
            "is_admin": user_email in ADMIN_USERS,
            **data,
        },
    )


@router.post("/api/dashboards/{slug}/archive")
async def toggle_archive(slug: Slug, request: Request, user_email: str = Depends(get_current_user)):
    body = await request.body()
    payload = (await request.json()) if body else {}
    archived = bool(payload.get("archived", True))
    if archived:
        for pub in list_publications(slug, active_only=True):
            unpublish(pub["publication_id"])
    try:
        update_dashboard(slug=slug, updater_email=user_email, is_archived=archived)
    except DashboardNotFound:
        return JSONResponse({"error": "Dashboard not found"}, status_code=404)
    return {"slug": slug, "is_archived": archived}


@router.post("/api/dashboards/{slug}/api-access")
async def toggle_api_access(slug: Slug, request: Request, user_email: str = Depends(get_current_user)):
    body = await request.body()
    payload = (await request.json()) if body else {}
    enabled = bool(payload.get("enabled", True))
    try:
        update_dashboard(slug=slug, updater_email=user_email, has_api_access=enabled)
    except DashboardNotFound:
        return JSONResponse({"error": "Dashboard not found"}, status_code=404)
    return {"slug": slug, "has_api_access": enabled}


@router.post("/api/dashboards/{slug}/rename")
async def rename_dashboard(slug: Slug, request: Request, user_email: str = Depends(get_current_user)):
    body = await request.body()
    payload = (await request.json()) if body else {}
    title = (payload.get("title") or "").strip()
    if not title:
        return JSONResponse({"error": "Title required"}, status_code=400)
    try:
        update_dashboard(slug=slug, updater_email=user_email, title=title)
    except DashboardNotFound:
        return JSONResponse({"error": "Dashboard not found"}, status_code=404)
    return {"slug": slug, "title": title}


@router.post("/api/dashboards/{slug}/schedule")
async def update_dashboard_schedule(slug: Slug, request: Request, user_email: str = Depends(get_current_user)):
    body = await request.body()
    payload = (await request.json()) if body else {}
    cron_schedule = payload.get("cron_schedule")
    cron_timeout = payload.get("cron_timeout")
    if cron_timeout is not None:
        try:
            cron_timeout = int(cron_timeout)
        except TypeError, ValueError:
            return JSONResponse({"error": "Invalid timeout"}, status_code=400)
    try:
        update_dashboard(
            slug=slug,
            updater_email=user_email,
            cron_schedule=cron_schedule,
            cron_timeout=cron_timeout,
        )
    except DashboardNotFound:
        return JSONResponse({"error": "Dashboard not found"}, status_code=404)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return {"ok": True, "slug": slug}


@router.post("/api/dashboards/{slug}/publish")
async def publish_dashboard(slug: Slug, request: Request, user_email: str = Depends(get_current_user)):
    body = await request.body()
    payload = (await request.json()) if body else {}
    environment = payload.get("environment", "staging")
    if environment not in ENVIRONMENTS:
        return JSONResponse({"error": "Invalid environment"}, status_code=400)
    try:
        return publish(slug, environment, user_email)
    except PublicationBlocked as exc:
        reason = exc.code if exc.code in BLOCKED_CODES else "blocked"
        return JSONResponse({"error": "publication_blocked", "reason": reason}, status_code=409)


@router.post("/api/publications/{publication_id}/unpublish")
async def unpublish_publication(publication_id: PublicationId, user_email: str = Depends(get_current_user)):
    if not unpublish(publication_id):
        return JSONResponse({"error": "Not found"}, status_code=404)
    return {"ok": True}


@router.post("/api/publications/{publication_id}/refresh-pause")
async def pause_publication_refresh(publication_id: PublicationId, user_email: str = Depends(get_current_user)):
    if pause_refresh(publication_id) or _publication_exists(publication_id):
        return {"ok": True, "paused": True}
    return JSONResponse({"error": "Not found"}, status_code=404)


@router.post("/api/publications/{publication_id}/refresh-resume")
async def resume_publication_refresh(publication_id: PublicationId, user_email: str = Depends(get_current_user)):
    if resume_refresh(publication_id) or _publication_exists(publication_id):
        return {"ok": True, "paused": False}
    return JSONResponse({"error": "Not found"}, status_code=404)


def _publication_exists(publication_id: str) -> bool:
    with get_db() as session:
        return (
            session.scalar(
                select(DashboardPublication).where(
                    DashboardPublication.publication_id == publication_id,
                    DashboardPublication.unpublished_at.is_(None),
                )
            )
            is not None
        )
