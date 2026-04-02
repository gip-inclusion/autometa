"""Reports: API routes + HTML views."""

import json
import logging
import re

import httpx
import markdown as md
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from markupsafe import Markup

from .. import notion
from ..config import ADMIN_USERS
from ..database import get_db, store
from ..deps import get_current_user, templates
from ..interactive_apps import scan_interactive_apps
from ..models import Report
from .html import get_sidebar_data

logger = logging.getLogger(__name__)

# --- HTML routes ---

html_router = APIRouter()


@html_router.get("/rapports")
def rapports_list(report_id: int | None = Query(default=None, alias="id")):
    """Legacy rapports list — redirects to /rechercher."""
    if report_id is not None:
        return RedirectResponse(f"/rapports/{int(report_id)}", status_code=301)
    return RedirectResponse("/rechercher?show=reports", status_code=301)


@html_router.get("/rapports/{report_id}.txt")
def rapport_txt(report_id: int):
    report = store.get_report(report_id)
    if not report:
        return JSONResponse({"error": "Report not found"}, status_code=404)
    return PlainTextResponse(report.content, media_type="text/plain; charset=utf-8")


@html_router.get("/rapports/{report_id}")
def rapport_detail(report_id: int, request: Request, user_email: str = Depends(get_current_user)):
    data = get_sidebar_data(user_email)

    current_report = store.get_report(report_id)
    if not current_report:
        return JSONResponse({"error": "Report not found"}, status_code=404)

    current_report_tags = store.get_report_tags(report_id)
    report_front_matter, report_html = render_report_content(current_report.content)

    return templates.TemplateResponse(
        request,
        "rapports.html",
        {
            "section": "rapports",
            "current_report": current_report,
            "current_report_tags": current_report_tags,
            "report_front_matter": report_front_matter,
            "report_html": report_html,
            **data,
        },
    )


def render_report_content(raw_content: str) -> tuple[dict, Markup]:
    front_matter = {}
    content = raw_content

    fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).split("\n"):
            idx = line.find(":")
            if idx > 0:
                key = line[:idx].strip().lower()
                value = line[idx + 1 :].strip()
                front_matter[key] = value
        content = content[fm_match.end() :]

    html = md.markdown(content, extensions=["fenced_code", "tables", "toc"])
    html = html.replace("<table>", '<table class="table table-sm table-striped">')

    return front_matter, Markup(html)


# --- Apps pin/unpin ---


@html_router.post("/api/apps/{slug}/pin")
async def pin_app(slug: str, request: Request, user_email: str = Depends(get_current_user)):
    if user_email not in ADMIN_USERS:
        return JSONResponse({"error": "Permission denied"}, status_code=403)

    apps = {a["slug"]: a for a in scan_interactive_apps()}
    app = apps.get(slug)
    if not app:
        return JSONResponse({"error": "App not found"}, status_code=404)

    body = await request.body()
    data = (await request.json()) if body else {}
    label = data.get("label", "").strip() or app["title"]
    store.pin_item("app", slug, label)
    return {"ok": True, "label": label}


@html_router.delete("/api/apps/{slug}/pin")
def unpin_app(slug: str, user_email: str = Depends(get_current_user)):
    if user_email not in ADMIN_USERS:
        return JSONResponse({"error": "Permission denied"}, status_code=403)

    store.unpin_item("app", slug)
    return {"ok": True}


# --- API routes ---

api_router = APIRouter(prefix="/api/reports")


@api_router.get("/tags")
def list_tags(type: str | None = Query(default=None, alias="type")):
    if type:
        tags = store.get_all_tags(tag_type=type)
    else:
        tags = store.get_all_tags()

    return {"tags": [{"name": t.name, "type": t.type, "label": t.label} for t in tags]}


@api_router.get("")
def list_reports(
    website: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=50),
):
    reports = store.list_reports(website=website, category=category, limit=limit)
    return {
        "reports": [
            {
                "id": r.id,
                "title": r.title,
                "website": r.website,
                "category": r.category,
                "conversation_id": r.conversation_id,
                "version": r.version,
                "updated_at": r.updated_at.isoformat(),
                "links": {
                    "self": f"/api/reports/{r.id}",
                    "conversation": f"/api/conversations/{r.conversation_id}",
                },
            }
            for r in reports
        ]
    }


@api_router.get("/{report_id}")
def get_report(report_id: int):
    report = store.get_report(report_id)
    if not report:
        return JSONResponse({"error": "Report not found"}, status_code=404)

    return {
        "id": report.id,
        "title": report.title,
        "website": report.website,
        "category": report.category,
        "tags": report.tags,
        "original_query": report.original_query,
        "version": report.version,
        "content": report.content,
        "source_conversation_id": report.source_conversation_id,
        "created_at": report.created_at.isoformat(),
        "updated_at": report.updated_at.isoformat(),
        "links": {
            "self": f"/api/reports/{report.id}",
            "view": f"/rapports/{report.id}",
        },
    }


