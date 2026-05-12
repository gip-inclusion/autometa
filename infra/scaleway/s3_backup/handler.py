"""Scaleway Function: daily snapshot of SOURCE_BUCKET → BACKUP_BUCKET/backup/YYYY-MM-DD/."""

import logging
import time
from datetime import datetime, timezone

import boto3
from botocore.config import Config

import config

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def build_client():
    return boto3.client(
        "s3",
        endpoint_url=config.S3_ENDPOINT,
        aws_access_key_id=config.S3_ACCESS_KEY,
        aws_secret_access_key=config.S3_SECRET_KEY,
        region_name=config.S3_REGION,
        config=Config(signature_version="s3v4", retries={"max_attempts": 5, "mode": "standard"}),
    )


def snapshot(client, source: str, target: str, snapshot_date: str) -> dict:
    prefix = f"backup/{snapshot_date}/"
    start = time.monotonic()
    objects = 0
    total_bytes = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=source):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            client.copy_object(
                Bucket=target,
                Key=f"{prefix}{key}",
                CopySource={"Bucket": source, "Key": key},
                MetadataDirective="COPY",
            )
            objects += 1
            total_bytes += obj["Size"]
    return {
        "snapshot": snapshot_date,
        "source": source,
        "target": f"{target}/{prefix}",
        "objects": objects,
        "bytes": total_bytes,
        "duration_s": round(time.monotonic() - start, 2),
    }


def handle(event, context):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = snapshot(build_client(), config.SOURCE_BUCKET, config.BACKUP_BUCKET, today)
    logger.info("snapshot done: %s", result)
    return result
