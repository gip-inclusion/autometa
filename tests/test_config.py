"""Config env-var wiring tests."""

from web import config


def test_public_dashboards_buckets_read_deployment_env_var_names():
    # Why: the public buckets are provisioned under PUBLIC_DASHBOARDS_BUCKET_<ENV>
    # (conftest sets those names); a divergent key silently resolves to None and
    # blocks publication with public-bucket-not-configured.
    assert config.PUBLIC_S3_BUCKET_STAGING == "test-staging-bucket"
    assert config.PUBLIC_S3_BUCKET_PROD == "test-prod-bucket"
