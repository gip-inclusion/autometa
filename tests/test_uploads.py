"""Tests for file upload functionality.

These tests focus on the core upload logic without requiring the full
Flask application to be initialized. This allows testing in environments
where not all dependencies are installed.
"""

import hashlib
import io
import os
import tempfile
from pathlib import Path

import pytest

# Set up test environment BEFORE any imports
_tmp_dir = tempfile.mkdtemp()
os.environ["DATA_DIR"] = _tmp_dir  # noqa: TID251

# Now we can safely import
from web import config, s3
from web.database import ConversationStore, UploadedFile
from web.uploads import (
    BLOCKED_EXTENSIONS,
    TEXT_EXTENSIONS,
    BlockedFileTypeError,
    FileTooLargeError,
    compute_sha256,
    delete_file,
    format_file_for_context,
    generate_stored_filename,
    is_text_file,
    restore_conversation_files,
    sanitize_filename,
    upload_file,
)

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

# Configure for testing
config.DATA_DIR = Path(_tmp_dir)
config.UPLOADS_DIR = Path(_tmp_dir) / "uploads"
config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
config.MAX_UPLOAD_SIZE = 10 * 1024 * 1024
config.TEXT_FILE_INLINE_LIMIT = 1024

store = ConversationStore()


def make_conversation():
    return store.create_conversation(user_id="test@example.com").id


@pytest.fixture
def setup_db(tmp_path, monkeypatch):
    """Tmp upload dirs, stub ClamAV, one DB transaction rolled back per test."""
    import web.config as config
    from web.db import test_transaction

    monkeypatch.setattr(
        "web.uploads.scan_with_clamav",
        lambda _path: (False, None),
    )
    monkeypatch.setattr(
        "web.uploads.upload_to_s3",
        lambda *_args, **_kw: True,
    )

    with test_transaction():
        config.DATA_DIR = tmp_path
        config.UPLOADS_DIR = tmp_path / "uploads"
        config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        config.MAX_UPLOAD_SIZE = 10 * 1024 * 1024
        config.TEXT_FILE_INLINE_LIMIT = 1024

        yield tmp_path


def test_compute_sha256_correct_hash():
    content = b"Hello, World!"
    expected = hashlib.sha256(content).hexdigest()
    assert compute_sha256(content) == expected


def test_compute_sha256_empty_content():
    content = b""
    expected = hashlib.sha256(content).hexdigest()
    assert compute_sha256(content) == expected


def test_compute_sha256_deterministic():
    content = b"test content"
    hash1 = compute_sha256(content)
    hash2 = compute_sha256(content)
    assert hash1 == hash2


def test_is_text_file_text_extension_is_detected():
    for ext in [".txt", ".md", ".csv", ".json", ".py", ".ts"]:
        assert is_text_file(f"file{ext}", None, b"") is True


def test_is_text_file_binary_extension_is_not_text():
    assert is_text_file("image.png", "image/png", b"\x89PNG") is False
    # PDF with binary content is detected as binary
    assert is_text_file("doc.pdf", "application/pdf", b"\x00\x01\x02") is False


def test_is_text_file_text_mime_type_is_detected():
    assert is_text_file("file", "text/plain", b"") is True
    assert is_text_file("file", "application/json", b"") is True


def test_is_text_file_content_based_detection():
    text_content = b"This is plain text content with mostly printable characters."
    assert is_text_file("unknown", None, text_content) is True


def test_is_text_file_binary_content_not_detected_as_text():
    binary_content = bytes(range(256))  # Contains non-printable bytes
    assert is_text_file("unknown", None, binary_content) is False


def test_sanitize_filename_removes_path_components():
    """Path traversal attempts are blocked."""
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("/etc/passwd") == "passwd"
    # On Unix, backslashes are treated as regular characters (sanitized to underscores)
    result = sanitize_filename("..\\..\\windows\\system32\\config")
    assert "passwd" not in result.lower()  # Not confused with Unix paths
    assert "_" in result  # Backslashes replaced


def test_sanitize_filename_removes_problematic_chars():
    """Problematic characters are replaced."""
    result = sanitize_filename('file<>:"|?*name.txt')
    assert result.endswith(".txt")
    assert "<" not in result
    assert ">" not in result
    assert ":" not in result
    assert '"' not in result
    assert "|" not in result
    assert "?" not in result
    assert "*" not in result


def test_sanitize_filename_limits_length():
    """Long filenames are truncated."""
    long_name = "a" * 300 + ".txt"
    result = sanitize_filename(long_name)
    assert len(result) <= 200
    assert result.endswith(".txt")


