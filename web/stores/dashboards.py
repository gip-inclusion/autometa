"""Dashboard read access."""

from sqlalchemy import select

from web.db import get_db
from web.models import Dashboard as DashboardModel
from web.models import DashboardTag as DashboardTagModel
from web.models import Tag as TagModel


def dashboard_to_dict(d, tags: list[str]) -> dict:
    return {
        "slug": d.slug,
        "title": d.title,
        "description": d.description or "",
        "website": d.website,
        "category": d.category,
        "tags": tags,
        "authors": [d.first_author_email],
        "first_author_email": d.first_author_email,
        "conversation_id": d.created_in_conversation_id,
        "created_at": d.created_at,
        "updated": d.updated_at,
        "is_archived": d.is_archived,
        "has_api_access": d.has_api_access,
        "has_cron": d.has_cron,
        "has_persistence": d.has_persistence,
        "cron_schedule": d.cron_schedule,
        "cron_timeout": d.cron_timeout,
        "cron_enabled": d.cron_enabled,
        "url": f"/interactive/{d.slug}/",
        "is_interactive": True,
    }


def serialize_dashboards(session, dashboards: list) -> list[dict]:
    if not dashboards:
        return []
    slugs = [d.slug for d in dashboards]
    tag_rows = session.execute(
        select(DashboardTagModel.dashboard_slug, TagModel.name)
        .join(TagModel, TagModel.id == DashboardTagModel.tag_id)
        .where(DashboardTagModel.dashboard_slug.in_(slugs))
    ).all()
    tags_by_slug: dict[str, list[str]] = {}
    for slug, name in tag_rows:
        tags_by_slug.setdefault(slug, []).append(name)
    return [dashboard_to_dict(d, tags_by_slug.get(d.slug, [])) for d in dashboards]


class DashboardsMixin:
    def list_dashboards(self, include_archived: bool = False) -> list[dict]:
        """Dashboards from the DB, sorted by `updated_at` desc. Active only unless include_archived."""
        with get_db() as session:
            stmt = select(DashboardModel).order_by(DashboardModel.updated_at.desc())
            if not include_archived:
                stmt = stmt.where(~DashboardModel.is_archived)
            return serialize_dashboards(session, list(session.scalars(stmt).all()))

    def list_archived_dashboards(self) -> list[dict]:
        """Archived dashboards only, sorted by `updated_at` desc."""
        with get_db() as session:
            stmt = select(DashboardModel).where(DashboardModel.is_archived).order_by(DashboardModel.updated_at.desc())
            return serialize_dashboards(session, list(session.scalars(stmt).all()))

    def get_dashboard(self, slug: str) -> dict | None:
        """Single dashboard (any archived status) as a dict, or None."""
        with get_db() as session:
            d = session.scalar(select(DashboardModel).where(DashboardModel.slug == slug))
            if d is None:
                return None
            return serialize_dashboards(session, [d])[0]
