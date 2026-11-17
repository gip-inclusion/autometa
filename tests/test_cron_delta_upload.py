"""Tests for cron delta upload optimization."""

import tempfile
import threading
import time
from pathlib import Path

import pytest

from web import cron
from web.cron import prepare_s3_workdir, upload_s3_results


def test_prepare_s3_workdir_computes_hashes(mocker):
    store = mocker.MagicMock()
    store.list_files.return_value = [
        {"path": "myapp/file1.txt"},
        {"path": "myapp/file2.txt"},
    ]
    contents = {"myapp/file1.txt": b"content1", "myapp/file2.txt": b"content2"}
    store.download.side_effect = contents.get

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


def test_prepare_s3_workdir_removes_its_tempdir_when_a_download_fails(mocker):
    store = mocker.MagicMock()
    store.list_files.return_value = [{"path": "slug/cron.py"}]
    store.download.side_effect = RuntimeError("S3 down")
    mkdtemp = mocker.spy(tempfile, "mkdtemp")

    with pytest.raises(RuntimeError):
        prepare_s3_workdir(store, "slug/", "slug")

    assert not Path(mkdtemp.spy_return).exists()


def in_pairs(result):
    """Chaque appel attend un second appel simultané : exécutés un par un, la barrière casse."""
    barrier = threading.Barrier(2, timeout=5)

    def call(*args):
        barrier.wait()
        return result

    return call


def test_prepare_s3_workdir_downloads_in_parallel(mocker):
    store = mocker.MagicMock()
    store.list_files.return_value = [{"path": f"myapp/f{i}.txt"} for i in range(4)]
    store.download.side_effect = in_pairs(b"x")

    workdir, pre_hashes = prepare_s3_workdir(store, "myapp/", "myapp")

    assert sorted(pre_hashes) == [f"f{i}.txt" for i in range(4)]
    assert (workdir / "f3.txt").read_bytes() == b"x"


def test_upload_s3_results_uploads_in_parallel(mocker, tmp_path):
    store = mocker.MagicMock()
    store.upload.side_effect = in_pairs(True)
    for i in range(4):
        (tmp_path / f"f{i}.txt").write_bytes(b"new")

    upload_s3_results(store, "myapp/", "myapp", tmp_path, {})

    assert sorted(call.args[0] for call in store.upload.call_args_list) == [f"myapp/f{i}.txt" for i in range(4)]


def test_the_facade_audit_reads_the_scripts_in_parallel(mocker):
    mocker.patch.object(cron, "read_cron_script", side_effect=in_pairs("from web import db\n"))
    tasks = [{"slug": f"tdb{i}", "source": "s3", "cron_path": f"tdb{i}/cron.py"} for i in range(4)]

    assert sorted(cron.facade_violations_by_slug(tasks)) == [f"tdb{i}" for i in range(4)]


def test_parallel_s3_calls_stay_within_the_pool_bound(mocker):
    active = peak = 0
    lock = threading.Lock()

    def download(path):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        return b"x"

    store = mocker.MagicMock()
    store.list_files.return_value = [{"path": f"myapp/f{i}.txt"} for i in range(40)]
    store.download.side_effect = download

    prepare_s3_workdir(store, "myapp/", "myapp")

    assert 1 < peak <= cron.S3_WORKERS


def test_a_downloaded_file_leaves_memory_before_the_next_download(mocker):
    # Why: tout garder en mémoire jusqu'à la fin laissait 470 Mo au parent après une publication de
    # 236 Mo (mesure glibc) ; la tâche suivante du lot le faisait tuer (OOM).
    mocker.patch.object(cron, "S3_WORKERS", 1)
    on_disk_at_each_download = []
    workdirs = mocker.spy(tempfile, "mkdtemp")

    def download(path):
        on_disk_at_each_download.append(sorted(p.name for p in Path(workdirs.spy_return).iterdir()))
        return b"x"

    store = mocker.MagicMock()
    store.list_files.return_value = [{"path": f"myapp/f{i}.txt"} for i in range(3)]
    store.download.side_effect = download

    prepare_s3_workdir(store, "myapp/", "myapp")

    assert on_disk_at_each_download == [[], ["f0.txt"], ["f0.txt", "f1.txt"]]


def test_a_file_is_only_read_once_the_previous_one_is_uploaded(mocker, tmp_path):
    mocker.patch.object(cron, "S3_WORKERS", 1)
    read = mocker.spy(Path, "read_bytes")
    reads_at_each_upload = []
    store = mocker.MagicMock()
    store.upload.side_effect = lambda *_: reads_at_each_upload.append(read.call_count)
    for i in range(3):
        (tmp_path / f"f{i}.txt").write_bytes(b"new")

    upload_s3_results(store, "myapp/", "myapp", tmp_path, {})

    assert reads_at_each_upload == [1, 2, 3]


def test_a_failed_upload_still_surfaces(mocker, tmp_path):
    store = mocker.MagicMock()
    store.upload.side_effect = RuntimeError("S3 down")
    (tmp_path / "f.txt").write_bytes(b"new")

    with pytest.raises(RuntimeError):
        upload_s3_results(store, "myapp/", "myapp", tmp_path, {})


def test_prepare_s3_workdir_refuses_a_key_that_escapes_the_workdir(mocker):
    store = mocker.MagicMock()
    store.list_files.return_value = [{"path": "myapp/ok.txt"}, {"path": "myapp//etc/passwd"}]
    store.download.return_value = b"x"

    workdir, pre_hashes = prepare_s3_workdir(store, "myapp/", "myapp")

    assert sorted(pre_hashes) == ["ok.txt"]
    assert sorted(p.name for p in workdir.iterdir()) == ["ok.txt"]
