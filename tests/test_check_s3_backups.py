"""Tests for the check-s3-backups cron: it is the only alert that a backup pass completed."""

import datetime
import importlib.util
import json
import logging
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

_CRON_PATH = Path(__file__).parent.parent / "cron" / "check-s3-backups" / "cron.py"
_spec = importlib.util.spec_from_file_location("check_s3_backups", _CRON_PATH)
check_s3_backups = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_s3_backups)

MANIFEST = {"ok": True, "objects": 14385, "bytes": 5480696576, "target": "matometa-backup/mirror/"}


class FakeS3:
    def __init__(self, manifest=None, error_code=None):
        self.manifest = manifest
        self.error_code = error_code
        self.requested = []

    def get_object(self, Bucket, Key):
        self.requested.append(Key)
        if self.error_code:
            raise ClientError({"Error": {"Code": self.error_code}}, "GetObject")
        return {"Body": FakeBody(json.dumps(self.manifest).encode())}


class FakeBody:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return self.payload


def run_with(mocker, client):
    mocker.patch.object(check_s3_backups.config, "BACKUP_S3_BUCKET", "matometa-backup")
    mocker.patch.object(check_s3_backups.s3_module, "make_client", return_value=client)
    check_s3_backups.main()


def test_success_log_names_the_mirror_once(mocker, caplog):
    # Why: the manifest's target already carries the bucket — logging both produced s3://bucket/bucket/...
    caplog.set_level(logging.INFO)
    run_with(mocker, FakeS3(manifest=MANIFEST))
    assert "s3://matometa-backup/mirror/" in caplog.text
    assert "matometa-backup/matometa-backup" not in caplog.text


def test_reads_todays_manifest_from_the_manifests_prefix(mocker):
    client = FakeS3(manifest=MANIFEST)
    run_with(mocker, client)
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    assert client.requested == [f"manifests/{today}.json"]


@pytest.mark.parametrize(
    ("client", "expected"),
    [
        (FakeS3(error_code="NoSuchKey"), "missing"),
        (FakeS3(error_code="404"), "missing"),
        (FakeS3(manifest={"ok": False, "failed": 3}), "failure"),
    ],
)
def test_raises_when_no_pass_completed_today(mocker, client, expected):
    with pytest.raises(RuntimeError, match=expected):
        run_with(mocker, client)


def test_propagates_unexpected_s3_errors(mocker):
    # Why: an AccessDenied must not be reported as "no backup today" — it is a different incident.
    with pytest.raises(ClientError):
        run_with(mocker, FakeS3(error_code="AccessDenied"))


def test_skips_when_no_backup_bucket_is_configured(mocker):
    mocker.patch.object(check_s3_backups.config, "BACKUP_S3_BUCKET", None)
    make_client = mocker.patch.object(check_s3_backups.s3_module, "make_client")
    check_s3_backups.main()
    make_client.assert_not_called()
