"""Parcours de navigateur — la même suite contre une URL locale ou contre une review app."""

import os
from collections.abc import Callable

import pytest
from playwright.sync_api import Page

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