@api_router.delete("/{report_id}")
def delete_report(report_id: int):
    if store.delete_report(report_id):
        return Response(status_code=200)
    return JSONResponse({"error": "Report not found"}, status_code=404)


@api_router.post("/{report_id}/archive")
def archive_report(report_id: int):
    if store.archive_report(report_id):
        return Response(status_code=200)
    return JSONResponse({"error": "Report not found"}, status_code=404)


@api_router.post("")
async def create_report(request: Request, user_email: str = Depends(get_current_user)):
    data = await request.json()
    if not data or "title" not in data or "content" not in data:
        return JSONResponse({"error": "Missing title or content"}, status_code=400)

    report = store.create_report(
        title=data["title"],
        content=data["content"],
        website=data.get("website"),
        category=data.get("category"),
        tags=data.get("tags"),
        original_query=data.get("original_query"),
        source_conversation_id=data.get("source_conversation_id"),
        user_id=user_email,
    )

    if not report:
        return JSONResponse({"error": "Failed to create report"}, status_code=500)

    if data.get("tags"):
        store.set_report_tags(report.id, data["tags"], update_timestamp=False)

    if data.get("source_conversation_id"):
        store.add_message(
            data["source_conversation_id"], "report", json.dumps({"report_id": report.id, "title": report.title})
        )

    return JSONResponse(
        {
            "id": report.id,
            "title": report.title,
            "links": {
                "self": f"/api/reports/{report.id}",
                "view": f"/rapports/{report.id}",
            },
        },
        status_code=201,
    )


@api_router.post("/{report_id}/publish-notion")
def publish_to_notion(report_id: int):
    if not notion.is_configured():
        return JSONResponse({"error": "Notion not configured"}, status_code=503)

    report = store.get_report(report_id)
    if not report:
        return JSONResponse({"error": "Report not found"}, status_code=404)

    if report.notion_url:
        return {"url": report.notion_url}

    try:
        _page_id, url = notion.publish_report(
            title=report.title,
            content=report.content,
            website=report.website,
            original_query=report.original_query,
        )
    except httpx.HTTPStatusError as e:
        body = e.response.text[:200]
        logger.error("Notion API error %d: %s", e.response.status_code, body)
        return JSONResponse({"error": "Notion API error"}, status_code=502)
    # Why: Notion client may raise various errors (network, JSON parsing, auth);
    # this endpoint must return a clean HTTP error, not crash.
    except Exception:
        logger.exception("Notion publish failed")
        return JSONResponse({"error": "Failed to publish to Notion"}, status_code=500)

    with get_db() as session:
        report_obj = session.get(Report, report_id)
        if report_obj:
            report_obj.notion_url = url

    return {"url": url}


@api_router.post("/{report_id}/pin")
async def pin_report(report_id: int, request: Request, user_email: str = Depends(get_current_user)):
    if user_email not in ADMIN_USERS:
        return JSONResponse({"error": "Permission denied"}, status_code=403)

    report = store.get_report(report_id)
    if not report:
        return JSONResponse({"error": "Report not found"}, status_code=404)

    body = await request.body()
    data = (await request.json()) if body else {}
    label = data.get("label", "").strip() or report.title
    store.pin_item("report", str(report_id), label)
    return {"ok": True, "label": label}


@api_router.delete("/{report_id}/pin")
def unpin_report(report_id: int, user_email: str = Depends(get_current_user)):
    if user_email not in ADMIN_USERS:
        return JSONResponse({"error": "Permission denied"}, status_code=403)

    store.unpin_item("report", str(report_id))
    return {"ok": True}


@api_router.get("/{report_id}/tags")
def get_report_tags(report_id: int):
    tags = store.get_report_tags(report_id)
    return {"tags": [{"name": t.name, "type": t.type, "label": t.label} for t in tags]}


@api_router.put("/{report_id}/tags")
async def set_report_tags(report_id: int, request: Request):
    data = await request.json()
    if not data or "tags" not in data:
        return JSONResponse({"error": "Missing 'tags' field"}, status_code=400)

    tag_names = data["tags"]
    if not isinstance(tag_names, list):
        return JSONResponse({"error": "'tags' must be a list"}, status_code=400)

    store.set_report_tags(report_id, tag_names)
    tags = store.get_report_tags(report_id)
    return {"tags": [{"name": t.name, "type": t.type, "label": t.label} for t in tags]}
