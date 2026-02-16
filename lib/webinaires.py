"""Webinaire attendance data: Livestorm + Grist sync into SQLite.

Provides API clients for both platforms and sync logic to maintain
a unified webinaires.db database.

Usage:
    from lib.webinaires import (
        LivestormClient, GristClient,
        ensure_schema, sync_livestorm, sync_grist,
    )
"""

import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

log = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "webinaires.db"

# ---------------------------------------------------------------------------
# Product inference
# ---------------------------------------------------------------------------

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
    """Best-effort product tagging from title and organizer email."""
    text = (title or "").lower()
    for pattern, product in _PRODUCT_PATTERNS:
        if re.search(pattern, text):
            return product
    return None


# ---------------------------------------------------------------------------
# Livestorm API client
# ---------------------------------------------------------------------------

class LivestormClient:
    """Livestorm REST API client (JSON:API format)."""

    BASE_URL = "https://api.livestorm.co/v1"
    PAGE_SIZE = 50

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("LIVESTORM_API_KEY")
        if not self.api_key:
            raise ValueError("LIVESTORM_API_KEY not set")
        self._session = requests.Session()
        self._session.headers["Authorization"] = self.api_key
        self.request_count = 0
        self.monthly_remaining = None

    def _get(self, path: str, params: dict | None = None, retries: int = 3) -> dict:
        url = f"{self.BASE_URL}{path}"
        for attempt in range(retries):
            resp = self._session.get(url, params=params, timeout=60)
            self.request_count += 1
            remaining = resp.headers.get("RateLimit-Monthly-Remaining")
            if remaining is not None:
                self.monthly_remaining = int(remaining)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 5))
                log.warning("Rate limited, waiting %ds (attempt %d)", wait, attempt + 1)
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                wait = 2 ** attempt
                log.warning("Server error %d on %s, retrying in %ds (attempt %d)",
                            resp.status_code, path, wait, attempt + 1)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        raise requests.HTTPError(
            f"Failed after {retries} retries: {resp.status_code} {path}",
            response=resp,
        )

    def paginate(self, path: str, params: dict | None = None) -> Iterator[dict]:
        """Yield all items across all pages."""
        params = dict(params or {})
        params["page[size]"] = self.PAGE_SIZE
        page = 0
        while True:
            params["page[number]"] = page
            result = self._get(path, params)
            for item in result.get("data", []):
                yield item
            meta = result.get("meta", {})
            if page + 1 >= meta.get("page_count", 1):
                break
            page += 1

    def get_events(self) -> list[dict]:
        return list(self.paginate("/events"))

    def get_event_sessions(self, event_id: str) -> list[dict]:
        return list(self.paginate(f"/events/{event_id}/sessions"))

    def get_session_people(self, session_id: str) -> list[dict]:
        return list(self.paginate(f"/sessions/{session_id}/people"))


# ---------------------------------------------------------------------------
# Grist API client
# ---------------------------------------------------------------------------

class GristClient:
    """Grist REST API client."""

    BASE_URL = "https://grist.numerique.gouv.fr/api"

    def __init__(
        self,
        api_key: str | None = None,
        doc_id: str | None = None,
    ):
        self.api_key = api_key or os.getenv("GRIST_API_KEY")
        self.doc_id = doc_id or os.getenv("GRIST_WEBINAIRES_DOC_ID")
        if not self.api_key:
            raise ValueError("GRIST_API_KEY not set")
        if not self.doc_id:
            raise ValueError("GRIST_WEBINAIRES_DOC_ID not set")
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {self.api_key}"
        self.request_count = 0

    def get_records(self, table_id: str) -> list[dict]:
        """Fetch all records from a table. Uses /records (not /data)."""
        url = f"{self.BASE_URL}/docs/{self.doc_id}/tables/{table_id}/records"
        resp = self._session.get(url, timeout=30)
        self.request_count += 1
        resp.raise_for_status()
        return resp.json().get("records", [])


