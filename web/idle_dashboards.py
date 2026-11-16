"""Tableaux de bord que personne n'ouvre plus : la liste, chaque semaine, pour décider de les archiver."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import Row, func, or_, select

from lib.query import CallerType, execute_datadog_count, execute_matomo_query
from web.db import get_db
from web.models import Dashboard, DashboardPublication

logger = logging.getLogger(__name__)

IDLE = timedelta(days=45)


def candidates(now: datetime) -> list[Row]:
    """TDB non archivés de plus de 45 jours, sans publication de production en ligne depuis moins de 45 jours."""
    live = (
        select(DashboardPublication.dashboard_slug, func.max(DashboardPublication.published_at).label("published_at"))
        .where(DashboardPublication.environment == "production", DashboardPublication.unpublished_at.is_(None))
        .group_by(DashboardPublication.dashboard_slug)
        .subquery()
    )
    with get_db() as session:
        return session.execute(
            select(
                Dashboard.slug, Dashboard.title, Dashboard.first_author_email, Dashboard.has_cron, live.c.published_at
            )
            .outerjoin(live, live.c.dashboard_slug == Dashboard.slug)
            .where(
                ~Dashboard.is_archived,
                Dashboard.created_at < now - IDLE,
                or_(live.c.published_at.is_(None), live.c.published_at < now - IDLE),
            )
            .order_by(Dashboard.slug)
        ).all()


def visited(prefix: str, now: datetime, segment: str = "") -> set[str] | None:
    """Slugs dont une page sous `prefix` a été vue dans Matomo depuis 45 jours ; None si Matomo n'a pas répondu."""
    result = execute_matomo_query(
        instance="inclusion",
        caller=CallerType.APP,
        method="Actions.getPageUrls",
        params={
            # Why: le site 224 suit l'app comme les domaines des publications.
            "idSite": 224,
            "period": "range",
            "date": f"{(now - IDLE).date()},{now.date()}",
            "flat": 1,
            "filter_limit": -1,
            "segment": segment,
        },
    )
    if not result.success:
        logger.warning("idle-dashboards: Matomo n'a pas répondu (%s)", result.error)
        return None
    return {
        page["label"].removeprefix(prefix).split("?")[0].split("/")[0]
        for page in result.data
        if page["label"].startswith(prefix) and page.get("nb_visits")
    }


def opened(slug: str) -> bool | None:
    """Une ligne d'accès à la page dans Datadog, sur toute sa rétention de 30 jours ; None s'il n'a pas répondu."""
    result = execute_datadog_count(search=f'service:matometa "/interactive/{slug}/"', caller=CallerType.APP, days=30)
    if not result.success:
        logger.warning("idle-dashboards: Datadog n'a pas répondu pour %s (%s)", slug, result.error)
        return None
    return result.data["count"] > 0
