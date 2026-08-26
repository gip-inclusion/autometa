"""Check that today's S3 mirror manifest exists in the backup bucket. Periodic — Sentry alerts via cron monitor on failure."""

import datetime
import json
import logging

from botocore.exceptions import ClientError

from web import config
from web import s3 as s3_module

logger = logging.getLogger(__name__)


def main() -> None:
    if not config.BACKUP_S3_BUCKET:
        logger.info("BACKUP_S3_BUCKET not configured; skipping")
        return

    client = s3_module.make_client()
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    manifest_key = f"manifests/{today}.json"
    try:
        body = client.get_object(Bucket=config.BACKUP_S3_BUCKET, Key=manifest_key)["Body"].read()
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("404", "NoSuchKey"):
            raise RuntimeError(f"Mirror manifest missing: s3://{config.BACKUP_S3_BUCKET}/{manifest_key}") from exc
        raise

    manifest = json.loads(body)
    if not manifest.get("ok"):
        raise RuntimeError(f"Mirror manifest reports failure: {manifest}")
    logger.info(
        "S3 mirror OK: s3://%s (%d objects, %d bytes)",
        manifest.get("target", f"{config.BACKUP_S3_BUCKET}/{manifest_key}"),
        manifest.get("objects", 0),
        manifest.get("bytes", 0),
    )


if __name__ == "__main__":
    main()
