"""La garde d'origine des décisions sur un envoi, à travers le routeur et le proxy de la cible servie."""

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.browser


@pytest.mark.parametrize(("same_host", "status"), [(False, 403), (True, 404)])
def test_an_origin_matching_the_host_passes_the_guard_without_sec_fetch_site(page: Page, base_url, same_host, status):
    """Why: le client de requêtes de Playwright n'envoie pas Sec-Fetch-Site, comme un navigateur ancien."""
    headers = {"Origin": base_url.rstrip("/")} if same_host else {}
    assert page.request.post("/api/agents/deliveries/999999999/approve", headers=headers).status == status
