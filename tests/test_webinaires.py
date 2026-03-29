"""Tests for lib.webinaires: helpers, Grist sync, upsert logic."""

import sqlite3

import pytest

from lib.webinaires import (
    T_INSCRIPTIONS,
    T_WEBINAIRES,
    GristClient,
    batch_upsert,
    extract_organisation,
    grist_duration_to_minutes,
    infer_product,
    sync_grist,
    ts_to_iso,
)


@pytest.fixture
def conn():
    """In-memory SQLite mimicking the DatalakeWriter interface for testing."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    # Why: these tables live in the remote datalake (Metabase PostgreSQL), not in our app DB.
    # We use SQLite here as a local test double for the DatalakeWriter.execute() interface.
    db.executescript(f"""
        CREATE TABLE {T_WEBINAIRES} (
            id TEXT PRIMARY KEY, source TEXT NOT NULL, source_id TEXT NOT NULL,
            title TEXT, description TEXT, organizer_email TEXT, product TEXT,
            status TEXT, started_at TEXT, ended_at TEXT, duration_minutes INTEGER,
            capacity INTEGER, registrants_count INTEGER, attendees_count INTEGER,
            registration_url TEXT, webinar_url TEXT, raw_json TEXT, synced_at TEXT
        );
        CREATE TABLE {T_INSCRIPTIONS} (
            id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL,
            webinar_id TEXT NOT NULL, session_id TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL, first_name TEXT, last_name TEXT, organisation TEXT,
            registered INTEGER DEFAULT 1, attended INTEGER, attendance_rate REAL,
            attendance_duration_seconds INTEGER, has_viewed_replay INTEGER,
            custom_fields TEXT, registered_at TEXT, synced_at TEXT,
            UNIQUE(source, webinar_id, session_id, email)
        );
    """)
    return db


@pytest.fixture
def grist_client(mocker):
    mocker.patch("lib.webinaires.config.GRIST_API_KEY", "fake-key")
    mocker.patch("lib.webinaires.config.GRIST_WEBINAIRES_DOC_ID", "fake-doc")
    client = GristClient()
    client._session = mocker.MagicMock()
    return client


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Présentation de DORA et prise en main", "dora"),
        ("Devenez expert des achats inclusifs", "marche"),
        ("Découvrez le Marché de l'inclusion", "marche"),
        ("Webinaire Pilotage : indicateurs", "pilotage"),
        ("Utiliser le site d'Immersion Facilitée", "immersion"),
        ("Bienvenue sur la Communauté", "communaute"),
        ("Formation RDV-Insertion pour les CD", "rdv-insertion"),
        ("Les emplois de l'inclusion", "emplois"),
        ("Webinaire pour les prescripteurs habilités", "emplois"),
        ("Comprendre le Pass IAE", "emplois"),
        ("Formation générale sur le numérique", None),
        ("", None),
        (None, None),
        ("DORA pour les prescripteurs", "dora"),
    ],
)
def test_infer_product(title, expected):
    assert infer_product(title) == expected


def test_ts_to_iso_valid_timestamp():
    result = ts_to_iso(1700000000)
    assert result.startswith("2023-11-14")
    assert "+00:00" in result


@pytest.mark.parametrize(
    "value,expected_none",
    [
        (1700000000.5, False),
        (0, True),
        (None, True),
        ("not-a-number", True),
    ],
)
def test_ts_to_iso_edge_cases(value, expected_none):
    assert (ts_to_iso(value) is None) == expected_none


@pytest.mark.parametrize(
    "value,expected",
    [
        ("30 min", 30),
        ("45 min", 45),
        ("60 min", 60),
        (None, None),
        ("", None),
    ],
)
def test_grist_duration_to_minutes(value, expected):
    assert grist_duration_to_minutes(value) == expected


@pytest.mark.parametrize(
    "fields,expected",
    [
        ([{"id": "company", "value": "ACME Corp"}], "ACME Corp"),
        ([{"id": "quel_est_le_nom_de_votre_structure", "value": "PLIE Bordeaux"}], "PLIE Bordeaux"),
        ([{"id": "entreprise", "value": "Mission Locale"}], "Mission Locale"),
        ([{"id": "departement", "value": "75"}], None),
        ([], None),
        ([{"id": "entreprise", "value": "second"}, {"id": "company", "value": "first"}], "first"),
        ([{"id": "company", "value": ""}, {"id": "entreprise", "value": "Fallback"}], "Fallback"),
    ],
)
def test_extract_organisation(fields, expected):
    assert extract_organisation(fields) == expected


def test_registration_unique_constraint(conn):
    conn.execute(
        f"INSERT INTO {T_INSCRIPTIONS} (source, webinar_id, session_id, email) VALUES ('test', 'w1', 's1', 'a@b.com')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            f"INSERT INTO {T_INSCRIPTIONS} (source, webinar_id, session_id, email) VALUES ('test', 'w1', 's1', 'a@b.com')"
        )


BATCH_UPSERT_INSERT_PREFIX = f"INSERT INTO {T_WEBINAIRES} (id, source, source_id, title) VALUES "
BATCH_UPSERT_CONFLICT_SUFFIX = " ON CONFLICT(id) DO UPDATE SET title=excluded.title"


def test_batch_upsert_inserts_all_rows(conn):
    rows = [(f"id-{i}", "grist", f"src-{i}", f"title-{i}") for i in range(250)]
    batch_upsert(conn, BATCH_UPSERT_INSERT_PREFIX, BATCH_UPSERT_CONFLICT_SUFFIX, rows, batch_size=100)
    conn.commit()
    assert conn.execute(f"SELECT COUNT(*) FROM {T_WEBINAIRES}").fetchone()[0] == 250


def test_batch_upsert_upsert_on_conflict(conn):
    batch_upsert(conn, BATCH_UPSERT_INSERT_PREFIX, BATCH_UPSERT_CONFLICT_SUFFIX, [("id-1", "grist", "src-1", "old")])
    conn.commit()
    batch_upsert(conn, BATCH_UPSERT_INSERT_PREFIX, BATCH_UPSERT_CONFLICT_SUFFIX, [("id-1", "grist", "src-1", "new")])
    conn.commit()
    assert conn.execute(f"SELECT title FROM {T_WEBINAIRES} WHERE id='id-1'").fetchone()[0] == "new"


def test_batch_upsert_empty_rows(conn):
    batch_upsert(conn, BATCH_UPSERT_INSERT_PREFIX, BATCH_UPSERT_CONFLICT_SUFFIX, [])
    assert conn.execute(f"SELECT COUNT(*) FROM {T_WEBINAIRES}").fetchone()[0] == 0


def test_batch_upsert_handles_special_characters(conn):
    rows = [("id-q", "grist", "src-q", "It's a \"test\" with 'quotes'")]
    batch_upsert(conn, BATCH_UPSERT_INSERT_PREFIX, BATCH_UPSERT_CONFLICT_SUFFIX, rows)
    conn.commit()
    assert (
        conn.execute(f"SELECT title FROM {T_WEBINAIRES} WHERE id='id-q'").fetchone()[0]
        == "It's a \"test\" with 'quotes'"
    )


def test_batch_upsert_handles_none_values(conn):
    batch_upsert(conn, BATCH_UPSERT_INSERT_PREFIX, BATCH_UPSERT_CONFLICT_SUFFIX, [("id-n", "grist", "src-n", None)])
    conn.commit()
    assert conn.execute(f"SELECT title FROM {T_WEBINAIRES} WHERE id='id-n'").fetchone()[0] is None


def mock_grist_response(mocker, records):
    resp = mocker.MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"records": records}
    resp.raise_for_status = mocker.MagicMock()
    return resp


SAMPLE_WEBINAIRES = [
    {
        "id": 11,
        "fields": {
            "event_id": "dora-prise-en-main-001",
            "titre": "DORA présentation et prise en main",
            "description": "Découvrez DORA",
            "organizer_email": "delphine@inclusion.gouv.fr",
            "duree": "60 min",
            "date_event": 1769086800,
            "date_fin": 1769090400,
            "lien_webinaire": "https://webinaire.example.com/1",
            "capacite": 350,
            "nb_inscrits": 2,
            "status": True,
            "form_inscription_url": "https://tally.so/r/xxx",
        },
    },
    {
        "id": 23,
        "fields": {
            "event_id": "missions-locales-001",
            "titre": "Webinaire special Missions Locales",
            "description": "L'essentiel pour les Missions Locales",
            "organizer_email": "aurelie@inclusion.gouv.fr",
            "duree": "45 min",
            "date_event": 1770195600,
            "date_fin": 1770198300,
            "lien_webinaire": "https://webinaire.example.com/2",
            "capacite": 350,
            "nb_inscrits": 220,
            "status": True,
        },
    },
]

SAMPLE_INSCRIPTIONS = [
    {
        "id": 101,
        "fields": {
            "event_id": "missions-locales-001",
            "email": "julie@example.fr",
            "prenom": "Julie",
            "nom": "Dupont",
            "entreprise": "Mission Locale de Reims",
            "a_participe": True,
        },
    },
    {
        "id": 102,
        "fields": {
            "event_id": "missions-locales-001",
            "email": "Pierre@Example.fr",
            "prenom": "Pierre",
            "nom": "Martin",
            "quel_est_le_nom_de_votre_structure": "PLIE Bordeaux",
            "a_participe": False,
        },
    },
    {
        "id": 103,
        "fields": {"event_id": "missions-locales-001", "email": "marie@example.fr", "prenom": "Marie", "nom": "Durand"},
    },
]


def test_grist_sync_webinars(mocker, conn, grist_client):
    def mock_get(url, **kwargs):
        if "Webinaires" in url:
            return mock_grist_response(mocker, SAMPLE_WEBINAIRES)
        return mock_grist_response(mocker, [])

    grist_client._session.get.side_effect = mock_get
    sync_grist(conn, grist_client)

    rows = conn.execute(f"SELECT * FROM {T_WEBINAIRES} ORDER BY id").fetchall()
    assert len(rows) == 2
    dora = dict(rows[0])
    assert dora["id"] == "grist:dora-prise-en-main-001"
    assert dora["source"] == "grist"
    assert dora["title"] == "DORA présentation et prise en main"
    assert dora["product"] == "dora"
    assert dora["duration_minutes"] == 60
    assert dora["capacity"] == 350


def test_grist_sync_inscriptions(mocker, conn, grist_client):
    def mock_get(url, **kwargs):
        if "Webinaires" in url:
            return mock_grist_response(mocker, SAMPLE_WEBINAIRES)
        if "Inscriptions" in url:
            return mock_grist_response(mocker, SAMPLE_INSCRIPTIONS)
        return mock_grist_response(mocker, [])

    grist_client._session.get.side_effect = mock_get
    sync_grist(conn, grist_client)

    rows = conn.execute(f"SELECT * FROM {T_INSCRIPTIONS} ORDER BY email").fetchall()
    assert len(rows) == 3
    julie = dict(rows[0])
    assert julie["email"] == "julie@example.fr"
    assert julie["first_name"] == "Julie"
    assert julie["organisation"] == "Mission Locale de Reims"
    assert julie["attended"] == 1


def test_grist_sync_email_lowercased(mocker, conn, grist_client):
    def mock_get(url, **kwargs):
        if "Webinaires" in url:
            return mock_grist_response(mocker, SAMPLE_WEBINAIRES)
        if "Inscriptions" in url:
            return mock_grist_response(mocker, SAMPLE_INSCRIPTIONS)
        return mock_grist_response(mocker, [])

    grist_client._session.get.side_effect = mock_get
    sync_grist(conn, grist_client)

    emails = [r[0] for r in conn.execute(f"SELECT email FROM {T_INSCRIPTIONS} ORDER BY email").fetchall()]
    assert "pierre@example.fr" in emails
    assert "Pierre@Example.fr" not in emails
