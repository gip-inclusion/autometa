"""Tests for web/sync_to_s3.py — S3 sync helpers."""

import logging

import pytest


def test_sync_file_emits_upload_log(tmp_path, mocker, caplog):
    interactive = tmp_path / "interactive"
    interactive.mkdir()
    file_path = interactive / "app1" / "data.json"
    file_path.parent.mkdir()
    file_path.write_text('{"k":"v"}')

    mocker.patch("web.sync_to_s3.config.INTERACTIVE_DIR", interactive)
    mocker.patch("web.sync_to_s3.s3.interactive.upload", return_value=True)

    from web.sync_to_s3 import _sync_file

    with caplog.at_level(logging.INFO, logger="web.sync_to_s3"):
        _sync_file(file_path)

    matches = [r for r in caplog.records if r.message == "s3.upload"]
    assert len(matches) == 1
    record = matches[0]
    assert getattr(record, "s3.path") == "app1/data.json"
    assert getattr(record, "s3.size") == 9
    assert isinstance(getattr(record, "s3.duration"), float)


def test_sync_file_skips_log_on_upload_failure(tmp_path, mocker, caplog):
    interactive = tmp_path / "interactive"
    interactive.mkdir()
    file_path = interactive / "f.txt"
    file_path.write_text("x")

    mocker.patch("web.sync_to_s3.config.INTERACTIVE_DIR", interactive)
    mocker.patch("web.sync_to_s3.s3.interactive.upload", return_value=False)

    from web.sync_to_s3 import _sync_file

    with caplog.at_level(logging.INFO, logger="web.sync_to_s3"):
        _sync_file(file_path)

    assert not any(r.message == "s3.upload" for r in caplog.records)


@pytest.mark.parametrize(
    ("relative", "uploaded"),
    [
        ("app1/index.html", True),
        ("app1/index.html.tmp.72700.1782377517513", False),
        ("app1/app.js.tmp.10939.db92350fc2ce", False),
        ("app1/__pycache__/cron.cpython-314.pyc", False),
        ("__pycache__/cron.cpython-314.pyc", False),
    ],
)
def test_sync_file_skips_atomic_write_temporaries_and_bytecode(tmp_path, mocker, relative, uploaded):
    interactive = tmp_path / "interactive"
    file_path = interactive / relative
    file_path.parent.mkdir(parents=True)
    file_path.write_text("x")
    mocker.patch("web.sync_to_s3.config.INTERACTIVE_DIR", interactive)
    upload = mocker.patch("web.sync_to_s3.s3.interactive.upload", return_value=True)

    from web.sync_to_s3 import _sync_file

    _sync_file(file_path)

    assert upload.called is uploaded
