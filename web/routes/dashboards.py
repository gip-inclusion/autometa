"""Dashboard management screen routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi import Path as PathParam
from fastapi.responses import RedirectResponse

from web.config import ADMIN_USERS
from web.cron import get_last_runs
from web.database import store
from web.deps import get_current_user, templates
from web.helpers import format_relative_date

from .html import get_sidebar_data

logger = logging.getLogger(__name__)

router = APIRouter()

VIEWS = ("featured", "mine", "latest", "search", "archived")

Slug = Annotated[str, PathParam(pattern=r"^[a-z0-9_-]+$", max_length=100)]


def _search(items: list[dict], q: str) -> list[dict]:
    ql = q.lower()
    return [
        d
        for d in items
        if ql in d["title"].lower()
        or ql in (d["description"] or "").lower()
        or ql in d["first_author_email"].lower()
        or any(ql in t.lower() for t in d["tags"])
    ]


@router.get("/dashboards")
def dashboards_page(
    request: Request,
    user_email: str = Depends(get_current_user),
    view: str = Query(default="featured"),
    q: str = Query(default=""),
):
    if view not in VIEWS:
        view = "featured"

    items: list[dict] = []
    pinned_cards: list[dict] = []

    if view == "featured":
        for p in store.list_pinned_items("app"):
            d = store.get_dashboard(p.item_id)
            if d and not d["is_archived"]:
                pinned_cards.append(d)
    elif view == "archived":
        items = store.list_archived_dashboards()
    else:
        items = store.list_dashboards()
        if view == "mine":
            items = [d for d in items if d["first_author_email"] == user_email]
        elif view == "search":
            items = _search(items, q) if q else []

    for d in items + pinned_cards:
        d["formatted_date"] = format_relative_date(d["updated"]) if d.get("updated") else ""

    data = get_sidebar_data(user_email)
    return templates.TemplateResponse(
        request,
        "dashboards.html",
        {
            "section": "dashboards",
            "current_conv": None,
            "view": view,
            "q": q,
            "items": items,
            "pinned_cards": pinned_cards,
            **data,
        },
    )


@router.get("/dashboards/{slug}")
def dashboard_redirect(slug: Slug):
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