# ---------------------------------------------------------------------------
# Database schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS webinars (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    title TEXT,
    description TEXT,
    organizer_email TEXT,
    product TEXT,
    status TEXT,
    started_at TEXT,
    ended_at TEXT,
    duration_minutes INTEGER,
    capacity INTEGER,
    registrants_count INTEGER,
    attendees_count INTEGER,
    registration_url TEXT,
    webinar_url TEXT,
    raw_json TEXT,
    synced_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    webinar_id TEXT REFERENCES webinars(id),
    status TEXT,
    started_at TEXT,
    ended_at TEXT,
    duration_seconds INTEGER,
    registrants_count INTEGER,
    attendees_count INTEGER,
    room_link TEXT,
    synced_at TEXT
);

CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    webinar_id TEXT NOT NULL,
    session_id TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    organisation TEXT,
    registered INTEGER DEFAULT 1,
    attended INTEGER,
    attendance_rate REAL,
    attendance_duration_seconds INTEGER,
    has_viewed_replay INTEGER,
    custom_fields TEXT,
    registered_at TEXT,
    synced_at TEXT,
    UNIQUE(source, webinar_id, session_id, email)
);

CREATE TABLE IF NOT EXISTS sync_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_reg_email ON registrations(email);
CREATE INDEX IF NOT EXISTS idx_reg_org ON registrations(organisation);
CREATE INDEX IF NOT EXISTS idx_reg_webinar ON registrations(webinar_id);
CREATE INDEX IF NOT EXISTS idx_reg_source_unique
    ON registrations(source, webinar_id, session_id, email);
