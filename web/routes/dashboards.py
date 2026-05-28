"""Dashboard management screen routes."""

import logging

from fastapi import APIRouter, Depends, Query, Request

from web.database import store
from web.deps import get_current_user, templates
from web.helpers import format_relative_date

from .html import get_sidebar_data

logger = logging.getLogger(__name__)

router = APIRouter()

VIEWS = ("featured", "mine", "latest", "search", "archived")


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
