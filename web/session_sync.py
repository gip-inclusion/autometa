"""Sync Claude CLI session files to/from S3 for horizontal scaling."""

import hashlib
import json
import logging
import time
from pathlib import Path

from botocore.exceptions import BotoCoreError

from . import config, s3

logger = logging.getLogger(__name__)

# Why: resume sessions almost always exist in S3 (confirmed in prod); a transient download
# blip would otherwise silently drop the conversation to the lossy history fallback.
_DOWNLOAD_ATTEMPTS = 3


def _get_project_slug() -> str:
    return str(config.BASE_DIR).replace("/", "-")


def get_session_dir() -> Path:
    return Path.home() / ".claude" / "projects" / _get_project_slug()


def get_session_path(session_id: str) -> Path:
    return get_session_dir() / f"{session_id}.jsonl"


def get_subagents_dir(session_id: str) -> Path:
    return get_session_dir() / session_id / "subagents"


def _local_session_matches(local_path: Path, head: dict) -> bool:
    if not local_path.exists() or local_path.stat().st_size != head["size"]:
        return False
    if "-" in head["etag"]:  # multipart upload: size match is the strongest signal available
        return True
    return hashlib.md5(local_path.read_bytes(), usedforsecurity=False).hexdigest() == head["etag"]


def download_session(session_id: str) -> bool:
    if not config.S3_BUCKET:
        return False

    local_path = get_session_path(session_id)
    head = s3.sessions.head(f"{session_id}.jsonl")
    if head is not None:
        if not head["exists"]:
            logger.debug("Session %s absent from S3; skipping download", session_id)
            return False
        if _local_session_matches(local_path, head):
            logger.debug("Session %s already current locally; skipping S3 download", session_id)
            return True

    content = None
    for attempt in range(1, _DOWNLOAD_ATTEMPTS + 1):
        try:
            content = s3.sessions.download(f"{session_id}.jsonl")
        except BotoCoreError as exc:
            # Why: s3.download swallows ClientError to None but lets network/timeout errors raise.
            logger.warning(
                "Session %s download error (attempt %d/%d): %s", session_id, attempt, _DOWNLOAD_ATTEMPTS, exc
            )
        if content is not None:
            break
        if attempt < _DOWNLOAD_ATTEMPTS:
            time.sleep(0.3 * attempt)  # 0.3s then 0.6s backoff between download retries

    if content is None:
        logger.warning("Session %s unavailable in S3 after %d attempts", session_id, _DOWNLOAD_ATTEMPTS)
        return False

    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(content)
    logger.info("Downloaded session %s from S3 (%d bytes)", session_id, len(content))

    _download_subagents(session_id)
    return True


def _download_subagents(session_id: str):
    for entry in s3.sessions.list_files(f"{session_id}/subagents/"):
        relative = entry["path"][len(f"{session_id}/") :]
        content = s3.sessions.download(entry["path"])
        if content is not None:
            local_path = get_session_dir() / session_id / relative
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(content)
            logger.debug("Downloaded subagent file: %s", relative)


def upload_session(session_id: str) -> bool:
    if not config.S3_BUCKET:
        return False

    local_path = get_session_path(session_id)
    if not local_path.exists():
        logger.warning("Session file not found locally: %s", local_path)
        return False

    if not s3.sessions.upload(f"{session_id}.jsonl", local_path.read_bytes(), "application/x-ndjson"):
        return False

    logger.info("Uploaded session %s to S3 (%d bytes)", session_id, local_path.stat().st_size)
    _upload_subagents(session_id)
    return True


def _upload_subagents(session_id: str):
    subagents_dir = get_subagents_dir(session_id)
    if not subagents_dir.exists():
        return

    for path in subagents_dir.rglob("*.jsonl"):
        relative = path.relative_to(get_session_dir() / session_id)
        s3.sessions.upload(f"{session_id}/{relative}", path.read_bytes(), "application/x-ndjson")
        logger.debug("Uploaded subagent file: %s", relative)


def _rewrite_session_id(jsonl_bytes: bytes, new_id: str) -> bytes:
    out = []
    for line in jsonl_bytes.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("Skipping malformed JSONL line while rewriting session id")
            out.append(line)
            continue
        if obj.get("sessionId"):
            obj["sessionId"] = new_id
        out.append(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    return b"\n".join(out) + (b"\n" if out else b"")


def copy_session(src_id: str, dst_id: str) -> bool:
    if not config.S3_BUCKET:
        return False

    content = s3.sessions.download(f"{src_id}.jsonl")
    if content is None:
        logger.warning("Cannot copy session: source %s not found in S3", src_id)
        return False

    rewritten = _rewrite_session_id(content, dst_id)
    if not s3.sessions.upload(f"{dst_id}.jsonl", rewritten, "application/x-ndjson"):
        return False

    local_path = get_session_path(dst_id)
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(rewritten)
    except OSError:
        logger.warning("Could not cache copied session %s locally; S3 copy stands", dst_id)

    logger.info("Copied session %s -> %s (%d bytes)", src_id, dst_id, len(rewritten))
    _copy_subagents(src_id, dst_id)
    return True


def _copy_subagents(src_id: str, dst_id: str):
    for entry in s3.sessions.list_files(f"{src_id}/subagents/"):
        relative = entry["path"][len(f"{src_id}/") :]
        content = s3.sessions.download(entry["path"])
        if content is None:
            continue
        rewritten = _rewrite_session_id(content, dst_id)
        if not s3.sessions.upload(f"{dst_id}/{relative}", rewritten, "application/x-ndjson"):
            logger.warning("Failed to copy subagent file %s to %s/%s", entry["path"], dst_id, relative)
            continue
        logger.debug("Copied subagent file: %s", relative)
