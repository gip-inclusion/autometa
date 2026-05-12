"""Function-local config. Standalone deployment — cannot import web.config."""

import os

S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "https://s3.fr-par.scw.cloud")
S3_REGION = os.environ.get("S3_REGION", "fr-par")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY")
SOURCE_BUCKET = os.environ.get("SOURCE_BUCKET")
BACKUP_BUCKET = os.environ.get("BACKUP_BUCKET")
