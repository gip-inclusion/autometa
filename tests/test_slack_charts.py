"""Graphiques des extraits Slack : dessinés et déposés une fois, montrés en image, nommés sinon."""

import pytest
from slack_sdk.errors import SlackApiError, SlackRequestError

from web import slack_charts

CHART = {"type": "chart", "source": "pie title Parts", "title": "Parts"}
TEXT = {"type": "section", "text": {"type": "plain_text", "text": "Avant."}}


@pytest.fixture(autouse=True)
def no_files(monkeypatch):
    monkeypatch.setattr(slack_charts, "files", {})


def slack(mocker, file_id="F0TEST"):
    web = mocker.MagicMock()
    web.files_upload_v2.return_value = {"files": [{"id": file_id}]}
    return web


def test_a_chart_not_yet_in_slack_is_named(mocker):
    assert slack_charts.shown([TEXT, CHART], images=True) == [
        TEXT,
        {"type": "section", "text": {"type": "plain_text", "text": "Graphique : Parts", "emoji": False}},
    ]
    assert slack_charts.shown([CHART | {"title": ""}], images=True)[0]["text"]["text"] == "Graphique"


def test_a_drawn_chart_is_deposited_as_a_file_of_the_app_and_shown_as_an_image(mocker):
    render = mocker.patch.object(slack_charts.mermaid_png, "render", return_value=b"\x89PNG")
    web = slack(mocker)

    assert slack_charts.deposit(web, CHART["source"]) is True

    render.assert_called_once_with("pie title Parts")
    sent = web.files_upload_v2.call_args.kwargs
    assert sent["content"] == b"\x89PNG"
    assert not {"channel", "channels", "channel_id"} & set(sent)
    assert slack_charts.shown([CHART], images=True) == [
        {
            "type": "image",
            "slack_file": {"id": "F0TEST"},
            "alt_text": "Parts",
            "title": {"type": "plain_text", "text": "Parts"},
        }
    ]
    assert slack_charts.shown([CHART | {"title": ""}], images=True)[0] == {
        "type": "image",
        "slack_file": {"id": "F0TEST"},
        "alt_text": "Graphique",
    }
    assert slack_charts.shown([CHART], images=False)[0]["text"]["text"] == "Graphique : Parts"


def test_a_chart_already_deposited_is_neither_drawn_nor_sent_again(mocker):
    render = mocker.patch.object(slack_charts.mermaid_png, "render", return_value=b"\x89PNG")
    web = slack(mocker)

    slack_charts.deposit(web, CHART["source"])

    assert slack_charts.deposit(web, CHART["source"]) is False
    assert render.call_count == 1
    assert web.files_upload_v2.call_count == 1


def test_a_chart_that_cannot_be_drawn_is_not_sent(mocker):
    mocker.patch.object(slack_charts.mermaid_png, "render", return_value=None)
    web = slack(mocker)

    assert slack_charts.deposit(web, CHART["source"]) is False
    web.files_upload_v2.assert_not_called()
    assert slack_charts.shown([CHART], images=True)[0]["type"] == "section"


def test_a_huge_chart_source_is_not_given_to_the_browser(mocker):
    render = mocker.patch.object(slack_charts.mermaid_png, "render")

    assert slack_charts.deposit(slack(mocker), "A-->B\n" * 4000) is False
    render.assert_not_called()


def refusal(mocker):
    return SlackApiError("refused", mocker.MagicMock(get=lambda key: "missing_scope"))


@pytest.mark.parametrize(
    "error,logged",
    [
        ("refusal", "envoi refusé : missing_scope"),
        (SlackRequestError("Failed to upload a file (status: 500)"), "envoi impossible : Failed to upload"),
        (TimeoutError("timed out"), "envoi impossible : timed out"),
    ],
)
def test_a_failed_upload_is_logged_with_what_slack_said_and_leaves_the_chart_named(mocker, caplog, error, logged):
    mocker.patch.object(slack_charts.mermaid_png, "render", return_value=b"\x89PNG")
    web = slack(mocker)
    web.files_upload_v2.side_effect = refusal(mocker) if error == "refusal" else error

    assert slack_charts.deposit(web, CHART["source"]) is False
    assert logged in caplog.text
    assert slack_charts.files == {}


def test_the_memory_of_deposited_charts_stays_bounded(mocker):
    mocker.patch.object(slack_charts.mermaid_png, "render", return_value=b"\x89PNG")
    web = slack(mocker)

    for rank in range(1200):
        slack_charts.deposit(web, f"pie title {rank}")

    assert len(slack_charts.files) <= 500


def test_two_charts_with_different_sources_never_share_a_file(mocker):
    mocker.patch.object(slack_charts.mermaid_png, "render", return_value=b"\x89PNG")
    web = slack(mocker)
    web.files_upload_v2.side_effect = [{"files": [{"id": "F1"}]}, {"files": [{"id": "F2"}]}]

    slack_charts.deposit(web, "pie title A")
    slack_charts.deposit(web, "pie title B")

    shown = slack_charts.shown([CHART | {"source": "pie title A"}, CHART | {"source": "pie title B"}], images=True)
    assert [block["slack_file"]["id"] for block in shown] == ["F1", "F2"]
