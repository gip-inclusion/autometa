from web import s3


def test_list_prefix(mocker):
    paginator = mocker.MagicMock()
    paginator.paginate.return_value = [{"Contents": [{"Key": "interactive/x/a.js"}, {"Key": "interactive/x/b.html"}]}]
    mocker.patch.object(s3._client, "get_paginator", return_value=paginator)
    assert s3.list_prefix("bkt", "interactive/x/") == ["interactive/x/a.js", "interactive/x/b.html"]


def test_copy_prefix_uses_server_side_copy(mocker):
    mocker.patch.object(s3, "list_prefix", return_value=["interactive/x/a.js"])
    copy = mocker.patch.object(s3._client, "copy_object")
    n = s3.copy_prefix("interactive/x/", "dst-bucket", "dashboards/x/")
    assert n == 1
    copy.assert_called_once_with(
        Bucket="dst-bucket",
        Key="dashboards/x/a.js",
        CopySource={"Bucket": s3.config.S3_BUCKET, "Key": "interactive/x/a.js"},
    )


def test_copy_prefix_falls_back_to_download_upload(mocker):
    from botocore.exceptions import ClientError

    mocker.patch.object(s3, "list_prefix", return_value=["interactive/x/a.js"])
    mocker.patch.object(
        s3._client, "copy_object", side_effect=ClientError({"Error": {"Code": "AccessDenied"}}, "CopyObject")
    )
    body = mocker.MagicMock()
    body.read.return_value = b"data"
    mocker.patch.object(s3._client, "get_object", return_value={"Body": body})
    put = mocker.patch.object(s3._client, "put_object")
    s3.copy_prefix("interactive/x/", "dst-bucket", "dashboards/x/")
    put.assert_called_once_with(Bucket="dst-bucket", Key="dashboards/x/a.js", Body=b"data")


def test_delete_prefix(mocker):
    mocker.patch.object(s3, "list_prefix", return_value=["dashboards/x/a.js", "dashboards/x/b.html"])
    deleted = mocker.patch.object(s3._client, "delete_object")
    assert s3.delete_prefix("dst-bucket", "dashboards/x/") == 2
    assert deleted.call_count == 2


def test_sync_prefix_copies_then_prunes_orphans(mocker):
    listed = []

    def fake_list(bucket, prefix):
        listed.append((bucket, prefix))
        if prefix == "publications/x/":
            return ["publications/x/a.js", "publications/x/b.html"]
        return ["dashboards/x/a.js", "dashboards/x/stale.js"]

    mocker.patch.object(s3, "list_prefix", side_effect=fake_list)
    copy = mocker.patch.object(s3._client, "copy_object")
    deleted = mocker.patch.object(s3._client, "delete_object")
    n = s3.sync_prefix("publications/x/", "dst-bucket", "dashboards/x/")
    assert n == 2
    assert copy.call_count == 2
    deleted.assert_called_once_with(Bucket="dst-bucket", Key="dashboards/x/stale.js")
    assert sum(1 for _, p in listed if p == "publications/x/") == 1


def test_publications_store_exposes_correct_prefix():
    from web import s3

    assert s3.publications.prefix == "publications/"
    assert s3.publications.key("foo/bar.json") == "publications/foo/bar.json"


def test_publications_store_uses_same_client_as_interactive():
    from web import s3

    # Same module-level boto client; we share credentials and bucket.
    assert s3.publications.__class__ is s3.interactive.__class__
