"""Provision the backup bucket: versioning on, lifecycle bounding how long the mirror keeps old versions."""

import logging

from botocore.exceptions import ClientError

import config
from handler import build_client

logger = logging.getLogger(__name__)

VERSION_RULE_ID = "bounded-version-history"


def apply(client, bucket: str, retention_days: int) -> list[dict]:
    """Enable versioning and (re)install the lifecycle rule that bounds the mirror's version history."""
    client.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
    try:
        existing = client.get_bucket_lifecycle_configuration(Bucket=bucket)["Rules"]
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "NoSuchLifecycleConfiguration":
            raise
        existing = []
    rules = [rule for rule in existing if rule["ID"] != VERSION_RULE_ID]
    rules.append({
        "ID": VERSION_RULE_ID,
        "Status": "Enabled",
        # Why: the whole bucket, not just mirror/ — on a versioned bucket an Expiration rule merely hides
        # an object behind a delete marker, so anything this rule misses (the legacy dated snapshots, the
        # manifests) would keep its versions forever.
        "Filter": {"Prefix": ""},
        # Why: only noncurrent versions may expire — an Expiration Days/Date here would delete the live mirror.
        "NoncurrentVersionExpiration": {"NoncurrentDays": retention_days},
        "Expiration": {"ExpiredObjectDeleteMarker": True},
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7},
    })
    client.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration={"Rules": rules})
    return rules


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    apply(build_client(), config.BACKUP_BUCKET, config.RETENTION_DAYS)
    logger.info(
        "provisioned %s: versioning enabled, %s-day version history", config.BACKUP_BUCKET, config.RETENTION_DAYS
    )
