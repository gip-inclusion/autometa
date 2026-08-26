"""Tests for the backup bucket provisioning (versioning + lifecycle)."""

import pytest
from botocore.exceptions import ClientError

import provision

BUCKET = "matometa-backup"
LEGACY_RULE = {
    "ID": "expire-snapshots-14d",
    "Status": "Enabled",
    "Filter": {"Prefix": "backup/"},
    "Expiration": {"Days": 14},
}


class FakeS3:
    def __init__(self, rules=None):
        self.rules = rules
        self.versioning = None

    def put_bucket_versioning(self, Bucket, VersioningConfiguration):
        self.versioning = VersioningConfiguration["Status"]

    def get_bucket_lifecycle_configuration(self, Bucket):
        if self.rules is None:
            raise ClientError({"Error": {"Code": "NoSuchLifecycleConfiguration"}}, "GetBucketLifecycleConfiguration")
        return {"Rules": self.rules}

    def put_bucket_lifecycle_configuration(self, Bucket, LifecycleConfiguration):
        self.rules = LifecycleConfiguration["Rules"]


def managed_rule(client):
    return next(rule for rule in client.rules if rule["ID"] == provision.VERSION_RULE_ID)


def test_apply_enables_versioning():
    client = FakeS3()
    provision.apply(client, BUCKET, retention_days=30)
    assert client.versioning == "Enabled"


def test_apply_expires_noncurrent_versions_delete_markers_and_stale_multipart_uploads():
    client = FakeS3()
    provision.apply(client, BUCKET, retention_days=30)
    rule = managed_rule(client)
    assert rule["NoncurrentVersionExpiration"] == {"NoncurrentDays": 30}
    assert rule["Expiration"] == {"ExpiredObjectDeleteMarker": True}
    assert rule["AbortIncompleteMultipartUpload"] == {"DaysAfterInitiation": 7}


def test_apply_bounds_version_history_across_the_whole_bucket():
    # Why: on a versioned bucket an Expiration rule only hides an object behind a delete marker. Anything
    # this rule does not cover — the legacy dated snapshots, the manifests — would be retained forever.
    client = FakeS3(rules=[LEGACY_RULE])
    provision.apply(client, BUCKET, retention_days=30)
    assert managed_rule(client)["Filter"] == {"Prefix": ""}


@pytest.mark.parametrize("forbidden", ["Days", "Date"])
def test_apply_never_expires_current_versions(forbidden):
    # Why: the rule spans the whole bucket, so an Expiration Days/Date here would delete the live mirror.
    client = FakeS3()
    provision.apply(client, BUCKET, retention_days=30)
    assert forbidden not in managed_rule(client)["Expiration"]


def test_apply_keeps_rules_it_does_not_own():
    client = FakeS3(rules=[LEGACY_RULE])
    provision.apply(client, BUCKET, retention_days=30)
    assert LEGACY_RULE in client.rules


def test_apply_is_idempotent():
    client = FakeS3()
    provision.apply(client, BUCKET, retention_days=30)
    provision.apply(client, BUCKET, retention_days=7)
    assert [rule["ID"] for rule in client.rules] == [provision.VERSION_RULE_ID]
    assert managed_rule(client)["NoncurrentVersionExpiration"] == {"NoncurrentDays": 7}
