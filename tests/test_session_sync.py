"""Tests for web/session_sync.py — S3 session file management."""

from web import session_sync


def test_get_session_path_contains_session_id():
    path = session_sync.get_session_path("abc-123")
    assert "abc-123.jsonl" in str(path)
    assert ".claude/projects/" in str(path)


def test_get_subagents_dir_contains_session_id():
    path = session_sync.get_subagents_dir("abc-123")
    assert "abc-123/subagents" in str(path)


def test_download_session_returns_false_without_s3(monkeypatch):
    monkeypatch.setattr("web.session_sync.config.S3_BUCKET", None)
    assert session_sync.download_session("any-id") is False


def test_upload_session_returns_false_without_s3(monkeypatch):
    monkeypatch.setattr("web.session_sync.config.S3_BUCKET", None)
    assert session_sync.upload_session("any-id") is False


def test_upload_session_returns_false_when_file_missing(monkeypatch):
    monkeypatch.setattr("web.session_sync.config.S3_BUCKET", "test-bucket")
    assert session_sync.upload_session("nonexistent-session-id") is False


def test_download_and_upload_roundtrip(monkeypatch, mocker, tmp_path):
    """Full roundtrip: upload a session, then download it to a different location."""
    stored = {}

    def mock_upload(path, content, content_type=None):
        stored[path] = content
        return True

    def mock_download(path):
        return stored.get(path)

    def mock_list_files(prefix=""):
        return [{"path": k, "size": len(v)} for k, v in stored.items() if k.startswith(prefix)]

    monkeypatch.setattr("web.session_sync.config.S3_BUCKET", "test-bucket")
    mocker.patch.object(session_sync.s3.sessions, "upload", side_effect=mock_upload)
    mocker.patch.object(session_sync.s3.sessions, "download", side_effect=mock_download)
    mocker.patch.object(session_sync.s3.sessions, "list_files", side_effect=mock_list_files)
    monkeypatch.setattr("web.session_sync.get_session_dir", lambda: tmp_path)

    session_id = "test-session-001"
    session_file = tmp_path / f"{session_id}.jsonl"
    session_file.write_text('{"type":"message","content":"hello"}\n')

    subagent_dir = tmp_path / session_id / "subagents"
    subagent_dir.mkdir(parents=True)
    (subagent_dir / "agent-abc.jsonl").write_text('{"type":"subagent"}\n')

    assert session_sync.upload_session(session_id) is True
    assert f"{session_id}.jsonl" in stored
    assert f"{session_id}/subagents/agent-abc.jsonl" in stored

    # Delete local files
    session_file.unlink()
    (subagent_dir / "agent-abc.jsonl").unlink()

    # Download
    assert session_sync.download_session(session_id) is True
    assert session_file.exists()
    assert session_file.read_text() == '{"type":"message","content":"hello"}\n'
    assert (subagent_dir / "agent-abc.jsonl").read_text() == '{"type":"subagent"}\n'


def test_download_nonexistent_session(monkeypatch, mocker, tmp_path):
    mocker.patch.object(session_sync.s3.sessions, "download", return_value=None)
    monkeypatch.setattr("web.session_sync.config.S3_BUCKET", "test-bucket")
    monkeypatch.setattr("web.session_sync.get_session_dir", lambda: tmp_path)

    assert session_sync.download_session("does-not-exist") is False


def test_copy_session_returns_false_without_s3(monkeypatch):
    monkeypatch.setattr("web.session_sync.config.S3_BUCKET", None)
    assert session_sync.copy_session("src", "dst") is False


def test_copy_session_returns_false_when_source_missing(monkeypatch, mocker):
    monkeypatch.setattr("web.session_sync.config.S3_BUCKET", "test-bucket")
    mocker.patch.object(session_sync.s3.sessions, "download", return_value=None)
    assert session_sync.copy_session("missing", "dst") is False


