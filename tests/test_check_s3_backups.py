"""Cron check-s3-backups : le manifeste manquant doit distinguer « backup incomplet » de « aucun backup »."""

import importlib.util
import json
from pathlib import Path

import pytest
from botocore.exceptions import ClientError


def load_cron():
    path = Path(__file__).resolve().parent.parent / "cron" / "check-s3-backups" / "cron.py"
    spec = importlib.util.spec_from_file_location("check_s3_backups_cron", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fake_client(mocker, *, manifest, prefix_key_count):
    client = mocker.Mock()
    if manifest is None:
        client.get_object.side_effect = ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
    else:
        body = mocker.Mock()
        body.read.return_value = json.dumps(manifest).encode()
        client.get_object.return_value = {"Body": body}
    client.list_objects_v2.return_value = {"KeyCount": prefix_key_count}
    return client


def run_main(mocker, *, manifest, prefix_key_count):
    client = fake_client(mocker, manifest=manifest, prefix_key_count=prefix_key_count)
    mocker.patch("web.config.BACKUP_S3_BUCKET", "matometa-backup")
    mocker.patch("web.s3.make_client", return_value=client)
    load_cron().main()
    return client


def test_manifest_present_and_ok_does_not_raise(mocker):
    client = run_main(mocker, manifest={"ok": True, "objects": 10, "bytes": 100}, prefix_key_count=0)
    client.get_object.assert_called_once()
    client.list_objects_v2.assert_not_called()


def test_manifest_missing_but_data_present_reports_incomplete(mocker):
    with pytest.raises(RuntimeError, match="incomplet"):
        run_main(mocker, manifest=None, prefix_key_count=3)


def test_manifest_missing_and_no_data_reports_no_backup(mocker):
    with pytest.raises(RuntimeError, match="[Aa]ucun snapshot"):
        run_main(mocker, manifest=None, prefix_key_count=0)


def test_manifest_reports_failure_raises(mocker):
    with pytest.raises(RuntimeError, match="failure"):
        run_main(mocker, manifest={"ok": False}, prefix_key_count=5)
