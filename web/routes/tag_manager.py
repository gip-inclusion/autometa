"""Tag Manager audit dashboard — read-only views over Matomo Tag Manager."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from lib.query import CallerType, execute_matomo_query
from lib.sources import get_tag_manager_sites
from web.deps import get_current_user, templates
from web.routes.html import get_sidebar_data

logger = logging.getLogger(__name__)

router = APIRouter()


def _find_site(matomo_id: int) -> dict:
    site = next((s for s in get_tag_manager_sites() if s["matomo_id"] == matomo_id), None)
    if not site:
        raise HTTPException(status_code=404, detail="Site inconnu")
    return site


def _matomo_call(method: str, params: dict):
    return execute_matomo_query(
        instance="inclusion",
        caller=CallerType.APP,
        method=method,
        params=params,
        timeout=30,
    )


def _live_export(site: dict) -> tuple[dict | None, dict | None, str | None]:
    container_result = _matomo_call(
        "TagManager.getContainer",
        {"idSite": site["matomo_id"], "idContainer": site["container_id"]},
    )
    if not container_result.success:
        logger.warning("TagManager.getContainer failed for site %s", site["matomo_id"])
        return None, None, "matomo_error"

    container = container_result.data
    live = next((r for r in container.get("releases", []) if r["environment"] == "live"), None)
    if not live:
        return container, None, None

    export_result = _matomo_call(
        "TagManager.exportContainerVersion",
        {
            "idSite": site["matomo_id"],
            "idContainer": site["container_id"],
            "idContainerVersion": live["idcontainerversion"],
        },
    )
    if not export_result.success:
        logger.warning("TagManager.exportContainerVersion failed for site %s", site["matomo_id"])
        return container, None, "matomo_error"

    return container, export_result.data, None


def _filter_tags(export: dict | None, trigger_id: int) -> list[dict]:
    if not export:
        return []
    return [t for t in export.get("tags", []) if trigger_id in t.get("fire_trigger_ids", [])]


def _tag_types_by_trigger(export: dict | None) -> dict[int, list[str]]:
    """Map trigger id → ordered, de-duplicated list of tag types firing on it."""
    result: dict[int, list[str]] = {}
    if not export:
        return result
    for tag in export.get("tags", []):
        for tid in tag.get("fire_trigger_ids", []):
            types = result.setdefault(tid, [])
            tag_type = tag.get("type", "Unknown")
            if tag_type not in types:
                types.append(tag_type)
    return result


def _resolve(matomo_id: int | None, trigger_id: int | None) -> tuple[dict | None, dict | None, dict | None, list[dict]]:
    site = export = trigger = None
    tags: list[dict] = []
    if matomo_id is not None:
        site = _find_site(matomo_id)
        _container, export, error = _live_export(site)
        if error:
            raise HTTPException(status_code=502, detail="Erreur lors de la récupération du conteneur")
    if trigger_id is not None and export is not None:
        trigger = next((t for t in export.get("triggers", []) if t.get("idtrigger") == trigger_id), None)
        if not trigger:
            raise HTTPException(status_code=404, detail="Trigger inconnu")
        tags = _filter_tags(export, trigger_id)
    return site, export, trigger, tags


def _respond(
    request: Request,
    user_email: str,
    matomo_id: int | None = None,
    trigger_id: int | None = None,
):
    site, export, trigger, tags = _resolve(matomo_id, trigger_id)
    tag_types_by_trigger = _tag_types_by_trigger(export)
    stack = "tags" if trigger else "triggers" if site else "sites"
    sidebar = get_sidebar_data(user_email)

    return templates.TemplateResponse(
        request,
        "tag_manager.html",
        {
            "section": "tag-manager",
            "sites": get_tag_manager_sites(),
            "site": site,
            "export": export,
            "trigger": trigger,
            "tags": tags,
            "tag_types_by_trigger": tag_types_by_trigger,
            "stack": stack,
            **sidebar,
        },
    )


@router.get("/tag-manager")
def tag_manager_page(request: Request, user_email: str = Depends(get_current_user)):
    return _respond(request, user_email)


@router.get("/tag-manager/sites/{matomo_id}")
def tag_manager_site(request: Request, matomo_id: int, user_email: str = Depends(get_current_user)):
    return _respond(request, user_email, matomo_id=matomo_id)


@router.get("/tag-manager/sites/{matomo_id}/triggers/{trigger_id}")
def tag_manager_trigger(
    request: Request,
    matomo_id: int,
    trigger_id: int,
    user_email: str = Depends(get_current_user),
):
    return _respond(request, user_email, matomo_id=matomo_id, trigger_id=trigger_id)
