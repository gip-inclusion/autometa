"""Sync Claude CLI session files to/from S3 for horizontal scaling."""

import logging
from pathlib import Path

from botocore.exceptions import ClientError

from . import config
from .s3 import s3_client

logger = logging.getLogger(__name__)

S3_SESSION_PREFIX = "sessions/"


def _get_project_slug() -> str:
    return str(config.BASE_DIR).replace("/", "-")


def get_session_dir() -> Path:
    return Path.home() / ".claude" / "projects" / _get_project_slug()


def get_session_path(session_id: str) -> Path:
    return get_session_dir() / f"{session_id}.jsonl"


def get_subagents_dir(session_id: str) -> Path:
    return get_session_dir() / session_id / "subagents"


def download_session(session_id: str) -> bool:
    """Download a session and its subagents from S3 to the local CLI directory."""
    if not config.S3_BUCKET:
        return False

    local_path = get_session_path(session_id)
    s3_key = f"{S3_SESSION_PREFIX}{session_id}.jsonl"

    try:
        response = s3_client.get_object(Bucket=config.S3_BUCKET, Key=s3_key)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(response["Body"].read())
        logger.info("Downloaded session %s from S3 (%d bytes)", session_id, local_path.stat().st_size)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            logger.debug("Session %s not found in S3", session_id)
            return False
        logger.error("Failed to download session %s: %s", session_id, e)
        return False

    _download_subagents(session_id)
    return True


def _download_subagents(session_id: str):
    prefix = f"{S3_SESSION_PREFIX}{session_id}/subagents/"
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=config.S3_BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                relative = key[len(f"{S3_SESSION_PREFIX}{session_id}/") :]
                local_path = get_session_dir() / session_id / relative
                local_path.parent.mkdir(parents=True, exist_ok=True)
                response = s3_client.get_object(Bucket=config.S3_BUCKET, Key=key)
                local_path.write_bytes(response["Body"].read())
                logger.debug("Downloaded subagent file: %s", relative)
    except ClientError as e:
        logger.warning("Failed to download subagents for %s: %s", session_id, e)


def upload_session(session_id: str) -> bool:
    """Upload a session and its subagents from local CLI directory to S3."""
    if not config.S3_BUCKET:
        return False

    local_path = get_session_path(session_id)
    if not local_path.exists():
        logger.warning("Session file not found locally: %s", local_path)
        return False

    s3_key = f"{S3_SESSION_PREFIX}{session_id}.jsonl"
    try:
        s3_client.put_object(
            Bucket=config.S3_BUCKET,
            Key=s3_key,
            Body=local_path.read_bytes(),
            ContentType="application/x-ndjson",
        )
        logger.info("Uploaded session %s to S3 (%d bytes)", session_id, local_path.stat().st_size)
    except ClientError as e:
        logger.error("Failed to upload session %s: %s", session_id, e)
        return False

    _upload_subagents(session_id)
    return True


def _upload_subagents(session_id: str):
    subagents_dir = get_subagents_dir(session_id)
    if not subagents_dir.exists():
        return

    for path in subagents_dir.rglob("*.jsonl"):
        relative = path.relative_to(get_session_dir() / session_id)
        s3_key = f"{S3_SESSION_PREFIX}{session_id}/{relative}"
        try:
            s3_client.put_object(
                Bucket=config.S3_BUCKET,
                Key=s3_key,
                Body=path.read_bytes(),
                ContentType="application/x-ndjson",
            )
            logger.debug("Uploaded subagent file: %s", relative)
        except ClientError as e:
            logger.warning("Failed to upload subagent %s: %s", relative, e)
