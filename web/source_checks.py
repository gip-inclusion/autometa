"""Sondes de disponibilité des sources de données, partagées par /sources et /selftest."""

import logging

import httpx
from sqlalchemy import text

from lib.query import (
    CallerType,
    execute_appli_monrecap_query,
    execute_autometa_tables_query,
    execute_dashboard_storage_query,
    execute_data_inclusion_query,
    execute_dora_staging_query,
    get_matomo,
)
from lib.sources import get_source_config

from . import config, s3
from .db import get_db
from .helpers import list_knowledge_files

logger = logging.getLogger(__name__)

PROBE_TIMEOUT_SEC = 3


def check_knowledge_base() -> tuple[bool, str]:
    sections = list_knowledge_files()
    count = sum(len(files) for files in sections.values())
    if not count:
        return (False, "aucune fiche lisible")
    return (True, f"{count} fiches dans {len(sections)} sections")


def check_app_db() -> tuple[bool, str]:
    with get_db() as session:
        session.execute(text("SELECT 1"))
    return (True, "connectée")


def check_dashboard_storage() -> tuple[bool, str]:
    result = execute_dashboard_storage_query(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'dashboard_storage'",
        caller=CallerType.APP,
    )
    if result.success:
        return (True, f"{result.data['rows'][0][0]} tables")
    return (False, result.error or "requête en échec")


def check_autometa_tables() -> tuple[bool, str]:
    result = execute_autometa_tables_query("SELECT 1", caller=CallerType.APP)
    if result.success:
        return (True, f"connectée ({result.execution_time_ms} ms)")
    return (False, result.error or "requête en échec")


def check_dora_staging() -> tuple[bool, str]:
    result = execute_dora_staging_query("SELECT 1", caller=CallerType.APP)
    if result.success:
        return (True, f"connectée en lecture seule ({result.execution_time_ms} ms)")
    return (False, result.error or "requête en échec")


def check_appli_monrecap() -> tuple[bool, str]:
    result = execute_appli_monrecap_query("SELECT 1", caller=CallerType.APP)
    if result.success:
        return (True, f"connectée ({result.execution_time_ms} ms)")
    return (False, result.error or "requête en échec")


def check_data_inclusion() -> tuple[bool, str]:
    result = execute_data_inclusion_query("SELECT 1", caller=CallerType.APP)
    if result.success:
        return (True, f"connectée ({result.execution_time_ms} ms)")
    return (False, result.error or "requête en échec")


def check_metabase_instance(instance: str) -> tuple[bool, str]:
    cfg = get_source_config("metabase", instance)
    url = cfg["url"].rstrip("/") + "/api/health"
    basic_auth = cfg.get("basic_auth")
    resp = httpx.get(url, auth=tuple(basic_auth.split(":", 1)) if basic_auth else None, timeout=PROBE_TIMEOUT_SEC)
    if resp.status_code == 200:
        return (True, "en bonne santé")
    return (False, f"HTTP {resp.status_code}")


def check_matomo() -> tuple[bool, str]:
    api = get_matomo("inclusion")
    resp = httpx.get(
        f"https://{api.url}/index.php",
        params={"module": "API", "method": "API.getMatomoVersion", "format": "json", "token_auth": api.token},
        timeout=PROBE_TIMEOUT_SEC,
    )
    resp.raise_for_status()
    return (True, "v" + resp.json().get("value", "?")[:40])


def check_notion() -> tuple[bool, str]:
    resp = httpx.get(
        "https://api.notion.com/v1/users/me",
        headers={"Authorization": f"Bearer {config.NOTION_TOKEN}", "Notion-Version": "2022-06-28"},
        timeout=PROBE_TIMEOUT_SEC,
    )
    if resp.status_code == 200:
        return (True, "intégration : " + resp.json().get("name", "ok"))
    return (False, f"HTTP {resp.status_code}")


def check_tally() -> tuple[bool, str]:
    resp = httpx.get(
        "https://api.tally.so/forms",
        headers={"Authorization": f"Bearer {config.TALLY_API_KEY}"},
        params={"limit": 1},
        timeout=PROBE_TIMEOUT_SEC,
    )
    if resp.status_code == 200:
        total = resp.json().get("total")
        return (True, f"{total} formulaires" if total is not None else "joignable")
    return (False, f"HTTP {resp.status_code}")


def check_grist() -> tuple[bool, str]:
    resp = httpx.get(
        f"https://grist.numerique.gouv.fr/api/docs/{config.GRIST_WEBINAIRES_DOC_ID}/tables",
        headers={"Authorization": f"Bearer {config.GRIST_API_KEY}"},
        timeout=PROBE_TIMEOUT_SEC,
    )
    if resp.status_code == 200:
        return (True, f"{len(resp.json().get('tables', []))} tables")
    return (False, f"HTTP {resp.status_code}")


def check_livestorm() -> tuple[bool, str]:
    resp = httpx.get(
        "https://api.livestorm.co/v1/ping",
        headers={"Authorization": config.LIVESTORM_API_KEY},
        timeout=PROBE_TIMEOUT_SEC,
    )
    if resp.status_code == 200:
        return (True, "joignable")
    return (False, f"HTTP {resp.status_code}")


def check_datadog() -> tuple[bool, str]:
    """Compte les événements de la dernière minute : valide la clé et la permission de lecture."""
    resp = httpx.post(
        f"https://api.{config.DATADOG_SITE}/api/v2/logs/analytics/aggregate",
        headers={"DD-API-KEY": config.DATADOG_API_KEY, "DD-APPLICATION-KEY": config.DATADOG_APP_KEY},
        json={"filter": {"query": "", "from": "now-1m", "to": "now"}, "compute": [{"aggregation": "count"}]},
        timeout=PROBE_TIMEOUT_SEC,
    )
    if resp.status_code == 200:
        buckets = resp.json().get("data", {}).get("buckets", [])
        events = buckets[0]["computes"]["c0"] if buckets else 0
        return (True, f"{events} événements sur la dernière minute")
    return (False, f"HTTP {resp.status_code}")


def check_zendesk() -> tuple[bool, str]:
    cfg = get_source_config("zendesk")
    resp = httpx.get(
        f"https://{cfg['subdomain']}.zendesk.com/api/v2/views/count.json",
        auth=(f"{cfg['email']}/token", cfg["token"]),
        timeout=PROBE_TIMEOUT_SEC,
    )
    if resp.status_code == 200:
        count = resp.json().get("view_count", {}).get("value")
        return (True, f"{count} vues" if count is not None else "joignable")
    return (False, f"HTTP {resp.status_code}")


def check_slack() -> tuple[bool, str]:
    resp = httpx.head(
        "https://slack.com/api/auth.test",
        headers={"Authorization": f"Bearer {config.SLACK_BOT_TOKEN}"},
        timeout=PROBE_TIMEOUT_SEC,
    )
    if resp.status_code == 200:
        return (True, "API joignable")
    return (False, f"HTTP {resp.status_code}")


def check_s3() -> tuple[bool, str]:
    key = "selftest/ping.txt"
    payload = b"ping"
    if not s3.interactive.upload(key, payload, "text/plain"):
        return (False, "écriture refusée")
    got = s3.interactive.download(key)
    s3.interactive.delete(key)
    if got != payload:
        return (False, "relecture incohérente")
    return (True, "écriture/lecture/suppression OK")
