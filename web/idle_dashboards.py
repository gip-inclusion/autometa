"""Tableaux de bord que personne n'ouvre plus : la liste, chaque semaine, pour décider de les archiver."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import Row, func, or_, select

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
