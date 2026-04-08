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
