"""Tests for the s3_backup Scaleway Function handler."""

import json

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

import handler

SOURCE = "matometa"
TARGET = "matometa-backup"


class FakeS3:
    """In-memory S3 double. Exposes no head_object: a pass must diff by listing, not per-object probes."""

    def __init__(
        self,
        source,
        mirrored=(),
        other_target=(),
        fail_copy_keys=(),
        fail_delete_keys=(),
        copy_error=None,
        versioning="Enabled",
    ):
        self.objects = {
            SOURCE: {key: (etag, 10) for key, etag in dict(source).items()},
            TARGET: {f"mirror/{key}": (etag, 10) for key, etag in dict(mirrored).items()}
            | {key: (etag, 10) for key, etag in dict(other_target).items()},
        }
        self.fail_copy_keys = set(fail_copy_keys)
        self.fail_delete_keys = set(fail_delete_keys)
        self.copy_error = copy_error or ClientError({"Error": {"Code": "AccessDenied"}}, "CopyObject")
        self.versioning = versioning
        self.copied = []
        self.deleted = []
        self.put = {}

    def get_bucket_versioning(self, Bucket):
        return {"Status": self.versioning} if self.versioning else {}

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return self

    def paginate(self, Bucket, Prefix=""):
        contents = [
            {"Key": key, "ETag": etag, "Size": size}
            for key, (etag, size) in sorted(self.objects[Bucket].items())
            if key.startswith(Prefix)
        ]
        yield {"Contents": contents[:1]}
        yield {"Contents": contents[1:]}

    def copy_object(self, Bucket, Key, CopySource, MetadataDirective):
        if CopySource["Key"] in self.fail_copy_keys:
            raise self.copy_error
        self.objects[Bucket][Key] = self.objects[CopySource["Bucket"]][CopySource["Key"]]
        self.copied.append(Key)

    def delete_object(self, Bucket, Key, **kwargs):
        if Key in self.fail_delete_keys:
            raise ClientError({"Error": {"Code": "AccessDenied"}}, "DeleteObject")
        self.deleted.append((Key, kwargs))
        self.objects[Bucket].pop(Key, None)

    def put_object(self, Bucket, Key, Body, ContentType):
        self.put[Key] = Body


def test_mirror_copies_objects_absent_from_the_mirror():
    client = FakeS3({"a": "1", "b": "2"}, mirrored={"a": "1"})
    result = handler.mirror(client, SOURCE, TARGET, "2026-08-12")
    assert result["ok"] is True
    assert result["copied"] == 1
    assert result["unchanged"] == 1
    assert result["objects"] == 2
    assert client.copied == ["mirror/b"]


@pytest.mark.parametrize(
    ("mirrored_etag", "expected_copies"),
    [("1", []), ("stale", ["mirror/a"])],
)
def test_mirror_recopies_an_object_only_when_its_etag_differs(mirrored_etag, expected_copies):
    client = FakeS3({"a": "1"}, mirrored={"a": mirrored_etag})
    handler.mirror(client, SOURCE, TARGET, "2026-08-12")
    assert client.copied == expected_copies


def test_mirror_deletes_keys_dropped_from_the_source_without_naming_a_version():
    client = FakeS3({"a": "1"}, mirrored={"a": "1", "gone": "9"})
    result = handler.mirror(client, SOURCE, TARGET, "2026-08-12")
    assert result["deleted"] == 1
    # Why: a version-unaware delete leaves a delete marker, so the backup keeps the removed object's history.
    assert client.deleted == [("mirror/gone", {})]


def test_mirror_leaves_everything_outside_the_mirror_prefix_alone():
    # Why: legacy dated snapshots and the manifests live in the same bucket. If the pass ever compared
    # them against the source they would all be deleted, and the manifest would still report success.
    client = FakeS3(
        {"a": "1"},
        mirrored={"a": "1"},
        other_target={"backup/2026-05-01/a": "old", "manifests/2026-08-11.json": "m"},
    )
    result = handler.mirror(client, SOURCE, TARGET, "2026-08-12")
    assert client.deleted == []
    assert result["objects"] == 1
    assert set(client.objects[TARGET]) >= {"backup/2026-05-01/a", "manifests/2026-08-11.json"}


