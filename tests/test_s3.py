"""Tests for web/s3.py — S3Store.head metadata lookup."""

import pytest
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError

from web import s3


def test_head_returns_size_and_etag(monkeypatch, mocker):
    monkeypatch.setattr("web.s3.config.S3_BUCKET", "test-bucket")
    mocker.patch.object(s3._client, "head_object", return_value={"ContentLength": 42, "ETag": '"abc123"'})
    assert s3.sessions.head("x.jsonl") == {"exists": True, "size": 42, "etag": "abc123"}


def test_head_returns_absent_on_404(monkeypatch, mocker):
    monkeypatch.setattr("web.s3.config.S3_BUCKET", "test-bucket")
    err = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
    mocker.patch.object(s3._client, "head_object", side_effect=err)
    assert s3.sessions.head("missing.jsonl") == {"exists": False}


@pytest.mark.parametrize(
    "exc",
    [
        ClientError({"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadObject"),
        BotoCoreError(),
    ],
)
def test_head_returns_none_when_unreachable(monkeypatch, mocker, exc):
    monkeypatch.setattr("web.s3.config.S3_BUCKET", "test-bucket")
    mocker.patch.object(s3._client, "head_object", side_effect=exc)
    assert s3.sessions.head("x.jsonl") is None


def test_download_returns_the_object_body(monkeypatch, mocker):
    monkeypatch.setattr("web.s3.config.S3_BUCKET", "test-bucket")
    mocker.patch.object(s3._client, "get_object", return_value={"Body": mocker.Mock(read=lambda: b"contenu")})
    assert s3.sessions.download("x.jsonl") == b"contenu"


@pytest.mark.parametrize(
    "exc",
    [
        ClientError({"Error": {"Code": "NoSuchKey", "Message": "Not Found"}}, "GetObject"),
        ClientError({"Error": {"Code": "403", "Message": "Forbidden"}}, "GetObject"),
        # Why: une coupure réseau tuait `run_all()` avant sa première tâche — tous les appelants héritaient du risque.
        EndpointConnectionError(endpoint_url="https://s3.example.org"),
        BotoCoreError(),
    ],
)
def test_download_returns_none_instead_of_raising(monkeypatch, mocker, exc):
    monkeypatch.setattr("web.s3.config.S3_BUCKET", "test-bucket")
    mocker.patch.object(s3._client, "get_object", side_effect=exc)
    assert s3.sessions.download("x.jsonl") is None
