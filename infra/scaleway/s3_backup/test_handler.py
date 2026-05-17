"""Tests for the s3_backup Scaleway Function handler."""

import json

import pytest
from botocore.exceptions import ClientError

import handler


def make_obj(key, etag="etag", size=10):
    return {"Key": key, "ETag": etag, "Size": size}


class FakeS3:
    """In-memory S3 double covering the calls snapshot() makes."""

    def __init__(self, source_objects, existing=None, fail_copy_keys=()):
        self.source_objects = list(source_objects)
        self.existing = dict(existing or {})
        self.fail_copy_keys = set(fail_copy_keys)
        self.copied = []
        self.put = {}

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return self

    def paginate(self, Bucket, Prefix=None, Delimiter=None):
        yield {"Contents": self.source_objects}

    def head_object(self, Bucket, Key):
        if Key in self.existing:
            return {"ETag": self.existing[Key]}
        raise ClientError({"Error": {"Code": "404"}}, "HeadObject")

    def copy_object(self, Bucket, Key, CopySource, MetadataDirective):
        if CopySource["Key"] in self.fail_copy_keys:
            raise ClientError({"Error": {"Code": "AccessDenied"}}, "CopyObject")
        self.copied.append(Key)

    def put_object(self, Bucket, Key, Body, ContentType):
        self.put[Key] = Body


def test_snapshot_copies_all_objects():
    client = FakeS3([make_obj("a"), make_obj("b"), make_obj("c")])
    result = handler.snapshot(client, "matometa", "matometa-backup", "2026-05-17")
    assert result["ok"] is True
    assert result["copied"] == 3
    assert result["objects"] == 3
    assert sorted(client.copied) == [
        "backup/2026-05-17/a",
        "backup/2026-05-17/b",
        "backup/2026-05-17/c",
    ]
    assert json.loads(client.put["backup/2026-05-17/_MANIFEST.json"])["ok"] is True


def test_snapshot_skips_objects_already_present_with_same_etag():
    client = FakeS3(
        [make_obj("a", etag="x"), make_obj("b", etag="y")],
        existing={"backup/2026-05-17/a": "x"},
    )
    result = handler.snapshot(client, "matometa", "matometa-backup", "2026-05-17")
    assert result["copied"] == 1
    assert result["skipped"] == 1
    assert client.copied == ["backup/2026-05-17/b"]


def test_snapshot_is_best_effort_and_flags_partial_failure():
    client = FakeS3([make_obj("a"), make_obj("bad"), make_obj("c")], fail_copy_keys={"bad"})
    result = handler.snapshot(client, "matometa", "matometa-backup", "2026-05-17")
    assert result["ok"] is False
    assert result["failed"] == 1
    assert result["copied"] == 2
    assert sorted(client.copied) == ["backup/2026-05-17/a", "backup/2026-05-17/c"]
    manifest = json.loads(client.put["backup/2026-05-17/_MANIFEST.json"])
    assert manifest["ok"] is False
    assert any("bad" in error for error in manifest["errors"])


def test_handle_raises_when_snapshot_incomplete(mocker):
    client = FakeS3([make_obj("a"), make_obj("bad")], fail_copy_keys={"bad"})
    mocker.patch.object(handler, "build_client", return_value=client)
    mocker.patch.object(handler.config, "SOURCE_BUCKET", "matometa")
    mocker.patch.object(handler.config, "BACKUP_BUCKET", "matometa-backup")
    mocker.patch.object(handler.config, "RETENTION_DAYS", 0)
    with pytest.raises(RuntimeError, match="incomplete"):
        handler.handle({}, None)