def test_sanitize_filename_empty_filename():
    """Empty filename returns 'unnamed'."""
    assert sanitize_filename("") == "unnamed"
    # Note: whitespace-only filenames are not currently treated as empty
    # This is acceptable since os.path.basename("   ") returns "   "


def test_sanitize_filename_preserves_valid_filename():
    """Valid filenames are preserved."""
    assert sanitize_filename("my_file-2024.csv") == "my_file-2024.csv"


def test_generate_stored_filename_preserves_extension():
    """File extension is preserved."""
    result = generate_stored_filename("document.pdf")
    assert result.endswith(".pdf")


def test_generate_stored_filename_includes_original_stem():
    """Original filename stem is included."""
    result = generate_stored_filename("my_report.csv")
    assert "my_report" in result


def test_generate_stored_filename_generates_unique_names():
    """Generated names are unique."""
    name1 = generate_stored_filename("file.txt")
    name2 = generate_stored_filename("file.txt")
    assert name1 != name2


def test_generate_stored_filename_handles_no_extension():
    result = generate_stored_filename("Makefile")
    assert "Makefile" in result


@pytest.mark.usefixtures("setup_db")
def test_upload_file_text_file():
    content = b"Hello, World!"
    file_obj = io.BytesIO(content)

    result, text_content = upload_file(
        file_obj=file_obj,
        filename="hello.txt",
        conversation_id=make_conversation(),
        user_id="test@example.com",
    )

    assert result is not None
    assert result.original_filename == "hello.txt"
    assert result.file_size == len(content)
    assert result.is_text is True
    assert result.sha256_hash == compute_sha256(content)
    assert text_content == "Hello, World!"


@pytest.mark.usefixtures("setup_db")
def test_upload_file_binary_file():
    content = bytes(range(256)) * 100  # Binary content
    file_obj = io.BytesIO(content)

    result, text_content = upload_file(
        file_obj=file_obj,
        filename="data.bin",
        conversation_id=make_conversation(),
        user_id="test@example.com",
    )

    assert result is not None
    assert result.is_text is False
    assert text_content is None


@pytest.mark.usefixtures("setup_db")
def test_upload_file_large_text_file_no_inline():
    # Make content larger than TEXT_FILE_INLINE_LIMIT (1KB in tests)
    content = b"x" * 2000
    file_obj = io.BytesIO(content)

    result, text_content = upload_file(
        file_obj=file_obj,
        filename="large.txt",
        conversation_id=make_conversation(),
        user_id="test@example.com",
    )

    assert result is not None
    assert result.is_text is True
    assert text_content is None  # Too large to inline


@pytest.mark.usefixtures("setup_db")
def test_upload_file_too_large_rejected():
    import web.config as config

    config.MAX_UPLOAD_SIZE = 100  # Very small for testing

    content = b"x" * 200
    file_obj = io.BytesIO(content)

    with pytest.raises(FileTooLargeError):
        upload_file(
            file_obj=file_obj,
            filename="big.txt",
            conversation_id=make_conversation(),
            user_id="test@example.com",
        )


@pytest.mark.usefixtures("setup_db")
def test_upload_file_blocked_extension_rejected():
    content = b"MZ"  # PE header start
    file_obj = io.BytesIO(content)

    with pytest.raises(BlockedFileTypeError):
        upload_file(
            file_obj=file_obj,
            filename="malware.exe",
            conversation_id=make_conversation(),
            user_id="test@example.com",
        )


@pytest.mark.usefixtures("setup_db")
def test_upload_file_duplicate_detection():
    """Duplicate files are detected by hash."""
    content = b"same content"
    file_obj1 = io.BytesIO(content)
    file_obj2 = io.BytesIO(content)
    conversation_id = make_conversation()

    result1, _ = upload_file(
        file_obj=file_obj1,
        filename="file1.txt",
        conversation_id=conversation_id,
        user_id="user1@example.com",
    )

    result2, _ = upload_file(
        file_obj=file_obj2,
        filename="file2.txt",  # Different name
        conversation_id=conversation_id,
        user_id="user1@example.com",
    )

    # Both should have same hash and stored filename
    assert result1.sha256_hash == result2.sha256_hash
    assert result1.stored_filename == result2.stored_filename
    # But different IDs and original filenames
    assert result1.id != result2.id
    assert result1.original_filename != result2.original_filename