def test_copy_session_rewrites_session_id_and_copies_subagents(monkeypatch, mocker):
    src_id = "11111111-1111-1111-1111-111111111111"
    dst_id = "22222222-2222-2222-2222-222222222222"

    src_jsonl = (
        b'{"type":"user","sessionId":"' + src_id.encode() + b'","content":"hi"}\n'
        b'{"type":"assistant","sessionId":"' + src_id.encode() + b'","content":"hello"}\n'
    )
    subagent_jsonl = b'{"type":"subagent","sessionId":"' + src_id.encode() + b'"}\n'

    files = {
        f"{src_id}.jsonl": src_jsonl,
        f"{src_id}/subagents/agent-1.jsonl": subagent_jsonl,
    }
    uploaded = {}

    def mock_download(path):
        return files.get(path)

    def mock_upload(path, content, content_type=None):
        uploaded[path] = content
        return True

    def mock_list_files(prefix=""):
        return [{"path": k, "size": len(v)} for k, v in files.items() if k.startswith(prefix)]

    monkeypatch.setattr("web.session_sync.config.S3_BUCKET", "test-bucket")
    mocker.patch.object(session_sync.s3.sessions, "download", side_effect=mock_download)
    mocker.patch.object(session_sync.s3.sessions, "upload", side_effect=mock_upload)
    mocker.patch.object(session_sync.s3.sessions, "list_files", side_effect=mock_list_files)

    assert session_sync.copy_session(src_id, dst_id) is True

    assert f"{dst_id}.jsonl" in uploaded
    assert f"{dst_id}/subagents/agent-1.jsonl" in uploaded

    for content in uploaded.values():
        assert src_id.encode() not in content
        assert dst_id.encode() in content


def test_copy_session_keeps_going_when_jsonl_has_malformed_line(monkeypatch, mocker):
    src_id = "11111111-1111-1111-1111-111111111111"
    dst_id = "22222222-2222-2222-2222-222222222222"

    src_jsonl = (
        b'{"type":"user","sessionId":"' + src_id.encode() + b'","content":"hi"}\n'
        b"this is not json\n"
        b'{"type":"assistant","sessionId":"' + src_id.encode() + b'","content":"hello"}\n'
    )
    files = {f"{src_id}.jsonl": src_jsonl}
    uploaded = {}

    monkeypatch.setattr("web.session_sync.config.S3_BUCKET", "test-bucket")
    mocker.patch.object(session_sync.s3.sessions, "download", side_effect=lambda p: files.get(p))
    mocker.patch.object(
        session_sync.s3.sessions,
        "upload",
        side_effect=lambda p, c, content_type=None: uploaded.update({p: c}) or True,
    )
    mocker.patch.object(session_sync.s3.sessions, "list_files", return_value=[])

    assert session_sync.copy_session(src_id, dst_id) is True
    written = uploaded[f"{dst_id}.jsonl"]
    assert b"this is not json" in written
    assert src_id.encode() not in written.replace(b"this is not json", b"")
    assert dst_id.encode() in written


def test_copy_session_logs_warning_when_subagent_upload_fails(monkeypatch, mocker, caplog):
    src_id = "11111111-1111-1111-1111-111111111111"
    dst_id = "22222222-2222-2222-2222-222222222222"

    files = {
        f"{src_id}.jsonl": b'{"type":"user","sessionId":"' + src_id.encode() + b'"}\n',
        f"{src_id}/subagents/agent-1.jsonl": b'{"type":"subagent","sessionId":"' + src_id.encode() + b'"}\n',
    }

    def mock_upload(path, content, content_type=None):
        return not path.endswith("subagents/agent-1.jsonl")

    monkeypatch.setattr("web.session_sync.config.S3_BUCKET", "test-bucket")
    mocker.patch.object(session_sync.s3.sessions, "download", side_effect=lambda p: files.get(p))
    mocker.patch.object(session_sync.s3.sessions, "upload", side_effect=mock_upload)
    mocker.patch.object(
        session_sync.s3.sessions,
        "list_files",
        side_effect=lambda prefix="": [{"path": k, "size": len(v)} for k, v in files.items() if k.startswith(prefix)],
    )

    with caplog.at_level("WARNING", logger="web.session_sync"):
        assert session_sync.copy_session(src_id, dst_id) is True
    assert any("Failed to copy subagent file" in r.message for r in caplog.records)
