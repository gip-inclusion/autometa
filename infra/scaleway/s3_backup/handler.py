"""Scaleway Function: daily snapshot of SOURCE_BUCKET → BACKUP_BUCKET/backup/YYYY-MM-DD/."""

import json
import logging
import time
from datetime import date, datetime, timedelta, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

import config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MANIFEST_FILENAME = "_MANIFEST.json"


def build_client():
    return boto3.client(
        "s3",
        endpoint_url=config.S3_ENDPOINT,
        aws_access_key_id=config.S3_ACCESS_KEY,
        aws_secret_access_key=config.S3_SECRET_KEY,
        region_name=config.S3_REGION,
        config=Config(signature_version="s3v4", retries={"max_attempts": 5, "mode": "standard"}),
    )


def _existing_etag(client, bucket: str, key: str) -> str | None:
    try:
        return client.head_object(Bucket=bucket, Key=key)["ETag"]
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return None
        raise


def snapshot(client, source: str, target: str, snapshot_date: str) -> dict:
    prefix = f"backup/{snapshot_date}/"
    start = time.monotonic()
    copied = 0
    skipped = 0
    total_bytes = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=source):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            dest_key = f"{prefix}{key}"
            # Why: re-runs after partial failure skip already-copied objects (ETag match = identical bytes).
            if _existing_etag(client, target, dest_key) == obj["ETag"]:
                skipped += 1
                total_bytes += obj["Size"]
                continue
            client.copy_object(
                Bucket=target,
                Key=dest_key,
                CopySource={"Bucket": source, "Key": key},
                MetadataDirective="COPY",
            )
            copied += 1
            total_bytes += obj["Size"]
    manifest = {
        "snapshot": snapshot_date,
        "source": source,
        "target": f"{target}/{prefix}",
        "copied": copied,
        "skipped": skipped,
        "objects": copied + skipped,
        "bytes": total_bytes,
        "duration_s": round(time.monotonic() - start, 2),
        "ok": True,
    }
    # Why: manifest written last — its presence atteste que la copie est complète (check Sentry s'y fie).
    client.put_object(
        Bucket=target,
        Key=f"{prefix}{MANIFEST_FILENAME}",
        Body=json.dumps(manifest).encode(),
        ContentType="application/json",
    )
    return manifest


def purge_old_snapshots(client, bucket: str, retention_days: int, today: date) -> int:
    cutoff = today - timedelta(days=retention_days)
    paginator = client.get_paginator("list_objects_v2")
    deleted = 0
    for page in paginator.paginate(Bucket=bucket, Prefix="backup/", Delimiter="/"):
        for common in page.get("CommonPrefixes", []) or []:
            sub = common["Prefix"]
            try:
                day = datetime.strptime(sub.split("/")[1], "%Y-%m-%d").date()
            except (IndexError, ValueError):
                continue
            if day >= cutoff:
                continue
            for inner in paginator.paginate(Bucket=bucket, Prefix=sub):
                batch = [{"Key": o["Key"]} for o in inner.get("Contents", [])]
                if not batch:
                    continue
                client.delete_objects(Bucket=bucket, Delete={"Objects": batch, "Quiet": True})
                deleted += len(batch)
    return deleted


def handle(event, context):
    today = datetime.now(timezone.utc).date()
    client = build_client()
    result = snapshot(client, config.SOURCE_BUCKET, config.BACKUP_BUCKET, today.isoformat())
    logger.info("snapshot done: %s", result)
    if config.RETENTION_DAYS > 0:
        purged = purge_old_snapshots(client, config.BACKUP_BUCKET, config.RETENTION_DAYS, today)
        logger.info("purged %d objects older than %d days", purged, config.RETENTION_DAYS)
        result["purged"] = purged
    return result