@pytest.mark.usefixtures("setup_db")
def test_upload_file_permissions_readonly():
    """Uploaded files are set to read-only."""
    content = b"test"
    file_obj = io.BytesIO(content)

    result, _ = upload_file(
        file_obj=file_obj,
        filename="test.txt",
        conversation_id=make_conversation(),
        user_id="test@example.com",
    )

    path = Path(result.storage_path)
    assert path.exists()

    # Check file is not writable (mode should be 0o444)
    mode = path.stat().st_mode
    assert not (mode & 0o222)  # No write bits


def test_format_file_for_context_with_text_content():
    uploaded_file = UploadedFile(
        original_filename="notes.txt",
        storage_path="/data/uploads/notes.txt",
        file_size=100,
        mime_type="text/plain",
        sha256_hash="abc123",
        is_text=True,
    )

    result = format_file_for_context(uploaded_file, "Hello, World!")

    assert "[Uploaded file: notes.txt]" in result
    assert "Size: 100 bytes" in result
    assert "Hello, World!" in result
    assert "```" in result  # Code block markers


def test_format_file_for_context_without_text_content():
    uploaded_file = UploadedFile(
        original_filename="image.png",
        storage_path="/data/uploads/image.png",
        file_size=50000,
        mime_type="image/png",
        sha256_hash="abc123",
        is_text=False,
    )

    result = format_file_for_context(uploaded_file, None)

    assert "[Uploaded file: image.png]" in result
    assert "Path: /data/uploads/image.png" in result
    assert "Binary file" in result


def test_format_file_for_context_large_text_file():
    uploaded_file = UploadedFile(
        original_filename="large.txt",
        storage_path="/data/uploads/large.txt",
        file_size=100000,
        mime_type="text/plain",
        sha256_hash="abc123",
        is_text=True,
    )

    result = format_file_for_context(uploaded_file, None)

    assert "too large to include inline" in result
    assert "Read tool" in result


def test_blocked_extensions_executable_extensions_blocked():
    assert ".exe" in BLOCKED_EXTENSIONS
    assert ".dll" in BLOCKED_EXTENSIONS
    assert ".bat" in BLOCKED_EXTENSIONS
    assert ".com" in BLOCKED_EXTENSIONS


def test_blocked_extensions_script_extensions_blocked():
    assert ".vbs" in BLOCKED_EXTENSIONS
    assert ".ps1" in BLOCKED_EXTENSIONS
    assert ".jar" in BLOCKED_EXTENSIONS


def test_text_extensions_common_text_extensions_included():
    assert ".txt" in TEXT_EXTENSIONS
    assert ".md" in TEXT_EXTENSIONS
    assert ".json" in TEXT_EXTENSIONS
    assert ".csv" in TEXT_EXTENSIONS


def test_text_extensions_programming_extensions_included():
    assert ".py" in TEXT_EXTENSIONS
    assert ".ts" in TEXT_EXTENSIONS
    assert ".java" in TEXT_EXTENSIONS
    assert ".go" in TEXT_EXTENSIONS


@pytest.mark.usefixtures("setup_db")
def test_database_integration_file_record_stored():
    """Uploaded files are stored in database."""
    content = b"test content"
    file_obj = io.BytesIO(content)

    result, _ = upload_file(
        file_obj=file_obj,
        filename="test.txt",
        conversation_id=make_conversation(),
        user_id="test@example.com",
    )

    # Retrieve from database
    retrieved = store.get_uploaded_file(result.id)
    assert retrieved is not None
    assert retrieved.original_filename == "test.txt"
    assert retrieved.user_id == "test@example.com"


@pytest.mark.usefixtures("setup_db")
def test_database_integration_files_by_hash():
    content = b"unique content"
    file_obj = io.BytesIO(content)

    result, _ = upload_file(
        file_obj=file_obj,
        filename="test.txt",
        conversation_id=make_conversation(),
        user_id="test@example.com",
    )

    # Find by hash
    found = store.get_uploaded_file_by_hash(result.sha256_hash, result.conversation_id)
    assert found is not None
    assert found.id == result.id


@pytest.mark.usefixtures("setup_db")
def test_delete_file_keeps_file_when_still_referenced(mocker):
    conv = store.create_conversation(user_id="u@example.com")
    shared = "dedup-shared.bin"
    f1 = store.add_uploaded_file(conv.id, "u@example.com", "a.bin", shared, "/tmp/x", 1, "h-shared")
    store.add_uploaded_file(conv.id, "u@example.com", "b.bin", shared, "/tmp/x", 1, "h-shared")

    delete_record = mocker.patch("web.uploads.store.delete_uploaded_file")
    unlink = mocker.patch("web.uploads.Path.unlink")

    assert delete_file(f1) is True
    delete_record.assert_called_once_with(f1.id)
    unlink.assert_not_called()


