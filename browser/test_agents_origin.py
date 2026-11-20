"""La garde d'origine des décisions sur un envoi, à travers le routeur et le proxy de la cible servie."""

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.browser


@pytest.mark.parametrize(
    ("same_host", "status", "body"),
    [
        (False, 403, {"detail": "requête venue d'une autre origine"}),
        (True, 404, {"error": "envoi introuvable"}),
    ],
)
def test_an_origin_matching_the_host_passes_the_guard_without_sec_fetch_site(
    page: Page, base_url, same_host, status, body
):
    """Why: le client de requêtes de Playwright n'envoie pas Sec-Fetch-Site ; le corps distingue la garde d'un refus du proxy."""
    headers = {"Origin": base_url.rstrip("/")} if same_host else {}
    response = page.request.post("/api/agents/deliveries/999999999/approve", headers=headers)
    assert (response.status, response.json()) == (status, body)
