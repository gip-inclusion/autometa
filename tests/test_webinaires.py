"""Tests for lib.webinaires: schema, helpers, Grist sync, upsert logic."""

import sqlite3

import pytest

from lib.webinaires import (
    T_INSCRIPTIONS,
    T_SESSIONS,
    T_SYNC_META,
    T_WEBINAIRES,
    GristClient,
    batch_upsert,
    ensure_schema,
    extract_organisation,
    grist_duration_to_minutes,
    infer_product,
    sync_grist,
    ts_to_iso,
)


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    return conn


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
    result = ts_to_iso(value)
    assert (result is None) == expected_none


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


def test_schema_tables_exist(db):
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert T_WEBINAIRES in tables
    assert T_SESSIONS in tables
    assert T_INSCRIPTIONS in tables
    assert T_SYNC_META in tables


def test_schema_ensure_schema_idempotent(db):
    """Calling ensure_schema twice doesn't fail."""
    ensure_schema(db)
    ensure_schema(db)


def test_schema_registration_unique_constraint(db):
    """Duplicate (source, webinar_id, session_id, email) is rejected."""
    db.execute(
        f"INSERT INTO {T_INSCRIPTIONS} (source, webinar_id, session_id, email) VALUES ('test', 'w1', 's1', 'a@b.com')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            f"INSERT INTO {T_INSCRIPTIONS} (source, webinar_id, session_id, email) "
            "VALUES ('test', 'w1', 's1', 'a@b.com')"
        )


def test_schema_registration_different_sessions_ok(db):
    db.execute(
        f"INSERT INTO {T_INSCRIPTIONS} (source, webinar_id, session_id, email) VALUES ('test', 'w1', 's1', 'a@b.com')"
    )
    db.execute(
        f"INSERT INTO {T_INSCRIPTIONS} (source, webinar_id, session_id, email) VALUES ('test', 'w1', 's2', 'a@b.com')"
    )
    count = db.execute(f"SELECT COUNT(*) FROM {T_INSCRIPTIONS}").fetchone()[0]
    assert count == 2


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
            "form_inscription_url": "https://tally.so/r/yyy",
        },
    },
]

SAMPLE_INSCRIPTIONS = [
    {
        "id": 1,
        "fields": {
            "email": "nora@example.fr",
            "nom": "Bentadmia",
            "prenom": "Nora",
            "entreprise": "CIO d'Elancourt",
            "date_inscription": 1767715153.834,
            "a_participe": False,
            "event_id": "dora-prise-en-main-001",
        },
    },
    {
        "id": 2,
        "fields": {
            "email": "Laure@EXAMPLE.FR",
            "nom": "SORBEE",
            "prenom": "Laure",
            "entreprise": "ESAT Les Néfliers",
            "date_inscription": 1767775834.152,
            "a_participe": True,
            "event_id": "dora-prise-en-main-001",
        },
    },
    {
        "id": 3,
        "fields": {
            "email": "julie@example.fr",
            "nom": "Dupont",
            "prenom": "Julie",
            "entreprise": "Mission Locale de Reims",
            "date_inscription": 1770000000,
            "a_participe": True,
            "event_id": "missions-locales-001",
        },
    },
]


BATCH_UPSERT_INSERT_PREFIX = f"INSERT INTO {T_WEBINAIRES} (id, source, source_id, title) VALUES "
BATCH_UPSERT_CONFLICT_SUFFIX = " ON CONFLICT(id) DO UPDATE SET title=excluded.title"


def test_batch_upsert_inserts_all_rows(db):
    """All rows are inserted across batches."""
    rows = [(f"id-{i}", "grist", f"src-{i}", f"title-{i}") for i in range(250)]
    batch_upsert(db, BATCH_UPSERT_INSERT_PREFIX, BATCH_UPSERT_CONFLICT_SUFFIX, rows, batch_size=100)
    db.commit()
    count = db.execute(f"SELECT COUNT(*) FROM {T_WEBINAIRES}").fetchone()[0]
    assert count == 250


def test_batch_upsert_upsert_on_conflict(db):
    """ON CONFLICT updates existing rows."""
    batch_upsert(
        db, BATCH_UPSERT_INSERT_PREFIX, BATCH_UPSERT_CONFLICT_SUFFIX, [("id-1", "grist", "src-1", "old title")]
    )
    db.commit()
    batch_upsert(
        db, BATCH_UPSERT_INSERT_PREFIX, BATCH_UPSERT_CONFLICT_SUFFIX, [("id-1", "grist", "src-1", "new title")]
    )
    db.commit()
    title = db.execute(f"SELECT title FROM {T_WEBINAIRES} WHERE id='id-1'").fetchone()[0]
    assert title == "new title"


