import pytest


@pytest.fixture
def s3_env(monkeypatch, tmp_path):
    monkeypatch.setattr("web.config.USE_S3", True)
    interactive = tmp_path / "interactive"
    interactive.mkdir()
    monkeypatch.setattr("web.config.INTERACTIVE_DIR", interactive)
    return interactive


def test_restore_skips_existing_files(s3_env, mocker):
    (s3_env / "app1").mkdir()
    (s3_env / "app1" / "index.html").write_text("<html>local</html>")

    mocker.patch("web.s3.list_files", return_value=[{"path": "app1/index.html", "size": 100}])
    mock_download = mocker.patch("web.s3.download_file")

    from web.warmup import restore_interactive_from_s3

    restore_interactive_from_s3()

    mock_download.assert_not_called()
    assert (s3_env / "app1" / "index.html").read_text() == "<html>local</html>"


def test_restore_downloads_missing_files(s3_env, mocker):
    mocker.patch(
        "web.s3.list_files",
        return_value=[
            {"path": "app1/index.html", "size": 50},
            {"path": "app1/style.css", "size": 30},
        ],
    )
    mocker.patch(
        "web.s3.download_file",
        side_effect=lambda p: b"<html>from-s3</html>" if "html" in p else b"body{}",
    )

    from web.warmup import restore_interactive_from_s3

    restore_interactive_from_s3()

    assert (s3_env / "app1" / "index.html").read_bytes() == b"<html>from-s3</html>"
    assert (s3_env / "app1" / "style.css").read_bytes() == b"body{}"


def test_restore_skipped_when_s3_disabled(monkeypatch, mocker):
    monkeypatch.setattr("web.config.USE_S3", False)
    mock_list = mocker.patch("web.s3.list_files")

    from web.warmup import restore_interactive_from_s3

    restore_interactive_from_s3()

    mock_list.assert_not_called()


def test_restore_handles_failed_download(s3_env, mocker):
    mocker.patch("web.s3.list_files", return_value=[{"path": "app1/broken.html", "size": 10}])
    mocker.patch("web.s3.download_file", return_value=None)

    from web.warmup import restore_interactive_from_s3

    restore_interactive_from_s3()

    assert not (s3_env / "app1" / "broken.html").exists()
