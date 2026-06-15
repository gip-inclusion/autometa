from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from web.conversation_embeddings import generate_conversation_embeddings as embeddings


def _row(
    *,
    message_id=1,
    conversation_id=10,
    user_id="alice@example.com",
    role="user",
    content="Bonjour Autometa",
    existing_content_hash=None,
    message_timestamp=None,
):
    return {
        "message_id": message_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "existing_content_hash": existing_content_hash,
        "message_timestamp": message_timestamp or datetime(2026, 7, 20, 9, 30, tzinfo=ZoneInfo("Europe/Paris")),
    }


class _FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class _FakeConnection:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []

    def execute(self, query, params):
        self.executed.append((str(query), params))
        return _FakeResult(self.rows)


class _FakeBegin:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, traceback):
        return False


class _FakeEngine:
    def __init__(self):
        self.connections = []

    def begin(self):
        connection = _FakeConnection()
        self.connections.append(connection)
        return _FakeBegin(connection)


@pytest.mark.parametrize(
    "content,expected_hash",
    [
        ("Bonjour Autometa", "57b56d8af73a02eb788428fe62874f04502a072f83e86426524b210a1daa1342"),
        ("equipe data", "dccd4c9e112684b42ad1db2e0433f08beb0451b1417aabc636aff2566ee856f3"),
    ],
)
def test_content_hash_uses_stable_sha256(content, expected_hash):
    assert embeddings.content_hash(content) == expected_hash


def test_content_preview_uses_configured_length(monkeypatch):
    monkeypatch.setattr(embeddings.config, "EMBEDDING_CONTENT_PREVIEW_LENGTH", 4)

    assert embeddings.content_preview("abcdef") == "abcd"


def test_to_pgvector_formats_float_values():
    assert embeddings.to_pgvector([1, "2.5", 0]) == "[1.0,2.5,0.0]"


@pytest.mark.parametrize(
    "values,expected",
    [
        ([0, 0], [0.0, 0.0]),
        ([3, 4], [0.6, 0.8]),
    ],
)
def test_normalize_embedding(values, expected):
    assert embeddings.normalize_embedding(values) == expected


def test_resolve_time_window_without_days_ago():
    assert embeddings.resolve_time_window(None) == (None, None)


@pytest.mark.parametrize(
    "days_ago,expected_date",
    [
        (0, datetime(2026, 7, 22).date()),
        (2, datetime(2026, 7, 20).date()),
    ],
)
def test_resolve_time_window_uses_display_timezone_day_boundaries(monkeypatch, days_ago, expected_date):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 7, 22, 15, 45, tzinfo=tz)

    monkeypatch.setattr(embeddings.config, "DISPLAY_TIMEZONE", "Europe/Paris")
    monkeypatch.setattr(embeddings, "datetime", FrozenDatetime)

    start_at, end_at = embeddings.resolve_time_window(days_ago)

    expected_start = datetime.combine(expected_date, datetime.min.time(), tzinfo=ZoneInfo("Europe/Paris"))
    assert start_at == expected_start
    assert end_at == expected_start + embeddings.timedelta(days=1)


def test_load_candidate_messages_applies_limit_and_time_filter(monkeypatch):
    monkeypatch.setattr(embeddings.config, "EMBEDDING_MODEL", "test-model")
    rows = [{"message_id": 1}]
    connection = _FakeConnection(rows=rows)
    start_at = datetime(2026, 7, 20, tzinfo=ZoneInfo("Europe/Paris"))
    end_at = datetime(2026, 7, 21, tzinfo=ZoneInfo("Europe/Paris"))

    assert embeddings.load_candidate_messages(connection, limit=10, start_at=start_at, end_at=end_at) == rows

    query, params = connection.executed[0]
    assert "limit :limit" in query
    assert "m.timestamp >= :start_at" in query
    assert params == {
        "embedding_model": "test-model",
        "limit": 10,
        "start_at": start_at,
        "end_at": end_at,
    }


def test_prepare_messages_skips_rows_with_unchanged_content_hash():
    unchanged = _row(existing_content_hash=embeddings.content_hash("Bonjour Autometa"))

    assert embeddings.prepare_messages([unchanged]) == []


def test_prepare_messages_builds_embedding_payload(monkeypatch):
    monkeypatch.setattr(embeddings.config, "EMBEDDING_CONTENT_PREVIEW_LENGTH", 7)
    timestamp = datetime(2026, 7, 20, 9, 30, tzinfo=ZoneInfo("Europe/Paris"))
    row = _row(
        message_id=42,
        conversation_id=99,
        user_id="bob@example.com",
        role="assistant",
        content="Contenu assez long",
        message_timestamp=timestamp,
    )

    assert embeddings.prepare_messages([row]) == [
        {
            "message_id": 42,
            "conversation_id": 99,
            "user_id": "bob@example.com",
            "role": "assistant",
            "content": "Contenu assez long",
            "content_hash": embeddings.content_hash("Contenu assez long"),
            "content_length": 18,
            "content_preview": "Contenu",
            "message_timestamp": timestamp,
        }
    ]


