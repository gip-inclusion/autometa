"""Consigne de sécurité (CSP) des pages de TDB : bloque les scripts hors liste et les signale."""

import json
import logging
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Request, Response

from lib import script_hosts

from . import config
from .deps import get_current_user
from .helpers import sanitize_for_log
from .routes.query import dashboard_slug

router = APIRouter()
logger = logging.getLogger(__name__)

REPORT_PATH = "/api/csp-report"

# Why: 137 TDB sur 139 ont du script en ligne ; le lot vise le code chargé d'ailleurs (sujet 09, Q3).
SCRIPT_SOURCES = ("'self'", "'unsafe-inline'", *script_hosts.ALLOWED)


def policy() -> str:
    """La CSP des pages de TDB, avec l'hôte du bucket vers lequel /interactive/ redirige leurs .js."""
    s3 = urlsplit(config.S3_ENDPOINT or "")
    bucket = f"{s3.scheme}://{config.S3_BUCKET}.{s3.netloc}"
    sources = [*SCRIPT_SOURCES, bucket] if s3.netloc and config.S3_BUCKET else SCRIPT_SOURCES
    return f"script-src {' '.join(sources)}; object-src 'none'; base-uri 'self'; report-uri {REPORT_PATH}"


async def csp_middleware(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/interactive/"):
        response.headers["Content-Security-Policy"] = policy()
    return response


def without_query(url: str) -> str:
    """Retire la chaîne de requête : elle peut porter un jeton de déclinaison."""
    return urlsplit(url)._replace(query="", fragment="").geturl()


@router.post(REPORT_PATH)
async def csp_report(request: Request, user_email: str = Depends(get_current_user)):
    try:
        report = json.loads(await request.body())["csp-report"]
    except ValueError, KeyError, TypeError:
        logger.debug("Rapport CSP illisible ignoré")
        return Response(status_code=400)
    logger.warning(
        "Violation CSP TDB=%s directive=%s bloqué=%s source=%s",
        dashboard_slug(report.get("document-uri")),
        sanitize_for_log(str(report.get("effective-directive") or report.get("violated-directive"))),
        sanitize_for_log(without_query(str(report.get("blocked-uri", "")))),
        sanitize_for_log(without_query(str(report.get("source-file", "")))),
    )
    return Response(status_code=204)
