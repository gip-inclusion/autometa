import datetime
import json
import logging

from botocore.exceptions import ClientError
from prefect import flow

from flows.base import run_with_recording
from web import config
from web import s3 as s3_module

logger = logging.getLogger(__name__)


def check_backup_manifest() -> None:
    if not config.BACKUP_S3_BUCKET:
        logger.info("BACKUP_S3_BUCKET not configured; skipping")
        return

    client = s3_module.make_client()
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    manifest_key = f"backup/{today}/_MANIFEST.json"
    try:
        body = client.get_object(Bucket=config.BACKUP_S3_BUCKET, Key=manifest_key)["Body"].read()
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("404", "NoSuchKey"):
            raise RuntimeError(
                f"Snapshot manifest missing: s3://{config.BACKUP_S3_BUCKET}/{manifest_key}"
            ) from exc
        raise

    manifest = json.loads(body)
    if not manifest.get("ok"):
        raise RuntimeError(f"Snapshot manifest reports failure: {manifest}")
    logger.info(
        "S3 snapshot OK: s3://%s/%s (%d objects, %d bytes)",
        config.BACKUP_S3_BUCKET,
        manifest.get("target", manifest_key),
        manifest.get("objects", 0),
        manifest.get("bytes", 0),
    )


@flow(name="check-s3-backups", log_prints=True)
def check_s3_backups() -> None:
    run_with_recording("check-s3-backups", check_backup_manifest)