CREATE INDEX IF NOT EXISTS idx_sessions_webinar ON sessions(webinar_id);
"""


def ensure_schema(conn: sqlite3.Connection):
    conn.executescript(SCHEMA_SQL)
    conn.executescript(INDEX_SQL)
    conn.commit()


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------

def _ts_to_iso(ts) -> str | None:
    """Convert a Unix timestamp (int or float) to ISO8601 string."""
    if ts is None or ts == 0:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OSError):
        return None


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Livestorm sync
# ---------------------------------------------------------------------------

def _extract_custom_field(fields: list[dict], field_id: str) -> str | None:
    """Extract a field value from Livestorm registration fields."""
    for f in fields:
        if f.get("id") == field_id:
            val = f.get("value")
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            return str(val) if val else None
    return None


def _extract_organisation(fields: list[dict]) -> str | None:
    """Try to extract organisation from various custom field names."""
    for field_id in (
        "company",
        "votre_structure",
        "quel_est_le_nom_de_votre_structure",
        "nom_de_votre_structure",
        "structure",
        "organisation",
        "entreprise",
    ):
        val = _extract_custom_field(fields, field_id)
        if val:
            return val
    return None


def sync_livestorm(conn: sqlite3.Connection, client: LivestormClient):
    """Full Livestorm sync: events -> sessions -> people."""
    now = _now_iso()

    # Phase 1: Events
    print("  Fetching events...")
    events = client.get_events()
    print(f"  {len(events)} events")

    for ev in events:
        attrs = ev["attributes"]
        source_id = ev["id"]
        webinar_id = f"livestorm:{source_id}"
        title = attrs.get("title", "")
        organizer = attrs.get("owner", {})
        organizer_email = None
        if isinstance(organizer, dict):
            organizer_attrs = organizer.get("attributes", {})
            organizer_email = organizer_attrs.get("email")

        conn.execute(
            """INSERT OR REPLACE INTO webinars
               (id, source, source_id, title, description, organizer_email,
                product, status, duration_minutes, registrants_count,
                registration_url, webinar_url, raw_json, synced_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                webinar_id,
                "livestorm",
                source_id,
                title,
                attrs.get("description"),
                organizer_email,
                infer_product(title, organizer_email),
                attrs.get("scheduling_status"),
                attrs.get("estimated_duration"),
                attrs.get("sessions_count"),
                attrs.get("registration_link"),
                attrs.get("registration_link"),
                json.dumps(ev, ensure_ascii=False),
                now,
            ),
        )
    conn.commit()
    print(f"  Events synced ({client.request_count} API calls so far)")

    # Phase 2: Sessions
    print("  Fetching sessions...")
    session_count = 0
    for i, ev in enumerate(events):
        source_id = ev["id"]
        webinar_id = f"livestorm:{source_id}"
        sessions = client.get_event_sessions(source_id)
        for sess in sessions:
            sa = sess["attributes"]
            sess_id = f"livestorm:{sess['id']}"
            conn.execute(
                """INSERT OR REPLACE INTO sessions
                   (id, webinar_id, status, started_at, ended_at,
                    duration_seconds, registrants_count, attendees_count,
                    room_link, synced_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sess_id,
                    webinar_id,
                    sa.get("status"),
                    _ts_to_iso(sa.get("started_at") or sa.get("estimated_started_at")),
                    _ts_to_iso(sa.get("ended_at")),
                    sa.get("duration"),
                    sa.get("registrants_count"),
                    sa.get("attendees_count"),
                    sa.get("room_link"),
                    now,
                ),
            )
            session_count += 1
        if (i + 1) % 50 == 0:
            conn.commit()
            print(f"    {i+1}/{len(events)} events processed, "
                  f"{session_count} sessions ({client.request_count} calls)")
    conn.commit()
    print(f"  {session_count} sessions synced ({client.request_count} API calls so far)")

    # Phase 3: People per session
    # Only fetch people for sessions not yet synced (incremental)
    already_synced = set(
        row[0] for row in conn.execute(
            "SELECT DISTINCT session_id FROM registrations WHERE source='livestorm'"
        ).fetchall()
    )
    all_sessions = conn.execute(
        "SELECT id FROM sessions WHERE id LIKE 'livestorm:%'"
    ).fetchall()
    to_sync = [(s,) for (s,) in all_sessions if s not in already_synced]
    print(f"  Fetching attendance data: {len(to_sync)} sessions "
          f"({len(all_sessions) - len(to_sync)} already synced)")
    reg_count = 0
    skipped_sessions = 0
    for i, (sess_id_row,) in enumerate(to_sync):
        livestorm_sess_id = sess_id_row.replace("livestorm:", "")
        webinar_id = conn.execute(
            "SELECT webinar_id FROM sessions WHERE id = ?", (sess_id_row,)
        ).fetchone()[0]

        try:
            people = client.get_session_people(livestorm_sess_id)
        except Exception as e:
            log.warning("Skipping session %s: %s", livestorm_sess_id, e)
            skipped_sessions += 1
            continue
        for person in people:
            pa = person["attributes"]
            rd = pa.get("registrant_detail") or {}
            fields = rd.get("fields", [])

            email = pa.get("email")
            if not email:
                continue

            organisation = _extract_organisation(fields)
            custom = {f["id"]: f.get("value") for f in fields
                      if f.get("id") not in ("email", "first_name", "last_name")}

            conn.execute(
                """INSERT INTO registrations
                   (source, webinar_id, session_id, email, first_name, last_name,
                    organisation, registered, attended, attendance_rate,
                    attendance_duration_seconds, has_viewed_replay,
                    custom_fields, registered_at, synced_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source, webinar_id, session_id, email)
                   DO UPDATE SET
                       first_name=excluded.first_name,
                       last_name=excluded.last_name,
                       organisation=excluded.organisation,
                       attended=excluded.attended,
                       attendance_rate=excluded.attendance_rate,
                       attendance_duration_seconds=excluded.attendance_duration_seconds,
                       has_viewed_replay=excluded.has_viewed_replay,
                       custom_fields=excluded.custom_fields,
                       synced_at=excluded.synced_at""",
                (
                    "livestorm",
                    webinar_id,
                    sess_id_row,
                    email.lower().strip(),
                    pa.get("first_name"),
                    pa.get("last_name"),
                    organisation,
                    1 if rd.get("attended") else 0,
                    rd.get("attendance_rate"),
                    rd.get("attendance_duration"),
                    1 if rd.get("has_viewed_replay") else 0,
                    json.dumps(custom, ensure_ascii=False) if custom else None,
                    _ts_to_iso(rd.get("created_at")),
                    now,
                ),
            )
            reg_count += 1

        if (i + 1) % 100 == 0:
            conn.commit()
            print(f"    {i+1}/{len(to_sync)} sessions, "
                  f"{reg_count} registrations ({client.request_count} calls, "
                  f"monthly remaining: {client.monthly_remaining})")

    conn.commit()
    print(f"  {reg_count} registrations synced ({client.request_count} API calls total)")
    if skipped_sessions:
        print(f"  WARNING: {skipped_sessions} sessions skipped due to API errors")
    return len(events), session_count, reg_count


# ---------------------------------------------------------------------------
# Grist sync
# ---------------------------------------------------------------------------

def _grist_ts_to_iso(ts) -> str | None:
    """Convert Grist timestamp (seconds since epoch, float) to ISO8601."""
    if ts is None or ts == 0:
        return None
    return _ts_to_iso(ts)


def _grist_duration_to_minutes(duree: str | None) -> int | None:
    """Parse Grist duration choice ('30 min', '45 min', '60 min')."""
    if not duree:
        return None
    m = re.search(r"(\d+)", str(duree))
    return int(m.group(1)) if m else None


def sync_grist(conn: sqlite3.Connection, client: GristClient):
    """Full Grist sync (always full replace for this small dataset)."""
    now = _now_iso()

    # Phase 1: Webinaires
    print("  Fetching Webinaires...")
    webinaires = client.get_records("Webinaires")
    print(f"  {len(webinaires)} webinaires")

    for rec in webinaires:
        f = rec["fields"]
        event_id = f.get("event_id", "")
        if not event_id:
            continue
        source_id = event_id
        webinar_id = f"grist:{source_id}"
        title = f.get("titre", "")
        organizer_email = f.get("organizer_email")

        conn.execute(
            """INSERT OR REPLACE INTO webinars
               (id, source, source_id, title, description, organizer_email,
                product, status, started_at, ended_at, duration_minutes,
                capacity, registrants_count, registration_url, webinar_url,
                raw_json, synced_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                webinar_id,
                "grist",
                source_id,
                title,
                f.get("description"),
                organizer_email,
                infer_product(title, organizer_email),
                "active" if f.get("status") else "inactive",
                _grist_ts_to_iso(f.get("date_event")),
                _grist_ts_to_iso(f.get("date_fin")),
                _grist_duration_to_minutes(f.get("duree")),
                f.get("capacite"),
                f.get("nb_inscrits"),
                f.get("form_inscription_url"),
                f.get("lien_webinaire"),
                json.dumps(rec, ensure_ascii=False),
                now,
            ),
        )
    conn.commit()

    # Phase 2: Inscriptions
    print("  Fetching Inscriptions...")
    inscriptions = client.get_records("Inscriptions")
    print(f"  {len(inscriptions)} inscriptions")

    reg_count = 0
    for rec in inscriptions:
        f = rec["fields"]
        email = f.get("email")
        if not email:
            continue
        event_id = f.get("event_id", "")
        webinar_id = f"grist:{event_id}" if event_id else None

        conn.execute(
            """INSERT INTO registrations
               (source, webinar_id, session_id, email, first_name, last_name,
                organisation, registered, attended, registered_at, synced_at)
               VALUES (?, ?, '', ?, ?, ?, ?, 1, ?, ?, ?)
               ON CONFLICT(source, webinar_id, session_id, email)
               DO UPDATE SET
                   first_name=excluded.first_name,
                   last_name=excluded.last_name,
                   organisation=excluded.organisation,
                   attended=excluded.attended,
                   registered_at=excluded.registered_at,
                   synced_at=excluded.synced_at""",
            (
                "grist",
                webinar_id,
                email.lower().strip(),
                f.get("prenom"),
                f.get("nom"),
                f.get("entreprise"),
                1 if f.get("a_participe") else 0,
                _grist_ts_to_iso(f.get("date_inscription")),
                now,
            ),
        )
        reg_count += 1

    conn.commit()
    print(f"  {reg_count} registrations synced ({client.request_count} API calls)")
    return len(webinaires), reg_count
