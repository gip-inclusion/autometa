"""Dashboard management screen routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse, RedirectResponse

from lib.dashboards import DashboardNotFound, update_dashboard
from web.config import ADMIN_USERS
from web.cron import get_last_runs
from web.database import store
from web.deps import get_current_user, templates
from web.helpers import format_relative_date

from .html import get_sidebar_data, group_items_by_date

router = APIRouter()

VIEWS = ("latest", "mine", "archived")

Slug = Annotated[str, PathParam(pattern=r"^[a-z0-9_-]+$", max_length=100)]


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

    dashboard["formatted_date"] = format_relative_date(dashboard["updated"]) if dashboard.get("updated") else ""

    last_run = None
    if dashboard["has_cron"]:
        runs = get_last_runs(limit_per_app=1).get(slug, [])
        last_run = runs[0] if runs else None
        if last_run and last_run["started_at"]:
            last_run["formatted_date"] = format_relative_date(last_run["started_at"])

    is_pinned = ("app", slug) in store.get_pinned_ids()
    data = get_sidebar_data(user_email)
    return templates.TemplateResponse(
        request,
        "dashboard_detail.html",
        {
            "section": "dashboards",
            "current_conv": None,
            "dashboard": dashboard,
            "last_run": last_run,
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
