"""Un service sortant injoignable ne doit pas pouvoir monopoliser un thread indéfiniment."""

import ast
from pathlib import Path

import httpx
import pytest

from lib.sources import get_matomo, get_metabase
from lib.tally import TallyClient
from lib.webinaires import GristClient
from web import s3

# Why: le 2026-09-07, S3 injoignable et les défauts botocore (5 tentatives × 60 s) ont bloqué le
# worker web pendant 9 min 30 — toutes les requêtes en 502, quel que soit l'endpoint appelé.
BUDGET_PIRE_CAS_S3_S = 60


def make_matomo(mocker):
    mocker.patch("lib.sources.get_source_config", return_value={"url": "http://matomo.test", "token": "t"})
    mocker.patch("lib.sources.get_default_instance", return_value="inclusion")
    return get_matomo()


def make_metabase(mocker):
    mocker.patch("lib.sources.get_source_config", return_value={"url": "http://metabase.test", "api_key": "k"})
    mocker.patch("lib.sources.get_default_instance", return_value="stats")
    return get_metabase()


CLIENTS_HTTPX = [
    ("matomo", make_matomo, httpx.Timeout(180, connect=10)),
    ("metabase", make_metabase, httpx.Timeout(60, connect=10)),
    ("tally", lambda _mocker: TallyClient(api_key="cle"), httpx.Timeout(30)),
    ("grist", lambda _mocker: GristClient(api_key="cle", doc_id="doc"), httpx.Timeout(30, connect=10)),
]


def test_le_pire_cas_d_un_appel_s3_injoignable_reste_sous_le_budget():
    config = s3.make_client().meta.config
    pire_cas = config.retries["total_max_attempts"] * (config.connect_timeout + config.read_timeout)
    assert pire_cas <= BUDGET_PIRE_CAS_S3_S


@pytest.mark.parametrize(
    "construire, timeout_attendu",
    [(construire, timeout) for _, construire, timeout in CLIENTS_HTTPX],
    ids=[nom for nom, _, _ in CLIENTS_HTTPX],
)
def test_les_clients_httpx_portent_un_timeout_au_constructeur(mocker, construire, timeout_attendu):
    client = construire(mocker)
    assert client._session.timeout == timeout_attendu


def test_le_client_httpx_du_script_review_app_porte_un_timeout():
    source = Path(__file__).parent.parent / "scripts" / "review_app.py"
    appels = [
        node
        for node in ast.walk(ast.parse(source.read_text()))
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "Client"
    ]
    assert appels
    assert all(any(kw.arg == "timeout" for kw in node.keywords) for node in appels)
