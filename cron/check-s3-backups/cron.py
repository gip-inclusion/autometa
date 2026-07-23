"""Check that today's S3 snapshot manifest exists in the backup bucket. Periodic — Sentry alerts via cron monitor on failure."""

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
    manifest_key = f"backup/{today}/_MANIFEST.json"
    try:
        body = client.get_object(Bucket=config.BACKUP_S3_BUCKET, Key=manifest_key)["Body"].read()
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("404", "NoSuchKey"):
            # Le manifeste est écrit en dernier : s'il manque mais que le dossier du jour contient
            # des objets, le producteur a échoué en cours de route (backup partiel), ce qui appelle
            # une remédiation différente d'un backup jamais lancé.
            listing = client.list_objects_v2(Bucket=config.BACKUP_S3_BUCKET, Prefix=f"backup/{today}/", MaxKeys=1)
            if listing.get("KeyCount", 0) > 0:
                raise RuntimeError(
                    f"Snapshot incomplet: données présentes sous s3://{config.BACKUP_S3_BUCKET}/backup/{today}/ "
                    "mais _MANIFEST.json manquant (le producteur a échoué avant d'écrire le manifeste)."
                ) from exc
            raise RuntimeError(
                f"Aucun snapshot pour {today}: s3://{config.BACKUP_S3_BUCKET}/backup/{today}/ est vide "
                "(backup non exécuté)."
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


if __name__ == "__main__":
    main()
