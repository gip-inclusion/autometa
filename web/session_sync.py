"""Sync Claude CLI session files to/from S3 for horizontal scaling."""

import logging
from pathlib import Path

from . import config, s3

logger = logging.getLogger(__name__)


def _get_project_slug() -> str:
    return str(config.BASE_DIR).replace("/", "-")


def get_session_dir() -> Path:
    return Path.home() / ".claude" / "projects" / _get_project_slug()


def get_session_path(session_id: str) -> Path:
    return get_session_dir() / f"{session_id}.jsonl"


def get_subagents_dir(session_id: str) -> Path:
    return get_session_dir() / session_id / "subagents"


def download_session(session_id: str) -> bool:
    if not config.S3_BUCKET:
        return False

    content = s3.sessions.download(f"{session_id}.jsonl")
    if content is None:
        return False

    local_path = get_session_path(session_id)
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
