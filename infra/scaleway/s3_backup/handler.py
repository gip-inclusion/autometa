"""Scaleway Function: mirror SOURCE_BUCKET into BACKUP_BUCKET/mirror/ — history comes from bucket versioning."""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

import config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MIRROR_PREFIX = "mirror/"


def build_client():
    return boto3.client(
        "s3",
        endpoint_url=config.S3_ENDPOINT,
        aws_access_key_id=config.S3_ACCESS_KEY,
        aws_secret_access_key=config.S3_SECRET_KEY,
        region_name=config.S3_REGION,
        config=Config(signature_version="s3v4", retries={"max_attempts": 5, "mode": "standard"}),
    )


def inventory(client, bucket: str, prefix: str = "") -> dict[str, tuple[str, int]]:
    """Key relative to prefix → (ETag, size), for every object under prefix."""
    paginator = client.get_paginator("list_objects_v2")
    return {
        obj["Key"][len(prefix) :]: (obj["ETag"], obj["Size"])
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix)
        for obj in page.get("Contents", [])
    }


def require_versioning(client, bucket: str) -> None:
    """Refuse a target that keeps no history: there, mirroring an overwrite or a deletion is irreversible."""
    status = client.get_bucket_versioning(Bucket=bucket).get("Status")
    if status != "Enabled":
        raise RuntimeError(f"{bucket} versioning is {status or 'disabled'} — refusing to mirror into it")


def mirror(client, source: str, target: str, run_date: str) -> dict:
    start = time.monotonic()
    require_versioning(client, target)
    # Why: two listings replace a per-object HEAD probe — a pass costs O(pages), not O(objects).
    src = inventory(client, source)
    mirrored = inventory(client, target, MIRROR_PREFIX)
    stale = [key for key, (etag, _) in src.items() if mirrored.get(key, (None, 0))[0] != etag]
    removed = [key for key in mirrored if key not in src]

    def copy_one(key: str) -> str | None:
        try:
            client.copy_object(
                Bucket=target,
                Key=MIRROR_PREFIX + key,
                CopySource={"Bucket": source, "Key": key},
                MetadataDirective="COPY",
            )
        # Why: BotoCoreError (read/connection timeout) on one object must count as a failed object,
        # not crash the whole pass via pool.map and lose the final manifest.
        except (ClientError, BotoCoreError) as exc:
            return f"copy {key}: {exc}"
        return None

    def delete_one(key: str) -> str | None:
        try:
            # Why: naming no version leaves a delete marker, so the mirror keeps the removed object's history.
            client.delete_object(Bucket=target, Key=MIRROR_PREFIX + key)
        except (ClientError, BotoCoreError) as exc:
            return f"delete {key}: {exc}"
        return None

    # Parallel server-side copies — the bottleneck is API round-trips, not bandwidth.
    with ThreadPoolExecutor(max_workers=16) as pool:
        errors = [error for error in pool.map(copy_one, stale) if error]
        errors += [error for error in pool.map(delete_one, removed) if error]

    manifest = {
        "run": run_date,
        "source": source,
        "target": f"{target}/{MIRROR_PREFIX}",
        "objects": len(src),
        "bytes": sum(size for _, size in src.values()),
        "copied": len(stale) - sum(1 for error in errors if error.startswith("copy ")),
        "unchanged": len(src) - len(stale),
        # Why: a multipart ETag is not a plain MD5, so a copy's ETag never equals it and the object
        # re-copies on every pass. Surfaced here so that churn is visible instead of silent.
        "multipart": sum(1 for etag, _ in src.values() if "-" in etag.strip('"')),
        "deleted": len(removed) - sum(1 for error in errors if error.startswith("delete ")),
        "failed": len(errors),
        "duration_s": round(time.monotonic() - start, 2),
        "ok": not errors,
    }
    if errors:
        manifest["errors"] = errors[:20]
    # Why: manifest written last — its presence atteste que la passe est complète (le cron de contrôle s'y fie).
    client.put_object(
        Bucket=target,
        Key=f"manifests/{run_date}.json",
        Body=json.dumps(manifest).encode(),
        ContentType="application/json",
    )
    return manifest


def handle(event, context):
    today = datetime.now(timezone.utc).date().isoformat()
    result = mirror(build_client(), config.SOURCE_BUCKET, config.BACKUP_BUCKET, today)
    logger.info("mirror pass done: %s", result)
    if not result["ok"]:
        raise RuntimeError(f"mirror pass incomplete: {result['failed']} object(s) failed")
    return result
