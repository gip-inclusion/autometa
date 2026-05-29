"""S3 storage with prefixed store instances."""

import logging
import mimetypes
from typing import BinaryIO, Optional

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from . import config

logger = logging.getLogger(__name__)


def make_client():
    return boto3.client(
        "s3",
        endpoint_url=config.S3_ENDPOINT,
        aws_access_key_id=config.S3_ACCESS_KEY,
        aws_secret_access_key=config.S3_SECRET_KEY,
        region_name=config.S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )


_client = make_client()
logger.info("S3 storage: bucket=%s, endpoint=%s", config.S3_BUCKET, config.S3_ENDPOINT)


class S3Store:
    """S3 operations scoped to a key prefix."""

    def __init__(self, prefix: str):
        self.prefix = prefix

    def key(self, path: str) -> str:
        return f"{self.prefix}{path.replace(chr(92), '/').lstrip('/')}"

    def upload(self, path: str, content: bytes, content_type: Optional[str] = None) -> bool:
        k = self.key(path)
        if content_type is None:
            content_type, _ = mimetypes.guess_type(k)
            content_type = content_type or "application/octet-stream"
        try:
            _client.put_object(Bucket=config.S3_BUCKET, Key=k, Body=content, ContentType=content_type)
            return True
        except ClientError as e:
            logger.error("S3 upload failed for %s: %s", k, e)
            return False

    def upload_fileobj(self, path: str, fileobj: BinaryIO, content_type: Optional[str] = None) -> bool:
        return self.upload(path, fileobj.read(), content_type)

    def download(self, path: str) -> Optional[bytes]:
        k = self.key(path)
        try:
            response = _client.get_object(Bucket=config.S3_BUCKET, Key=k)
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.debug("S3 file not found: %s", k)
                return None
            logger.error("S3 download failed for %s: %s", k, e)
            return None

    def get_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        k = self.key(path)
        try:
            return _client.generate_presigned_url(
                "get_object",
                Params={"Bucket": config.S3_BUCKET, "Key": k},
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            logger.error("Failed to generate presigned URL for %s: %s", k, e)
            return None

    def stream(self, path: str, chunk_size: int = 65_536):
        k = self.key(path)
        try:
            response = _client.get_object(Bucket=config.S3_BUCKET, Key=k)
            body = response["Body"]

            def chunks():
                try:
                    while True:
                        chunk = body.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
                finally:
                    body.close()

            return chunks()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.debug("S3 file not found: %s", k)
                return None
            logger.error("S3 stream failed for %s: %s", k, e)
            return None

    def exists(self, path: str) -> bool:
        k = self.key(path)
        try:
            _client.head_object(Bucket=config.S3_BUCKET, Key=k)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error("S3 head_object failed for %s: %s", k, e)
            return False

    def delete(self, path: str) -> bool:
        k = self.key(path)
        try:
            _client.delete_object(Bucket=config.S3_BUCKET, Key=k)
            logger.debug("Deleted from S3: %s", k)
            return True
        except ClientError as e:
            logger.error("S3 delete failed for %s: %s", k, e)
            return False

    def list_files(self, prefix: str = "") -> list[dict]:
        full_prefix = self.key(prefix)
        files = []
        try:
            paginator = _client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=config.S3_BUCKET, Prefix=full_prefix):
                for obj in page.get("Contents", []):
                    files.append({
                        "path": obj["Key"][len(self.prefix) :],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                    })
        except ClientError as e:
            logger.error("S3 list failed for prefix %s: %s", full_prefix, e)
        return files

    def list_directories(self, prefix: str = "") -> list[str]:
        if not config.S3_BUCKET:
            return []
        full_prefix = self.key(prefix)
        directories = set()
        try:
            response = _client.list_objects_v2(
                Bucket=config.S3_BUCKET,
                Prefix=full_prefix,
                Delimiter="/",
            )
            for common_prefix in response.get("CommonPrefixes", []):
                dir_path = common_prefix["Prefix"][len(full_prefix) :].rstrip("/")
                directories.add(dir_path)
        except ClientError as e:
            logger.error("S3 list directories failed for prefix %s: %s", full_prefix, e)
        return sorted(directories)


interactive = S3Store("interactive/")
sessions = S3Store("sessions/")
uploads = S3Store("interactive/uploads/")


def list_prefix(bucket: str, prefix: str) -> list[str]:
    """All object keys under prefix in the given bucket."""
    keys: list[str] = []
    paginator = _client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def copy_prefix(src_prefix: str, dst_bucket: str, dst_prefix: str) -> int:
    """Copy every object under src_prefix (in S3_BUCKET) to dst_bucket/dst_prefix. Returns count."""
    count = 0
    for src_key in list_prefix(config.S3_BUCKET, src_prefix):
        dst_key = f"{dst_prefix}{src_key[len(src_prefix) :]}"
        try:
            _client.copy_object(
                Bucket=dst_bucket,
                Key=dst_key,
                CopySource={"Bucket": config.S3_BUCKET, "Key": src_key},
            )
        except ClientError:
            body = _client.get_object(Bucket=config.S3_BUCKET, Key=src_key)["Body"].read()
            _client.put_object(Bucket=dst_bucket, Key=dst_key, Body=body)
        count += 1
    return count


def delete_prefix(bucket: str, prefix: str) -> int:
    """Delete every object under prefix in the given bucket. Returns count."""
    keys = list_prefix(bucket, prefix)
    for key in keys:
        _client.delete_object(Bucket=bucket, Key=key)
    return len(keys)