def test_insert_embeddings_returns_zero_without_messages():
    connection = _FakeConnection()

    assert embeddings.insert_embeddings(connection, [], []) == 0
    assert connection.executed == []


def test_insert_embeddings_executes_idempotent_upsert(monkeypatch):
    monkeypatch.setattr(embeddings.config, "EMBEDDING_MODEL", "test-model")
    connection = _FakeConnection()
    message = embeddings.prepare_messages([_row(message_id=42, content="Contenu")])[0]

    assert embeddings.insert_embeddings(connection, [message], [[3, 4]]) == 1

    query, params = connection.executed[0]
    assert "on conflict (message_id, embedding_model)" in query
    assert "content_hash is distinct from excluded.content_hash" in query
    assert params == [
        {
            "message_id": 42,
            "conversation_id": 10,
            "user_id": "alice@example.com",
            "role": "user",
            "content_hash": embeddings.content_hash("Contenu"),
            "content_length": 7,
            "content_preview": "Contenu",
            "message_timestamp": message["message_timestamp"],
            "embedding_model": "test-model",
            "embedding": "[3.0,4.0]",
        }
    ]


def test_generate_embeddings_returns_when_no_message_to_embed(monkeypatch, mocker):
    engine = _FakeEngine()
    monkeypatch.setattr(embeddings, "get_engine", lambda: engine)
    monkeypatch.setattr(embeddings, "resolve_time_window", lambda days_ago: (None, None))
    monkeypatch.setattr(embeddings, "load_candidate_messages", lambda connection, limit, start_at, end_at: [])
    prepare = mocker.patch.object(embeddings, "prepare_messages", return_value=[])
    mocker.patch.object(embeddings.StaticModel, "from_pretrained")
    insert = mocker.patch.object(embeddings, "insert_embeddings")

    embeddings.generate_embeddings(limit=None, batch_size=2, days_ago=None)

    prepare.assert_called_once_with([])
    insert.assert_not_called()
    assert len(engine.connections) == 1


def test_generate_embeddings_batches_normalized_embeddings(monkeypatch, mocker):
    engine = _FakeEngine()
    rows = [_row(message_id=1, content="a"), _row(message_id=2, content="b"), _row(message_id=3, content="c")]
    messages = embeddings.prepare_messages(rows)
    inserted_batches = []

    class FakeModel:
        def encode(self, texts):
            return [[3, 4] for _ in texts]

    monkeypatch.setattr(embeddings, "get_engine", lambda: engine)
    monkeypatch.setattr(
        embeddings,
        "resolve_time_window",
        lambda days_ago: (
            datetime(2026, 7, 20, tzinfo=ZoneInfo("Europe/Paris")),
            datetime(2026, 7, 21, tzinfo=ZoneInfo("Europe/Paris")),
        ),
    )
    monkeypatch.setattr(embeddings, "load_candidate_messages", lambda connection, limit, start_at, end_at: rows)
    monkeypatch.setattr(embeddings, "prepare_messages", lambda loaded_rows: messages)
    mocker.patch.object(embeddings.StaticModel, "from_pretrained", return_value=FakeModel())

    def fake_insert(connection, batch, batch_embeddings):
        inserted_batches.append((batch, batch_embeddings))
        return len(batch)

    monkeypatch.setattr(embeddings, "insert_embeddings", fake_insert)

    embeddings.generate_embeddings(limit=3, batch_size=2, days_ago=2)

    assert [len(batch) for batch, _ in inserted_batches] == [2, 1]
    assert inserted_batches[0][1] == [[0.6, 0.8], [0.6, 0.8]]
    assert inserted_batches[1][1] == [[0.6, 0.8]]
    assert len(engine.connections) == 3


def test_main_parses_arguments_and_calls_generate_embeddings(monkeypatch, mocker):
    generate = mocker.patch.object(embeddings, "generate_embeddings")
    basic_config = mocker.patch.object(embeddings.logging, "basicConfig")
    monkeypatch.setattr(
        "sys.argv",
        ["generate-conversation-embeddings", "--limit", "5", "--batch-size", "2", "--days-ago", "1"],
    )

    embeddings.main()

    basic_config.assert_called_once()
    generate.assert_called_once_with(limit=5, batch_size=2, days_ago=1)
