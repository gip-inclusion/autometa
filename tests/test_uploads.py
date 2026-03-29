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
os.environ["DATA_DIR"] = _tmp_dir

# Now we can safely import
from web import config
from web.database import ConversationStore, UploadedFile, init_db
from web.uploads import (
    BLOCKED_EXTENSIONS,
    TEXT_EXTENSIONS,
    BlockedFileTypeError,
    FileTooLargeError,
    compute_sha256,
    format_file_for_context,
    generate_stored_filename,
    is_text_file,
    sanitize_filename,
    upload_file,
)

# Configure for testing
config.DATA_DIR = Path(_tmp_dir)
config.UPLOADS_DIR = Path(_tmp_dir) / "uploads"
config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
config.MAX_UPLOAD_SIZE = 10 * 1024 * 1024
config.TEXT_FILE_INLINE_LIMIT = 1024
config.USE_S3 = False

# Create a fresh store for tests
init_db()
store = ConversationStore()


@pytest.fixture
def setup_db(tmp_path, monkeypatch):
    """Tmp upload dirs, stub ClamAV, one DB transaction rolled back per test."""
    import web.config as config
    from web.db import test_transaction

    monkeypatch.setattr(
        "web.uploads.scan_with_clamav",
        lambda _path: (False, None),
    )

    with test_transaction():
        config.DATA_DIR = tmp_path
        config.UPLOADS_DIR = tmp_path / "uploads"
        config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        config.MAX_UPLOAD_SIZE = 10 * 1024 * 1024
        config.TEXT_FILE_INLINE_LIMIT = 1024
        config.USE_S3 = False

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
        conversation_id=None,
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
        conversation_id=None,
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
        conversation_id=None,
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
            conversation_id=None,
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
            conversation_id=None,
            user_id="test@example.com",
        )


@pytest.mark.usefixtures("setup_db")
def test_upload_file_duplicate_detection():
    """Duplicate files are detected by hash."""
    content = b"same content"
    file_obj1 = io.BytesIO(content)
    file_obj2 = io.BytesIO(content)

    result1, _ = upload_file(
        file_obj=file_obj1,
        filename="file1.txt",
        conversation_id=None,
        user_id="user1@example.com",
    )

    result2, _ = upload_file(
        file_obj=file_obj2,
        filename="file2.txt",  # Different name
        conversation_id=None,
        user_id="user2@example.com",
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
        conversation_id=None,
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
        conversation_id=None,
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
        conversation_id=None,
        user_id="test@example.com",
    )

    # Find by hash
    found = store.get_uploaded_file_by_hash(result.sha256_hash)
    assert found is not None
    assert found.id == result.id


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