def test_batch_upsert_empty_rows(db):
    """Empty row list is a no-op."""
    batch_upsert(db, BATCH_UPSERT_INSERT_PREFIX, BATCH_UPSERT_CONFLICT_SUFFIX, [])
    count = db.execute(f"SELECT COUNT(*) FROM {T_WEBINAIRES}").fetchone()[0]
    assert count == 0


def test_batch_upsert_handles_special_characters(db):
    """Values with quotes and special chars are escaped properly."""
    rows = [("id-quote", "grist", "src-q", "It's a \"test\" with 'quotes'")]
    batch_upsert(db, BATCH_UPSERT_INSERT_PREFIX, BATCH_UPSERT_CONFLICT_SUFFIX, rows)
    db.commit()
    title = db.execute(f"SELECT title FROM {T_WEBINAIRES} WHERE id='id-quote'").fetchone()[0]
    assert title == "It's a \"test\" with 'quotes'"


def test_batch_upsert_handles_none_values(db):
    """None values are inserted as NULL."""
    rows = [("id-null", "grist", "src-n", None)]
    batch_upsert(db, BATCH_UPSERT_INSERT_PREFIX, BATCH_UPSERT_CONFLICT_SUFFIX, rows)
    db.commit()
    title = db.execute(f"SELECT title FROM {T_WEBINAIRES} WHERE id='id-null'").fetchone()[0]
    assert title is None


def test_batch_upsert_exact_batch_boundary(db):
    """Row count exactly equal to batch_size works."""
    rows = [(f"id-{i}", "grist", f"src-{i}", f"t-{i}") for i in range(100)]
    batch_upsert(db, BATCH_UPSERT_INSERT_PREFIX, BATCH_UPSERT_CONFLICT_SUFFIX, rows, batch_size=100)
    db.commit()
    count = db.execute(f"SELECT COUNT(*) FROM {T_WEBINAIRES}").fetchone()[0]
    assert count == 100


def test_grist_sync_webinars(mocker, db, grist_client):
    """Webinaires are inserted with correct fields."""

    def mock_get(url, **kwargs):
        if "Webinaires" in url:
            return mock_grist_response(mocker, SAMPLE_WEBINAIRES)
        return mock_grist_response(mocker, [])

    grist_client._session.get.side_effect = mock_get
    sync_grist(db, grist_client)

    rows = db.execute(f"SELECT * FROM {T_WEBINAIRES} ORDER BY id").fetchall()
    assert len(rows) == 2

    dora = dict(rows[0])
    assert dora["id"] == "grist:dora-prise-en-main-001"
    assert dora["source"] == "grist"
    assert dora["title"] == "DORA présentation et prise en main"
    assert dora["product"] == "dora"
    assert dora["duration_minutes"] == 60
    assert dora["capacity"] == 350


def test_grist_sync_inscriptions(mocker, db, grist_client):
    """Inscriptions are inserted with correct fields."""

    def mock_get(url, **kwargs):
        if "Webinaires" in url:
            return mock_grist_response(mocker, SAMPLE_WEBINAIRES)
        if "Inscriptions" in url:
            return mock_grist_response(mocker, SAMPLE_INSCRIPTIONS)
        return mock_grist_response(mocker, [])

    grist_client._session.get.side_effect = mock_get
    sync_grist(db, grist_client)

    rows = db.execute(f"SELECT * FROM {T_INSCRIPTIONS} ORDER BY email").fetchall()
    assert len(rows) == 3

    julie = dict(rows[0])
    assert julie["email"] == "julie@example.fr"
    assert julie["first_name"] == "Julie"
    assert julie["last_name"] == "Dupont"
    assert julie["organisation"] == "Mission Locale de Reims"
    assert julie["attended"] == 1
    assert julie["webinar_id"] == "grist:missions-locales-001"
    assert julie["session_id"] == ""


def test_grist_sync_email_lowercased(mocker, db, grist_client):
    """Emails are normalized to lowercase."""

    def mock_get(url, **kwargs):
        if "Webinaires" in url:
            return mock_grist_response(mocker, SAMPLE_WEBINAIRES)
        if "Inscriptions" in url:
            return mock_grist_response(mocker, SAMPLE_INSCRIPTIONS)
        return mock_grist_response(mocker, [])

    grist_client._session.get.side_effect = mock_get
    sync_grist(db, grist_client)

    emails = [r[0] for r in db.execute(f"SELECT email FROM {T_INSCRIPTIONS} ORDER BY email").fetchall()]
    assert all(e == e.lower() for e in emails)
    assert "laure@example.fr" in emails


