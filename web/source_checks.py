"""Sondes de disponibilité des sources de données, partagées par /sources et /selftest."""

import logging
import re

import httpx
from sqlalchemy import text

from lib.query import (
    CallerType,
    execute_autometa_tables_query,
    execute_dashboard_storage_query,
    execute_data_inclusion_query,
    execute_dora_staging_query,
    get_matomo,
)
from lib.rpe import doctor
from lib.sources import get_source_config, list_instances, load_config

from . import config, s3
from .db import get_db
from .helpers import list_knowledge_files

logger = logging.getLogger(__name__)

PROBE_TIMEOUT_SEC = 3

DSN_CREDENTIALS = re.compile(r"://[^/\s:@]+:[^/\s@]+@")
SENSITIVE_QUERY_PARAM = re.compile(r"([?&](?:token[_a-z]*|api[_-]?key|pass[a-z]*|secret|auth)=)[^&\s'\"]+", re.I)


def known_secrets() -> list[str]:
    """Valeurs secrètes résolues, y compris celles de config/sources.yaml (jetons Matomo, Metabase, Zendesk)."""
    values = [
        config.NOTION_TOKEN,
        config.GRIST_API_KEY,
        config.LIVESTORM_API_KEY,
        config.SLACK_BOT_TOKEN,
        config.TALLY_API_KEY,
        config.RPE_PUBLIC_PASS,
        config.AUTOMETA_TABLES_DATABASE_URL,
        config.DATA_INCLUSION_DATABASE_URL,
        config.DATABASE_URL,
        config.DASHBOARD_STORAGE_DB_URL,
    ]
    for source_type in ("matomo", "metabase", "zendesk"):
        for instance in list_instances(source_type):
            cfg = load_config().get(source_type, {}).get(instance, {})
            values += [cfg.get(key) for key in ("token", "api_key", "password")]
    return [v for v in values if v and len(v) > 6 and not v.startswith("${env.")]


def redact(detail: str) -> str:
    """Retire d'un message de sonde tout ce qui pourrait être un secret."""
    out = DSN_CREDENTIALS.sub("://***@", detail)
    # Why: httpx met l'URL complète dans ses exceptions — un jeton passé en paramètre s'y retrouve.
    out = SENSITIVE_QUERY_PARAM.sub(r"\1***", out)
    for secret in known_secrets():
        out = out.replace(secret, "***")
    return out


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


def check_data_inclusion() -> tuple[bool, str]:
    result = execute_data_inclusion_query("SELECT 1", caller=CallerType.APP)
    if result.success:
        return (True, f"connectée ({result.execution_time_ms} ms)")
    return (False, result.error or "requête en échec")


def check_metabase_instance(instance: str) -> tuple[bool, str]:
    cfg = get_source_config("metabase", instance)
    url = cfg["url"].rstrip("/") + "/api/health"
    resp = httpx.get(url, timeout=PROBE_TIMEOUT_SEC)
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


def check_rpe() -> tuple[bool, str]:
    report = doctor(timeout=PROBE_TIMEOUT_SEC)
    checks = report.get("checks", [])
    if report.get("ok"):
        return (True, " · ".join(c["check"] for c in checks) + " OK")
    failed = next((c for c in checks if not c["ok"]), None)
    return (False, f"{failed['check']} : {failed['reason']}" if failed else "échec")


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
