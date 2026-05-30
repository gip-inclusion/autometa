"""Dashboard publication — immutable snapshots pushed to public S3 buckets."""

import logging
import secrets
import string
from datetime import datetime, timezone

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import select

from web import alerts, config, s3
from web.db import get_db
from web.models import Dashboard, DashboardPublication

logger = logging.getLogger(__name__)

ENVIRONMENTS = ("staging", "production")
BLOCKED_CODES = frozenset({"archived", "uses-query-api", "empty", "public-bucket-not-configured", "unknown"})
_ID_ALPHABET = string.ascii_lowercase + string.digits
_MAX_REFRESH_ERROR_LEN = 500


class PublicationBlocked(Exception):
    """Raised when a dashboard cannot be published. `code` is a short stable string."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _log_safe(value: str) -> str:
    """Strip CR/LF from user-controlled values before logging (log-injection guard)."""
    return value.replace("\r", "").replace("\n", "")


def is_publishable(has_api_access: bool, has_persistence: bool) -> bool:
    """A dashboard using the query API can't be served statically, so it can't be published."""
    return not (has_api_access or has_persistence)


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
    if not _public_bucket(environment):
        raise PublicationBlocked("public-bucket-not-configured")
    with get_db() as session:
        dashboard = session.scalar(select(Dashboard).where(Dashboard.slug == slug))
        if dashboard is None:
            raise PublicationBlocked("unknown")
        if dashboard.is_archived:
            raise PublicationBlocked("archived")
        if not is_publishable(dashboard.has_api_access, dashboard.has_persistence):
            raise PublicationBlocked("uses-query-api")

        publication_id = _generate_publication_id()
        snapshot_has_cron = s3.interactive.exists(f"{slug}/cron.py")
        copied = s3.copy_prefix(f"interactive/{slug}/", config.S3_BUCKET, f"publications/{slug}/{publication_id}/")
        if copied == 0:
            raise PublicationBlocked("empty")

        bucket = _public_bucket(environment)
        path = _public_path(slug, publication_id, environment)
        # Copy the new snapshot in (and prune orphans) before touching the previous publication,
        # so a failure here never leaves the public path empty.
        s3.sync_prefix(f"publications/{slug}/{publication_id}/", bucket, path)

        if environment == "production":
            for prev in session.scalars(
                select(DashboardPublication).where(
                    DashboardPublication.dashboard_slug == slug,
                    DashboardPublication.environment == "production",
                    DashboardPublication.unpublished_at.is_(None),
                )
            ):
                prev.unpublished_at = datetime.now(timezone.utc)

        pub = DashboardPublication(
            dashboard_slug=slug,
            publication_id=publication_id,
            environment=environment,
            published_by=publisher_email,
            published_at=datetime.now(timezone.utc),
            snapshot_has_cron=snapshot_has_cron,
        )
        session.add(pub)
        session.flush()
        logger.info(
            "publish slug=%s env=%s id=%s by=%s",
            _log_safe(slug),
            environment,
            publication_id,
            _log_safe(publisher_email),
        )
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
        s3.delete_prefix(
            _public_bucket(pub.environment), _public_path(pub.dashboard_slug, pub.publication_id, pub.environment)
        )
        pub.unpublished_at = datetime.now(timezone.utc)
        logger.info(
            "unpublish slug=%s env=%s id=%s", _log_safe(pub.dashboard_slug), pub.environment, pub.publication_id
        )
        return True


def list_publications(slug: str, active_only: bool = True) -> list[dict]:
    with get_db() as session:
        stmt = select(DashboardPublication).where(DashboardPublication.dashboard_slug == slug)
        if active_only:
            stmt = stmt.where(DashboardPublication.unpublished_at.is_(None))
        stmt = stmt.order_by(DashboardPublication.published_at.desc())
        return [_to_dict(p) for p in session.scalars(stmt)]


def pause_refresh(publication_id: str) -> bool:
    return _set_paused(publication_id, paused=True)


def resume_refresh(publication_id: str) -> bool:
    return _set_paused(publication_id, paused=False)


def _set_paused(publication_id: str, *, paused: bool) -> bool:
    with get_db() as session:
        pub = session.scalar(
            select(DashboardPublication).where(
                DashboardPublication.publication_id == publication_id,
                DashboardPublication.unpublished_at.is_(None),
            )
        )
        if pub is None:
            return False
        currently_paused = pub.refresh_paused_at is not None
        if currently_paused == paused:
            return False
        pub.refresh_paused_at = datetime.now(timezone.utc) if paused else None
        logger.info(
            "refresh_pause slug=%s id=%s paused=%s",
            _log_safe(pub.dashboard_slug),
            pub.publication_id,
            paused,
        )
        return True


def _short_error(exc: BaseException) -> str:
    """Compact `ExcClass: message` for storage in last_refresh_error, capped at 500 chars."""
    text = f"{exc.__class__.__name__}: {exc}"
    if len(text) > _MAX_REFRESH_ERROR_LEN:
        text = text[: _MAX_REFRESH_ERROR_LEN - 1] + "…"
    return text


def _notify_refresh_status_change(pub: DashboardPublication, previous_status: str | None) -> None:
    new = pub.last_refresh_status
    broke = new == "failure" and previous_status != "failure"
    recovered = new == "success" and previous_status == "failure"
    if not (broke or recovered):
        return
    app_slug = f"{pub.dashboard_slug}-{pub.publication_id}"
    url = public_url(pub.dashboard_slug, pub.publication_id, pub.environment)
    if broke:
        snippet = (pub.last_refresh_error or "").strip().replace("```", "ʼʼʼ")
        message = f":red_circle: *Rafraîchissement échoué : {app_slug}*\n<{url}|Voir la publication>"
        if snippet:
            message += f"\n```{snippet}```"
    else:
        message = f":large_green_circle: *Rafraîchissement rétabli : {app_slug}*\n<{url}|Voir la publication>"
    alerts.notify_alert_channel(message)


def refresh(publication_id: str) -> None:
    """Re-sync a publication's snapshot to its public bucket; update refresh state; alert on transition."""
    with get_db() as session:
        # Why: SELECT filters out unpublished/paused publications, but `s3.sync_prefix` is not
        # transactional with the DB. A concurrent unpublish between this SELECT and the sync can
        # still re-populate the public bucket. Accepted for V1 — unpublish is a manual, low-frequency
        # operation and the window is bounded by snapshot size.
        pub = session.scalar(
            select(DashboardPublication).where(
                DashboardPublication.publication_id == publication_id,
                DashboardPublication.unpublished_at.is_(None),
                DashboardPublication.refresh_paused_at.is_(None),
            )
        )
        if pub is None:
            return
        previous_status = pub.last_refresh_status
        try:
            s3.sync_prefix(
                f"publications/{pub.dashboard_slug}/{pub.publication_id}/",
                _public_bucket(pub.environment),
                _public_path(pub.dashboard_slug, pub.publication_id, pub.environment),
            )
            pub.last_successful_refresh_at = datetime.now(timezone.utc)
            pub.last_refresh_status = "success"
            pub.last_refresh_error = None
        except (ClientError, BotoCoreError) as exc:
            pub.last_refresh_status = "failure"
            pub.last_refresh_error = _short_error(exc)
        logger.info(
            "refresh slug=%s id=%s status=%s",
            _log_safe(pub.dashboard_slug),
            pub.publication_id,
            pub.last_refresh_status,
        )
        _notify_refresh_status_change(pub, previous_status)
