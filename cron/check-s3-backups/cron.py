"""Check that today's S3 snapshot exists in the backup bucket. Periodic — Sentry alerts via cron monitor on failure."""

import datetime
import logging

import boto3
from botocore.config import Config

from web import config

logger = logging.getLogger(__name__)


def main() -> None:
    if not config.BACKUP_S3_BUCKET:
        logger.info("BACKUP_S3_BUCKET not configured; skipping")
        return

    client = boto3.client(
        "s3",
        endpoint_url=config.S3_ENDPOINT,
        aws_access_key_id=config.S3_ACCESS_KEY,
        aws_secret_access_key=config.S3_SECRET_KEY,
        region_name=config.S3_REGION,
        config=Config(signature_version="s3v4"),
    )
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    prefix = f"backup/{today}/"
    response = client.list_objects_v2(Bucket=config.BACKUP_S3_BUCKET, Prefix=prefix, MaxKeys=1)
    if not response.get("KeyCount", 0):
        raise RuntimeError(f"S3 snapshot missing: s3://{config.BACKUP_S3_BUCKET}/{prefix}")
    logger.info("S3 snapshot OK: s3://%s/%s", config.BACKUP_S3_BUCKET, prefix)


if __name__ == "__main__":
    main()