@pytest.mark.parametrize(
    ("versioning", "expected"),
    [(None, "disabled"), ("Suspended", "Suspended")],
)
def test_mirror_refuses_to_run_when_the_target_keeps_no_history(versioning, expected):
    # Why: without versioning, mirroring a deletion destroys the only copy and the manifest would
    # still say ok — the backup would silently stop being a backup.
    client = FakeS3({"a": "1"}, mirrored={"gone": "9"}, versioning=versioning)
    with pytest.raises(RuntimeError, match=expected):
        handler.mirror(client, SOURCE, TARGET, "2026-08-12")
    assert client.copied == []
    assert client.deleted == []
    assert client.put == {}


def test_mirror_writes_a_dated_manifest_outside_the_mirror_prefix():
    client = FakeS3({"a": "1"})
    handler.mirror(client, SOURCE, TARGET, "2026-08-12")
    manifest = json.loads(client.put["manifests/2026-08-12.json"])
    assert manifest["ok"] is True
    assert manifest["objects"] == 1
    assert manifest["bytes"] == 10
    assert manifest["target"] == f"{TARGET}/mirror/"


def test_mirror_counts_objects_whose_etag_cannot_confirm_a_copy():
    # Why: a multipart ETag is not a plain MD5, so the copy's ETag never matches and the object is
    # re-copied every pass. Counted in the manifest so that churn is visible instead of silent.
    client = FakeS3({"single": "1", "multi": "abc-3"})
    result = handler.mirror(client, SOURCE, TARGET, "2026-08-12")
    assert result["multipart"] == 1


@pytest.mark.parametrize(
    "copy_error",
    [
        ClientError({"Error": {"Code": "AccessDenied"}}, "CopyObject"),
        # Why: a transient network error is a BotoCoreError, not a ClientError — it must be
        # counted as a failed object rather than crash the pass before the manifest is written.
        EndpointConnectionError(endpoint_url="https://s3.fr-par.scw.cloud"),
    ],
)
def test_mirror_is_best_effort_and_flags_partial_failure(copy_error):
    client = FakeS3({"a": "1", "bad": "2", "c": "3"}, fail_copy_keys={"bad"}, copy_error=copy_error)
    result = handler.mirror(client, SOURCE, TARGET, "2026-08-12")
    assert result["ok"] is False
    assert result["failed"] == 1
    assert result["copied"] == 2
    manifest = json.loads(client.put["manifests/2026-08-12.json"])
    assert manifest["ok"] is False
    assert any("bad" in error for error in manifest["errors"])


def test_mirror_counts_a_failed_deletion_without_counting_it_as_deleted():
    client = FakeS3({"a": "1"}, mirrored={"a": "1", "gone": "9", "also-gone": "8"}, fail_delete_keys={"mirror/gone"})
    result = handler.mirror(client, SOURCE, TARGET, "2026-08-12")
    assert result["ok"] is False
    assert result["failed"] == 1
    assert result["deleted"] == 1
    assert result["copied"] == 0
    assert any("delete gone" in error for error in json.loads(client.put["manifests/2026-08-12.json"])["errors"])


def test_handle_raises_when_the_pass_is_incomplete(mocker):
    client = FakeS3({"a": "1", "bad": "2"}, fail_copy_keys={"bad"})
    mocker.patch.object(handler, "build_client", return_value=client)
    mocker.patch.object(handler.config, "SOURCE_BUCKET", SOURCE)
    mocker.patch.object(handler.config, "BACKUP_BUCKET", TARGET)
    with pytest.raises(RuntimeError, match="incomplete"):
        handler.handle({}, None)
