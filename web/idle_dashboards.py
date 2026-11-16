"""Tableaux de bord que personne n'ouvre plus : la liste, chaque semaine, pour décider de les archiver."""

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from sqlalchemy import Row, func, or_, select

from lib.query import CallerType, execute_datadog_count, execute_matomo_query
from web import alerts, config
from web.audit import slack_escape
from web.db import get_db
from web.models import Dashboard, DashboardPublication
from web.s3_janitor import blocks

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


def run() -> None:
    """Liste dans le canal d'alertes les TDB que personne n'a ouverts depuis 45 jours, pour qu'on les archive."""
    if not config.ENV.posts_alerts:
        return
    now = datetime.now(timezone.utc)
    internal = visited("/interactive/", now)
    public = visited("/dashboards/", now, f"pageUrl=^{quote(config.PUBLIC_DASHBOARDS_PROD_URL, safe='')}")
    if internal is None or public is None:
        alerts.notify_alert_channel(
            ":warning: Tableaux de bord sans visite : Matomo n'a pas répondu, pas de liste cette semaine"
        )
        return
    seen_in_matomo = internal | public
    idle, unchecked = [], 0
    for dashboard in candidates(now):
        if dashboard.slug in seen_in_matomo:
            continue
        seen = opened(dashboard.slug)
        if seen is None:
            unchecked += 1
        elif not seen:
            idle.append(dashboard)
    report(idle, unchecked)


def report(idle: list[Row], unchecked: int) -> None:
    """Le compte dans le canal d'alertes, un TDB par ligne en fil avec le lien vers sa page."""
    count = len(idle)
    summary = f":zzz: {count} tableau{'x' if count > 1 else ''} de bord sans visite depuis 45 jours — à archiver ?"
    if unchecked:
        summary += f" ({unchecked} non vérifié{'s' if unchecked > 1 else ''} : Datadog n'a pas répondu)"
    lines = [
        f"<{config.BASE_URL}/dashboards/{d.slug}/edit|{d.slug}> — {slack_escape(d.title)} — {d.first_author_email}"
        + (" — cron" if d.has_cron else "")
        + (" — publié, à dépublier aussi" if d.published_at else "")
        for d in idle
    ]
    thread = alerts.notify_alert_channel(summary)
    if thread:
        for block in blocks(lines):
            alerts.notify_alert_channel(block, thread_ts=thread)
