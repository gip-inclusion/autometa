"""Dashboard publication — immutable snapshots pushed to public S3 buckets."""

import logging
import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import select

from web import config, s3
from web.db import get_db
from web.models import Dashboard, DashboardPublication

logger = logging.getLogger(__name__)

ENVIRONMENTS = ("staging", "production")
_ID_ALPHABET = string.ascii_lowercase + string.digits


class PublicationBlocked(Exception):
    """Raised when a dashboard cannot be published (unknown, archived, or uses the query API)."""


def _generate_publication_id() -> str:
    return "".join(secrets.choice(_ID_ALPHABET) for _ in range(6))


def _public_bucket(environment: str) -> str:
    return config.PUBLIC_S3_BUCKET_PROD if environment == "production" else config.PUBLIC_S3_BUCKET_STAGING


def _public_name(slug: str, publication_id: str, environment: str) -> str:
    return slug if environment == "production" else f"{slug}-{publication_id}"


def _public_path(slug: str, publication_id: str, environment: str) -> str:
    return f"dashboards/{_public_name(slug, publication_id, environment)}/"


def public_url(slug: str, publication_id: str, environment: str) -> str:
    base = config.PUBLIC_DASHBOARDS_PROD_URL if environment == "production" else config.PUBLIC_DASHBOARDS_STAGING_URL
    return f"{base}/dashboards/{_public_name(slug, publication_id, environment)}"


def _to_dict(pub: DashboardPublication) -> dict:
    return {
        "publication_id": pub.publication_id,
        "environment": pub.environment,
        "published_by": pub.published_by,
        "published_at": pub.published_at,
        "url": public_url(pub.dashboard_slug, pub.publication_id, pub.environment),
    }


def publish(slug: str, environment: str, publisher_email: str) -> dict:
    if environment not in ENVIRONMENTS:
        raise ValueError(f"Invalid environment: {environment}")
    with get_db() as session:
        dashboard = session.scalar(select(Dashboard).where(Dashboard.slug == slug))
        if dashboard is None:
            raise PublicationBlocked(f"unknown dashboard: {slug}")
        if dashboard.is_archived:
            raise PublicationBlocked("archived")
        if dashboard.has_api_access or dashboard.has_persistence:
            raise PublicationBlocked("uses-query-api")

        publication_id = _generate_publication_id()
        s3.copy_prefix(f"interactive/{slug}/", config.S3_BUCKET, f"publications/{slug}/{publication_id}/")

        bucket = _public_bucket(environment)
        path = _public_path(slug, publication_id, environment)
        if environment == "production":
            s3.delete_prefix(bucket, path)
            for prev in session.scalars(
                select(DashboardPublication).where(
                    DashboardPublication.dashboard_slug == slug,
                    DashboardPublication.environment == "production",
                    DashboardPublication.unpublished_at.is_(None),
                )
            ):
                prev.unpublished_at = datetime.now(timezone.utc)
        s3.copy_prefix(f"publications/{slug}/{publication_id}/", bucket, path)

        pub = DashboardPublication(
            dashboard_slug=slug,
            publication_id=publication_id,
            environment=environment,
            published_by=publisher_email,
            published_at=datetime.now(timezone.utc),
        )
        session.add(pub)
        session.flush()
        logger.info("publish slug=%s env=%s id=%s by=%s", slug, environment, publication_id, publisher_email)
        return _to_dict(pub)


def unpublish(publication_id: str) -> bool:
    with get_db() as session:
        pub = session.scalar(
            select(DashboardPublication).where(
                DashboardPublication.publication_id == publication_id,
                DashboardPublication.unpublished_at.is_(None),
            )
        )
        if pub is None:
            return False
        s3.delete_prefix(_public_bucket(pub.environment), _public_path(pub.dashboard_slug, pub.publication_id, pub.environment))
        pub.unpublished_at = datetime.now(timezone.utc)
        logger.info("unpublish slug=%s env=%s id=%s", pub.dashboard_slug, pub.environment, pub.publication_id)
        return True


def list_publications(slug: str, active_only: bool = True) -> list[dict]:
    with get_db() as session:
        stmt = select(DashboardPublication).where(DashboardPublication.dashboard_slug == slug)
        if active_only:
            stmt = stmt.where(DashboardPublication.unpublished_at.is_(None))
        stmt = stmt.order_by(DashboardPublication.published_at.desc())
        return [_to_dict(p) for p in session.scalars(stmt)]
