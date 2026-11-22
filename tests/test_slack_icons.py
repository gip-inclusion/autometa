"""Icônes des Work Objects : celle du genre de l'objet, déposée une fois ; sans fichier ou sans Slack, l'objet tel quel."""

import pytest
from slack_sdk.errors import SlackApiError

from web import slack_icons

ENTITY = {
    "url": "https://autometa.example/c/0a1b2c3d",
    "external_ref": {"id": "0a1b2c3d", "type": "conversation"},
    "entity_payload": {"attributes": {"title": {"text": "Titre"}}, "fields": {}, "custom_fields": []},
}


@pytest.fixture(autouse=True)
def icons(tmp_path, monkeypatch):
    monkeypatch.setattr(slack_icons, "ICONS", tmp_path)
    monkeypatch.setattr(slack_icons, "files", {})
    return tmp_path


def slack(mocker):
    web = mocker.MagicMock()
    web.files_upload_v2.return_value = {"files": [{"id": "F0ICON"}]}
    return web


def test_without_an_image_for_its_kind_an_object_goes_as_it_is_and_nothing_is_sent_or_logged(mocker, caplog):
    web = slack(mocker)

    assert slack_icons.with_icon(web, ENTITY) is ENTITY
    web.files_upload_v2.assert_not_called()
    assert caplog.text == ""


def test_an_image_is_deposited_once_as_a_file_of_the_app_and_used_from_the_next_object_on(mocker, icons):
    (icons / "conversation.png").write_bytes(b"\x89PNG conversation")
    web = slack(mocker)

    first = slack_icons.with_icon(web, ENTITY)
    second = slack_icons.with_icon(web, ENTITY)
    third = slack_icons.with_icon(web, ENTITY)

    assert "product_icon" not in first["entity_payload"]["attributes"]
    assert second["entity_payload"]["attributes"] == {
        "title": {"text": "Titre"},
        "product_icon": {"alt_text": "Conversation", "slack_file": {"id": "F0ICON"}},
    }
    assert third == second
    assert "product_icon" not in ENTITY["entity_payload"]["attributes"]
    web.files_upload_v2.assert_called_once()
    sent = web.files_upload_v2.call_args.kwargs
    assert sent["content"] == b"\x89PNG conversation"
    assert not {"channel", "channels", "channel_id"} & set(sent)


@pytest.mark.parametrize(
    ("kind", "label"),
    [
        ("conversation", "Conversation"),
        ("dashboard", "Tableau de bord"),
        ("public_dashboard", "Tableau de bord public"),
    ],
)
def test_each_kind_of_object_has_its_own_image(mocker, icons, kind, label):
    (icons / f"{kind}.png").write_bytes(kind.encode())
    web = slack(mocker)
    entity = ENTITY | {"external_ref": {"id": "x", "type": kind}}

    slack_icons.with_icon(web, entity)
    shown = slack_icons.with_icon(web, entity)

    assert shown["entity_payload"]["attributes"]["product_icon"]["alt_text"] == label


def test_an_image_slack_refuses_leaves_the_object_as_it_is_with_one_log_line_and_is_tried_again_later(
    mocker, icons, caplog
):
    (icons / "conversation.png").write_bytes(b"image")
    web = slack(mocker)
    web.files_upload_v2.side_effect = [SlackApiError("refused", mocker.MagicMock(get={"error": "missing_scope"}.get))]

    assert slack_icons.with_icon(web, ENTITY) is ENTITY

    assert caplog.text.count("Icône Slack conversation non déposée, envoi refusé : missing_scope") == 1
    web.files_upload_v2.side_effect = None
    slack_icons.with_icon(web, ENTITY)
    assert "product_icon" in slack_icons.with_icon(web, ENTITY)["entity_payload"]["attributes"]


def test_an_image_that_changes_is_deposited_again(mocker, icons):
    (icons / "conversation.png").write_bytes(b"une")
    web = slack(mocker)
    slack_icons.with_icon(web, ENTITY)

    (icons / "conversation.png").write_bytes(b"autre")
    slack_icons.with_icon(web, ENTITY)

    assert web.files_upload_v2.call_count == 2
