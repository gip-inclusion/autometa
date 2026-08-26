"""Pages « Sources de données » : registre, accès et fraîcheur."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Annotated

import markdown
from fastapi import APIRouter, Depends, Request
from fastapi import Path as PathParam
from fastapi.responses import HTMLResponse
from redis.exceptions import RedisError

from web import config
from web.deps import get_current_user, templates
from web.helpers import format_relative_date
from web.redis_conn import get_redis
from web.source_checks import redact
from web.sources_registry import GROUPS, Source, find_source, grouped_sources

from .html import get_sidebar_data

logger = logging.getLogger(__name__)

router = APIRouter()

PROBE_TTL_SEC = 60
PROBE_KEY_PREFIX = "autometa:source_probe:"
DETAIL_MAX_LEN = 200
DOC_ROOTS = ("knowledge", "skills", "docs")

Slug = Annotated[str, PathParam(pattern=r"^[a-z0-9-]+$", max_length=60)]


async def cache_get(slug: str) -> dict | None:
    """Résultat mis en cache, partagé par tous les processus web."""
    try:
        raw = await (await get_redis()).get(PROBE_KEY_PREFIX + slug)
    except RedisError as exc:
        logger.warning("Cache de sondes indisponible (%s) : la source est sondée à chaque fois", type(exc).__name__)
        return None
    return json.loads(raw) if raw else None


async def cache_set(slug: str, result: dict) -> None:
    try:
        await (await get_redis()).setex(PROBE_KEY_PREFIX + slug, PROBE_TTL_SEC, json.dumps(result))
    except RedisError as exc:
        logger.warning("Écriture du cache de sondes impossible (%s)", type(exc).__name__)


def run_check(source: Source) -> dict:
    try:
        ok, detail = source.check()
    except Exception as exc:
        # Why: chaque client tiers lève sa propre famille d'exceptions, et une sonde en échec n'emporte pas la page.
        logger.warning("Sonde %s en échec : %s", source.slug, type(exc).__name__)
        ok, detail = False, f"{type(exc).__name__} : {exc}"
    return {"state": "ok" if ok else "ko", "detail": redact(detail).strip()[:DETAIL_MAX_LEN]}


async def probe(source: Source) -> dict:
    """État d'accès d'une source, au plus une sonde par minute et par source, tous processus web confondus."""
    if not source.configured():
        return {"state": "unconfigured", "detail": "non configuré dans cet environnement"}

    cached = await cache_get(source.slug)
    if cached:
        return cached

    result = await asyncio.to_thread(run_check, source)
    await cache_set(source.slug, result)
    return result


def inventory_state(source: Source) -> dict:
    if source.inventory is None:
        return {"realtime": True}
    synced_at = source.inventory()
    if synced_at is None:
        return {"realtime": False, "label": "jamais synchronisé"}
    return {"realtime": False, "label": format_relative_date(synced_at), "title": str(synced_at)}


def doc_path(source: Source) -> Path | None:
    """La fiche d'une source est un document déjà existant : jamais une copie écrite pour la page."""
    if not source.doc:
        return None
    candidate = (config.BASE_DIR / source.doc).resolve()
    roots = [(config.BASE_DIR / name).resolve() for name in DOC_ROOTS]
    if not any(candidate.is_relative_to(root) for root in roots):
        logger.warning("Fiche hors des dossiers autorisés pour %s", source.slug)
        return None
    return candidate if candidate.is_file() else None


def strip_front_matter(text: str) -> str:
    """Les SKILL.md portent un en-tête YAML qui n'a rien à faire à l'écran."""
    if not text.startswith("---\n"):
        return text
    _, _, rest = text.partition("---\n")
    before, sep, after = rest.partition("\n---\n")
    return after if sep else text


@router.get("/sources")
def sources_page(request: Request, user_email: str = Depends(get_current_user)):
    groups = grouped_sources()
    return templates.TemplateResponse(
        request,
        "sources.html",
        {
            "section": "sources",
            "groups": groups,
            "group_order": GROUPS,
            "inventories": {s.slug: inventory_state(s) for sources in groups.values() for s in sources},
            **get_sidebar_data(user_email, request),
        },
    )


@router.get("/sources/{slug}/access", response_class=HTMLResponse)
async def source_access(slug: Slug, request: Request, user_email: str = Depends(get_current_user)):
    source = find_source(slug)
    if not source:
        return HTMLResponse("", status_code=404)
    return templates.TemplateResponse(
        request,
        "_source_access.html",
        {"source": source, "access": await probe(source)},
    )


@router.get("/sources/{slug}")
def source_detail(slug: Slug, request: Request, user_email: str = Depends(get_current_user)):
    source = find_source(slug)
    if not source:
        return templates.TemplateResponse(
            request,
            "source_detail.html",
            {"section": "sources", "error": "Source inconnue", **get_sidebar_data(user_email, request)},
            status_code=404,
        )

    path = doc_path(source)
    doc_html = None
    if path:
        doc_html = markdown.markdown(strip_front_matter(path.read_text()), extensions=["tables", "fenced_code"])

    return templates.TemplateResponse(
        request,
        "source_detail.html",
        {
            "section": "sources",
            "source": source,
            "doc_html": doc_html,
            "doc_rel": source.doc,
            "inventory": inventory_state(source),
            **get_sidebar_data(user_email, request),
        },
    )
