"""Webinaire attendance data: Grist sync into the datalake."""

import json
import logging
import re
import time
from datetime import datetime, timezone

import httpx

from lib.query import CallerType, execute_metabase_query
from web import config
from web.log import setup_logging

logger = logging.getLogger(__name__)

T_WEBINAIRES = "matometa_webinaires"
T_INSCRIPTIONS = "matometa_webinaire_inscriptions"
T_SYNC_META = "matometa_webinaire_sync_meta"

_PRODUCT_PATTERNS = [
    (r"\bdora\b", "dora"),
    (r"\bmarche\b|\bmarch[eé]\b|\bachats?\b", "marche"),
    (r"\bpilotage\b", "pilotage"),
    (r"\bimmersion\b", "immersion"),
    (r"\bcommunaut[eé]\b", "communaute"),
    (r"\brdv.?insertion\b", "rdv-insertion"),
    (r"\bemplois?\b|\bpass iae\b|\bcandidature\b|\bprescri", "emplois"),
]


def infer_product(title: str, organizer_email: str | None = None) -> str | None:
    text = (title or "").lower()
    for pattern, product in _PRODUCT_PATTERNS:
        if re.search(pattern, text):
            return product
    return None


class _ResultProxy:
    def __init__(self, data):
        self._rows = [tuple(r) for r in (data or {}).get("rows", [])]

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class DatalakeWriter:
    """Write to datalake PostgreSQL via Metabase SQL API.

    Provides a sqlite3-like ``execute(sql, params)`` interface.
    Parameterized queries use ``?`` placeholders (interpolated before sending).
    """

    def __init__(self, database_id: int = 2):
        self._database_id = database_id
        self._caller = CallerType.APP

    def execute(self, sql, params=None):
        if params:
            sql = self._interpolate(sql, params)
        result = execute_metabase_query(
            instance="datalake",
            caller=self._caller,
            sql=sql,
            database_id=self._database_id,
        )
        if not result.success:
            # INSERT/UPDATE/DDL execute but Metabase complains about no ResultSet
            if result.error and "ResultSet" in result.error:
                return _ResultProxy(None)
            raise RuntimeError(f"Datalake query failed: {result.error}")
        return _ResultProxy(result.data)

    def commit(self):
        pass  # auto-commit per query

    @staticmethod
    def _interpolate(sql, params):
        parts = sql.split("?")
        if len(parts) - 1 != len(params):
            raise ValueError(f"Expected {len(parts) - 1} placeholders, got {len(params)} params")
        out = parts[0]
        for i, val in enumerate(params):
            out += escape_val(val) + parts[i + 1]
        return out


def escape_val(val):
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val).replace("'", "''")
    return f"'{s}'"


def batch_upsert(conn, insert_prefix, conflict_suffix, rows, batch_size=100):
    if not rows:
        return
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        values_clauses = []
        for row in batch:
            escaped = ", ".join(escape_val(v) for v in row)
            values_clauses.append(f"({escaped})")
        sql = insert_prefix + ", ".join(values_clauses) + conflict_suffix
        conn.execute(sql)


class GristClient:
    """Grist REST API client."""

    BASE_URL = "https://grist.numerique.gouv.fr/api"

    def __init__(
        self,
        api_key: str | None = None,
        doc_id: str | None = None,
    ):
        self.api_key = api_key or config.GRIST_API_KEY
        self.doc_id = doc_id or config.GRIST_WEBINAIRES_DOC_ID
        if not self.api_key:
            raise ValueError("GRIST_API_KEY not set")
        if not self.doc_id:
            raise ValueError("GRIST_WEBINAIRES_DOC_ID not set")
        self._session = httpx.Client(headers={"Authorization": f"Bearer {self.api_key}"})
        self.request_count = 0

    def get_records(self, table_id: str) -> list[dict]:
        url = f"{self.BASE_URL}/docs/{self.doc_id}/tables/{table_id}/records"
        resp = self._session.get(url, timeout=30)
        self.request_count += 1
        resp.raise_for_status()
        return resp.json().get("records", [])


def ts_to_iso(ts) -> str | None:
    if ts is None or ts == 0:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OSError):
        return None


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def grist_duration_to_minutes(duree: str | None) -> int | None:
    if not duree:
        return None
    m = re.search(r"(\d+)", str(duree))
    return int(m.group(1)) if m else None


