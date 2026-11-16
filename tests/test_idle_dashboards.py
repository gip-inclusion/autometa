"""Les tableaux de bord que personne n'ouvre plus : qui est listé, sur quelles preuves, et ce qu'en dit Slack."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from web import idle_dashboards
from web.db import get_db
from web.models import Dashboard, DashboardPublication

NOW = datetime(2026, 11, 16, tzinfo=timezone.utc)


def make_dashboard(session, slug, days_old, archived=False):
    session.add(
        Dashboard(
            slug=slug,
            title="t",
            description="d",
            website="emplois",
            category="c",
            first_author_email="alice@x",
            is_archived=archived,
            has_api_access=False,
            has_cron=False,
            has_persistence=False,
            created_at=NOW - timedelta(days=days_old),
            updated_at=NOW,
        )
    )
    session.flush()


def make_publication(session, slug, environment, days_old, unpublished=False):
    session.add(
        DashboardPublication(
            dashboard_slug=slug,
            publication_id=uuid.uuid4().hex[:6],
            environment=environment,
            published_by="bob@x",
            published_at=NOW - timedelta(days=days_old),
            unpublished_at=NOW - timedelta(days=1) if unpublished else None,
        )
    )


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_candidates_are_old_dashboards_without_a_recent_live_production_publication():
    run_id = uuid.uuid4().hex[:8]
    with get_db() as session:
        make_dashboard(session, f"old-{run_id}", 60)
        make_dashboard(session, f"recent-{run_id}", 30)
        make_dashboard(session, f"archived-{run_id}", 60, archived=True)
        for name, environment, days_old, unpublished in (
            ("published-long-ago", "production", 50, False),
            ("published-lately", "production", 10, False),
            ("staging-only", "staging", 10, False),
            ("unpublished", "production", 10, True),
        ):
            make_dashboard(session, f"{name}-{run_id}", 60)
            make_publication(session, f"{name}-{run_id}", environment, days_old, unpublished)

    found = {row.slug: row.published_at for row in idle_dashboards.candidates(NOW) if row.slug.endswith(run_id)}

    assert found == {
        f"old-{run_id}": None,
        f"published-long-ago-{run_id}": NOW - timedelta(days=50),
        f"staging-only-{run_id}": None,
        f"unpublished-{run_id}": None,
    }
