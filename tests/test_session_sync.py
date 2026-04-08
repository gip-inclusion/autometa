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


def test_download_and_upload_roundtrip(monkeypatch, tmp_path):
    """Full roundtrip: upload a session, then download it to a different location."""
    uploaded = {}

    class FakeS3Client:
        def get_object(self, Bucket, Key):
            if Key not in uploaded:
                from botocore.exceptions import ClientError

                raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")

            class Body:
                def read(self):
                    return uploaded[Key]

            return {"Body": Body()}

        def put_object(self, Bucket, Key, Body, ContentType=None):
            uploaded[Key] = Body

        def get_paginator(self, operation):
            class FakePaginator:
                def paginate(self, Bucket, Prefix):
                    matching = [k for k in uploaded if k.startswith(Prefix)]
                    if matching:
                        yield {"Contents": [{"Key": k} for k in matching]}

            return FakePaginator()

    monkeypatch.setattr("web.session_sync.config.S3_BUCKET", "test-bucket")
    monkeypatch.setattr("web.session_sync.s3_client", FakeS3Client())

    # Point session dir to tmp_path
    monkeypatch.setattr("web.session_sync.get_session_dir", lambda: tmp_path)

    session_id = "test-session-001"
    session_file = tmp_path / f"{session_id}.jsonl"
    session_file.write_text('{"type":"message","content":"hello"}\n')

    # Also create a subagent file
    subagent_dir = tmp_path / session_id / "subagents"
    subagent_dir.mkdir(parents=True)
    (subagent_dir / "agent-abc.jsonl").write_text('{"type":"subagent"}\n')

    assert session_sync.upload_session(session_id) is True
    assert f"sessions/{session_id}.jsonl" in uploaded
    assert f"sessions/{session_id}/subagents/agent-abc.jsonl" in uploaded

    # Delete local files
    session_file.unlink()
    (subagent_dir / "agent-abc.jsonl").unlink()

    # Download
    assert session_sync.download_session(session_id) is True
    assert session_file.exists()
    assert session_file.read_text() == '{"type":"message","content":"hello"}\n'
    assert (subagent_dir / "agent-abc.jsonl").read_text() == '{"type":"subagent"}\n'


def test_download_nonexistent_session(monkeypatch, tmp_path):
    from botocore.exceptions import ClientError

    class FakeS3Client:
        def get_object(self, Bucket, Key):
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")

    monkeypatch.setattr("web.session_sync.config.S3_BUCKET", "test-bucket")
    monkeypatch.setattr("web.session_sync.s3_client", FakeS3Client())
    monkeypatch.setattr("web.session_sync.get_session_dir", lambda: tmp_path)

    assert session_sync.download_session("does-not-exist") is False
