"""Tests for cron delta upload optimization."""

import tempfile
from pathlib import Path

from web.cron import prepare_s3_workdir, upload_s3_results


def test_prepare_s3_workdir_computes_hashes(mocker):
    store = mocker.MagicMock()
    store.list_files.return_value = [
        {"path": "myapp/file1.txt"},
        {"path": "myapp/file2.txt"},
    ]
    store.download.side_effect = [b"content1", b"content2"]

    workdir, pre_hashes = prepare_s3_workdir(store, "myapp/", "myapp")

    assert len(pre_hashes) == 2
    assert "file1.txt" in pre_hashes
    assert pre_hashes["file1.txt"] == "7e55db001d319a94b0b713529a756623"


def test_upload_s3_results_skips_unchanged(mocker):
    store = mocker.MagicMock()
    workdir = Path(tempfile.mkdtemp())
    (workdir / "unchanged.txt").write_bytes(b"same content")
    (workdir / "changed.txt").write_bytes(b"new content")

    pre_hashes = {
        "unchanged.txt": "793953ee398d864ec40252df9554c3e6",
        "changed.txt": "old_hash",
    }

    upload_s3_results(store, "myapp/", "myapp", workdir, pre_hashes)

    assert store.upload.call_count == 1
    store.upload.assert_called_with("myapp/changed.txt", b"new content")


def test_upload_s3_results_uploads_new_files(mocker):
    store = mocker.MagicMock()
    workdir = Path(tempfile.mkdtemp())
    (workdir / "brand_new.txt").write_bytes(b"hello")

    upload_s3_results(store, "myapp/", "myapp", workdir, {})

    store.upload.assert_called_once_with("myapp/brand_new.txt", b"hello")