@pytest.mark.usefixtures("setup_db")
def test_database_integration_conversation_files():
    # Create a conversation first
    conv = store.create_conversation(user_id="test@example.com")

    # Upload files to conversation
    for i in range(3):
        content = f"file {i}".encode()
        file_obj = io.BytesIO(content)
        upload_file(
            file_obj=file_obj,
            filename=f"file{i}.txt",
            conversation_id=conv.id,
            user_id="test@example.com",
        )

    # List files
    files = store.get_conversation_files(conv.id)
    assert len(files) == 3


@pytest.mark.usefixtures("setup_db")
def test_an_upload_is_stored_in_its_conversation_folder():
    conversation_id = make_conversation()

    result, _ = upload_file(io.BytesIO(b"x"), "notes.txt", conversation_id=conversation_id)

    assert Path(result.storage_path).parent == config.UPLOADS_DIR / conversation_id
    assert result.stored_filename.startswith(f"{conversation_id}/")


@pytest.mark.usefixtures("setup_db")
def test_the_same_file_in_another_conversation_is_stored_again_in_its_folder():
    first, _ = upload_file(io.BytesIO(b"same"), "a.txt", conversation_id=make_conversation())
    second, _ = upload_file(io.BytesIO(b"same"), "a.txt", conversation_id=make_conversation())

    assert first.storage_path != second.storage_path
    assert Path(second.storage_path).exists()


def test_uploads_are_kept_out_of_the_served_interactive_prefix():
    assert not s3.uploads.key("f.pdf").startswith(s3.interactive.prefix)


def test_a_decomposed_accent_is_stored_composed():
    assert (
        sanitize_filename("re\u0301sume\u0301 l\u2019e\u0301te\u0301.pdf")
        == "r\u00e9sum\u00e9 l\u2019\u00e9t\u00e9.pdf"
    )


@pytest.mark.usefixtures("setup_db")
def test_a_file_erased_by_a_restart_is_restored_from_s3(mocker):
    result, _ = upload_file(io.BytesIO(b"contenu"), "notes.txt", conversation_id=make_conversation())
    Path(result.storage_path).unlink()
    download = mocker.patch.object(s3.uploads, "download", return_value=b"contenu")

    restore_conversation_files(result.conversation_id)

    download.assert_called_once_with(result.stored_filename)
    assert Path(result.storage_path).read_bytes() == b"contenu"


@pytest.mark.usefixtures("setup_db")
def test_a_file_still_on_disk_is_not_downloaded_again(mocker):
    result, _ = upload_file(io.BytesIO(b"contenu"), "notes.txt", conversation_id=make_conversation())
    download = mocker.patch.object(s3.uploads, "download")

    restore_conversation_files(result.conversation_id)

    download.assert_not_called()


@pytest.mark.usefixtures("setup_db")
def test_a_file_absent_from_s3_does_not_stop_the_others(mocker):
    conversation_id = make_conversation()
    lost, _ = upload_file(io.BytesIO(b"un"), "un.txt", conversation_id=conversation_id)
    kept, _ = upload_file(io.BytesIO(b"deux"), "deux.txt", conversation_id=conversation_id)
    for uploaded in (lost, kept):
        Path(uploaded.storage_path).unlink()
    mocker.patch.object(s3.uploads, "download", side_effect={kept.stored_filename: b"deux"}.get)

    restore_conversation_files(conversation_id)

    assert Path(kept.storage_path).read_bytes() == b"deux"


@pytest.mark.usefixtures("setup_db")
def test_a_file_that_cannot_be_written_is_skipped(mocker):
    result, _ = upload_file(io.BytesIO(b"un"), "un.txt", conversation_id=make_conversation())
    Path(result.storage_path).unlink()
    mocker.patch.object(s3.uploads, "download", return_value=b"un")
    mocker.patch.object(Path, "write_bytes", side_effect=OSError("disque plein"))

    restore_conversation_files(result.conversation_id)

    assert not Path(result.storage_path).exists()


@pytest.mark.usefixtures("setup_db")
def test_uploading_again_a_file_lost_from_disk_stores_it_again():
    conversation_id = make_conversation()
    first, _ = upload_file(io.BytesIO(b"same"), "a.txt", conversation_id=conversation_id)
    Path(first.storage_path).unlink()

    second, _ = upload_file(io.BytesIO(b"same"), "a.txt", conversation_id=conversation_id)

    assert Path(second.storage_path).read_bytes() == b"same"
