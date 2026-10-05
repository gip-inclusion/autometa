"""La synchronisation des tags Notion annonce ses refus, ses rejets et les termes à valider."""

import pytest

from lib import tag_sync


def result(applied=0, rejected=(), error=None):
    return tag_sync.SyncResult(applied=applied, rejected=list(rejected), error=error)


@pytest.mark.parametrize(
    ("sync_result", "pending", "expected"),
    [
        (result(error="NOTION_TAGS_DB absent"), [], [":warning: Synchro tags Notion refusée — NOTION_TAGS_DB absent"]),
        (result(applied=2, rejected=["tag-x: facette inconnue"]), [], [":warning: Synchro tags Notion — 1 ligne(s)"]),
        (result(applied=3), [], []),
    ],
    ids=["refusee", "rejets", "silencieuse"],
)
def test_the_sync_reports_only_what_deserves_a_message(mocker, sync_result, pending, expected):
    mocker.patch.object(tag_sync, "sync_tags", return_value=sync_result)
    mocker.patch.object(tag_sync, "pending_terms", return_value=pending)
    notify = mocker.patch.object(tag_sync, "notify_alert_channel")

    tag_sync.main()

    assert [
        call.args[0][: len(prefix)] for call, prefix in zip(notify.call_args_list, expected, strict=True)
    ] == expected


def test_pending_terms_are_listed_with_a_link_to_the_notion_base(mocker):
    mocker.patch.object(tag_sync, "sync_tags", return_value=result(applied=1))
    mocker.patch.object(tag_sync, "pending_terms", return_value=[{"name": "IAE", "facet": "theme", "usages": 4}])
    mocker.patch.object(tag_sync.config, "NOTION_TAGS_DB", "https://notion.example/tags")
    notify = mocker.patch.object(tag_sync, "notify_alert_channel")

    tag_sync.main()

    message = notify.call_args.args[0]
    assert "`IAE`" in message
    assert "4 usage(s)" in message
    assert "https://notion.example/tags" in message