def sync_grist(conn, client: GristClient):
    """Full Grist sync (always full replace for this small dataset)."""
    now = now_iso()

    # Phase 1: Webinaires
    logger.info("Fetching Webinaires...")
    webinaires = client.get_records("Webinaires")
    logger.info("%d webinaires", len(webinaires))

    webinaire_rows = []
    for rec in webinaires:
        f = rec["fields"]
        event_id = f.get("event_id", "")
        if not event_id:
            continue
        source_id = event_id
        webinar_id = f"grist:{source_id}"
        title = f.get("titre", "")
        organizer_email = f.get("organizer_email")

        webinaire_rows.append((
            webinar_id,
            "grist",
            source_id,
            title,
            f.get("description"),
            organizer_email,
            infer_product(title, organizer_email),
            "active" if f.get("status") else "inactive",
            ts_to_iso(f.get("date_event")),
            ts_to_iso(f.get("date_fin")),
            grist_duration_to_minutes(f.get("duree")),
            f.get("capacite"),
            f.get("nb_inscrits"),
            f.get("form_inscription_url"),
            f.get("lien_webinaire"),
            json.dumps(rec, ensure_ascii=False),
            now,
        ))

    batch_upsert(
        conn,
        f"""INSERT INTO {T_WEBINAIRES}
           (id, source, source_id, title, description, organizer_email,
            product, status, started_at, ended_at, duration_minutes,
            capacity, registrants_count, registration_url, webinar_url,
            raw_json, synced_at) VALUES """,
        """ ON CONFLICT(id) DO UPDATE SET
               source=excluded.source,
               source_id=excluded.source_id,
               title=excluded.title,
               description=excluded.description,
               organizer_email=excluded.organizer_email,
               product=excluded.product,
               status=excluded.status,
               started_at=excluded.started_at,
               ended_at=excluded.ended_at,
               duration_minutes=excluded.duration_minutes,
               capacity=excluded.capacity,
               registrants_count=excluded.registrants_count,
               registration_url=excluded.registration_url,
               webinar_url=excluded.webinar_url,
               raw_json=excluded.raw_json,
               synced_at=excluded.synced_at""",
        webinaire_rows,
    )
    conn.commit()

    # Phase 2: Inscriptions
    logger.info("Fetching Inscriptions...")
    inscriptions = client.get_records("Inscriptions")
    logger.info("%d inscriptions", len(inscriptions))

    inscription_rows = []
    for rec in inscriptions:
        f = rec["fields"]
        email = f.get("email")
        if not email:
            continue
        event_id = f.get("event_id", "")
        webinar_id = f"grist:{event_id}" if event_id else None

        inscription_rows.append((
            "grist",
            webinar_id,
            "",
            email.lower().strip(),
            f.get("prenom"),
            f.get("nom"),
            f.get("entreprise"),
            1,
            1 if f.get("a_participe") else 0,
            ts_to_iso(f.get("date_inscription")),
            now,
        ))

    batch_upsert(
        conn,
        f"""INSERT INTO {T_INSCRIPTIONS}
           (source, webinar_id, session_id, email, first_name, last_name,
            organisation, registered, attended, registered_at, synced_at) VALUES """,
        """ ON CONFLICT(source, webinar_id, session_id, email)
           DO UPDATE SET
               first_name=excluded.first_name,
               last_name=excluded.last_name,
               organisation=excluded.organisation,
               attended=excluded.attended,
               registered_at=excluded.registered_at,
               synced_at=excluded.synced_at""",
        inscription_rows,
    )
    conn.commit()

    reg_count = len(inscription_rows)
    logger.info("%d registrations synced (%d API calls)", reg_count, client.request_count)
    return len(webinaires), reg_count


def main():
    """CLI entry point for cron: sync Grist webinaire data into the datalake."""
    setup_logging(level=logging.DEBUG if config.DEBUG else logging.INFO)
    conn = DatalakeWriter()
    t0 = time.time()

    logger.info("--- Grist ---")
    client = GristClient()
    webinaires, regs = sync_grist(conn, client)
    logger.info("%d webinaires, %d registrations", webinaires, regs)

    total_time = time.time() - t0
    now = datetime.now(tz=timezone.utc).isoformat()

    total_webinars = conn.execute(f"SELECT COUNT(*) FROM {T_WEBINAIRES}").fetchone()[0]
    total_regs = conn.execute(f"SELECT COUNT(*) FROM {T_INSCRIPTIONS}").fetchone()[0]

    for key, value in [
        ("last_sync", now),
        ("sync_duration_seconds", str(round(total_time, 1))),
        ("total_webinars", str(total_webinars)),
        ("total_registrations", str(total_regs)),
    ]:
        conn.execute(
            f"""INSERT INTO {T_SYNC_META} (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (key, value),
        )

    logger.info("Done in %.0fs — %d webinars, %d registrations", total_time, total_webinars, total_regs)
