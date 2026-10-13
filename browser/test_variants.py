"""Déclinaisons dans l'application servie : l'index interne et la page d'édition."""

import shutil
import uuid
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect
from sqlalchemy import delete

from lib.dashboards import create_dashboard
from lib.variants import add_variant
from web import config, s3
from web.db import get_db
from web.models import Dashboard

pytestmark = pytest.mark.browser


@pytest.fixture
def multi_source_dashboard():
    """Un TDB multi-sources avec une déclinaison, créé par la bibliothèque de l'application."""
    slug = f"e2e-variants-{uuid.uuid4().hex[:8]}"
    create_dashboard(
        slug=slug,
        title="Parcours déclinaisons",
        description="e2e",
        website=None,
        category=None,
        tags=[],
        has_cron=True,
        multi_source=True,
        first_author_email="e2e@inclusion.gouv.fr",
        created_in_conversation_id=None,
    )
    variant = add_variant(slug, "117", "Emplois")
    yield slug, variant
    with get_db() as session:
        session.execute(delete(Dashboard).where(Dashboard.slug == slug))
    shutil.rmtree(config.INTERACTIVE_DIR / slug, ignore_errors=True)
    # Why: le watcher a déjà poussé le dossier sur S3, d'où l'application le restaurerait au boot.
    for entry in s3.interactive.list_files(f"{slug}/"):
        s3.interactive.delete(entry["path"])


def test_dod_3_the_internal_index_lists_variants_and_links_to_the_edit_page(
    visit: Callable[[str], None], page: Page, multi_source_dashboard
):
    slug, variant = multi_source_dashboard

    visit(f"/interactive/{slug}/")

    expect(page.get_by_role("link", name="Emplois")).to_have_attribute("href", variant["url"])
    expect(page.get_by_role("link", name="Gérer ce tableau de bord")).to_have_attribute(
        "href", f"/dashboards/{slug}/edit"
    )


def test_dod_5_the_edit_page_lists_each_variant_with_its_links(
    visit: Callable[[str], None], page: Page, multi_source_dashboard
):
    slug, variant = multi_source_dashboard

    visit(f"/dashboards/{slug}/edit")

    row = page.locator("#variants-table tbody tr").first
    expect(row).to_contain_text("117")
    expect(row).to_contain_text("Emplois")
    expect(row.get_by_role("link", name="Ouvrir")).to_have_attribute("href", variant["url"])
    expect(page.get_by_role("link", name="Mapping JSON")).to_have_attribute("href", f"/api/dashboards/{slug}/variants")