def test_grist_sync_idempotent(mocker, db, grist_client):
    """Running sync twice doesn't duplicate data."""

    def mock_get(url, **kwargs):
        if "Webinaires" in url:
            return mock_grist_response(mocker, SAMPLE_WEBINAIRES)
        if "Inscriptions" in url:
            return mock_grist_response(mocker, SAMPLE_INSCRIPTIONS)
        return mock_grist_response(mocker, [])

    grist_client._session.get.side_effect = mock_get

    sync_grist(db, grist_client)
    sync_grist(db, grist_client)

    webinar_count = db.execute(f"SELECT COUNT(*) FROM {T_WEBINAIRES}").fetchone()[0]
    reg_count = db.execute(f"SELECT COUNT(*) FROM {T_INSCRIPTIONS}").fetchone()[0]
    assert webinar_count == 2
    assert reg_count == 3


def test_grist_sync_updates_on_resync(mocker, db, grist_client):
    """Re-syncing updates changed fields (e.g. a_participe)."""

    def mock_get_v1(url, **kwargs):
        if "Webinaires" in url:
            return mock_grist_response(mocker, SAMPLE_WEBINAIRES)
        if "Inscriptions" in url:
            return mock_grist_response(mocker, SAMPLE_INSCRIPTIONS[:1])
        return mock_grist_response(mocker, [])

    grist_client._session.get.side_effect = mock_get_v1
    sync_grist(db, grist_client)

    attended = db.execute(f"SELECT attended FROM {T_INSCRIPTIONS} WHERE email='nora@example.fr'").fetchone()[0]
    assert attended == 0

    updated = [
        {
            "id": 1,
            "fields": {
                **SAMPLE_INSCRIPTIONS[0]["fields"],
                "a_participe": True,
            },
        }
    ]

    def mock_get_v2(url, **kwargs):
        if "Webinaires" in url:
            return mock_grist_response(mocker, SAMPLE_WEBINAIRES)
        if "Inscriptions" in url:
            return mock_grist_response(mocker, updated)
        return mock_grist_response(mocker, [])

    grist_client._session.get.side_effect = mock_get_v2
    sync_grist(db, grist_client)

    attended = db.execute(f"SELECT attended FROM {T_INSCRIPTIONS} WHERE email='nora@example.fr'").fetchone()[0]
    assert attended == 1


def test_grist_sync_skips_empty_email(mocker, db, grist_client):
    """Records without email are skipped."""
    no_email = [
        {
            "id": 99,
            "fields": {
                "email": "",
                "nom": "Ghost",
                "prenom": "User",
                "event_id": "dora-prise-en-main-001",
            },
        }
    ]

    def mock_get(url, **kwargs):
        if "Webinaires" in url:
            return mock_grist_response(mocker, SAMPLE_WEBINAIRES)
        if "Inscriptions" in url:
            return mock_grist_response(mocker, no_email)
        return mock_grist_response(mocker, [])

    grist_client._session.get.side_effect = mock_get
    sync_grist(db, grist_client)

    count = db.execute(f"SELECT COUNT(*) FROM {T_INSCRIPTIONS}").fetchone()[0]
    assert count == 0


def test_grist_sync_skips_empty_event_id(mocker, db, grist_client):
    """Webinaires without event_id are skipped."""
    no_event_id = [
        {
            "id": 99,
            "fields": {
                "event_id": "",
                "titre": "Orphan webinar",
            },
        }
    ]

    def mock_get(url, **kwargs):
        if "Webinaires" in url:
            return mock_grist_response(mocker, no_event_id)
        return mock_grist_response(mocker, [])

    grist_client._session.get.side_effect = mock_get
    sync_grist(db, grist_client)

    count = db.execute(f"SELECT COUNT(*) FROM {T_WEBINAIRES}").fetchone()[0]
    assert count == 0


def test_grist_sync_return_value(mocker, db, grist_client):
    """sync_grist returns (webinar_count, registration_count)."""

    def mock_get(url, **kwargs):
        if "Webinaires" in url:
            return mock_grist_response(mocker, SAMPLE_WEBINAIRES)
        if "Inscriptions" in url:
            return mock_grist_response(mocker, SAMPLE_INSCRIPTIONS)
        return mock_grist_response(mocker, [])

    grist_client._session.get.side_effect = mock_get
    webinars, regs = sync_grist(db, grist_client)
    assert webinars == 2
    assert regs == 3
