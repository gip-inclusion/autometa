"""Parcours de navigateur — la même suite contre une URL locale ou contre une review app."""

import os
import re
from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page, expect

# La cible et les identifiants viennent de l'environnement du runner, pas de web/config.py :
# la suite s'exécute hors du processus servi, et ne connaît de l'application que son URL.
BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000")
HTTP_CREDENTIALS = os.environ.get("E2E_HTTP_CREDENTIALS", "")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Le second mode d'entrée d'oauth2-proxy sur une review app ; en local il n'y a pas de proxy."""
    if not HTTP_CREDENTIALS:
        return browser_context_args
    username, _, password = HTTP_CREDENTIALS.partition(":")
    return {**browser_context_args, "http_credentials": {"username": username, "password": password}}


@pytest.fixture
def visit(page: Page) -> Callable[[str], None]:
    """Navigue sans attendre les CDN tiers du thème : leur disponibilité n'est pas ce qu'on teste."""

    def _visit(path: str) -> None:
        page.goto(path, wait_until="domcontentloaded")

    return _visit


@pytest.fixture
def fake_agent(page: Page) -> None:
    """Les tours ne se jouent que contre le moteur factice : ailleurs ils dépenseraient un vrai modèle."""
    if page.request.get("/api/auth/status").json().get("backend") != "fake":
        pytest.skip("cible servie sans AGENT_BACKEND=fake")


@pytest.fixture
def ask(page: Page) -> Callable[[str], None]:
    """Envoie un message par la barre de saisie."""

    def _ask(text: str) -> None:
        page.locator("#chatInput").fill(text)
        page.locator("#chatSendBtn").click()

    return _ask


@pytest.fixture
def conversation(fake_agent, visit: Callable[[str], None], ask: Callable[[str], None], page: Page) -> Iterator[str]:
    """Une conversation dont le premier tour (agent factice) est terminé ; un tour laissé en cours est arrêté."""
    visit("/explorations/new")
    ask("Première question")
    expect(page.locator(".event-final-answer")).to_contain_text("Réponse factice : Première question", timeout=15000)
    conversation_id = re.search(r"/explorations/([0-9a-f-]{36})", page.url).group(1)
    yield conversation_id
    page.request.post(f"/api/conversations/{conversation_id}/cancel")
