"""Tests for lib/slack.py — Slack API helpers."""

from lib.slack import lookup_user, post_message


def test_post_message_posts_to_channel_and_returns_the_message_ts(mocker):
    post = mocker.patch("lib.slack.httpx.post")
    post.return_value.json.return_value = {"ok": True, "ts": "1700000000.000100"}

    result = post_message("tok", "C0TEST", "hello")

    assert result == "1700000000.000100"
    args, kwargs = post.call_args
    assert args[0] == "https://slack.com/api/chat.postMessage"
    assert kwargs["json"] == {"channel": "C0TEST", "text": "hello"}
    assert kwargs["headers"]["Authorization"] == "Bearer tok"
    assert kwargs["timeout"] == 10


def test_post_message_returns_none_when_not_ok(mocker):
    post = mocker.patch("lib.slack.httpx.post")
    post.return_value.json.return_value = {"ok": False, "error": "channel_not_found"}

    assert post_message("tok", "C0TEST", "hello") is None


def test_post_message_replies_in_a_thread(mocker):
    post = mocker.patch("lib.slack.httpx.post")
    post.return_value.json.return_value = {"ok": True, "ts": "2.0"}

    post_message("tok", "C0TEST", "détail", thread_ts="1.0")

    assert post.call_args.kwargs["json"] == {"channel": "C0TEST", "text": "détail", "thread_ts": "1.0"}


def test_lookup_user_returns_id_for_known_email(mocker):
    get = mocker.patch("lib.slack.httpx.get")
    get.return_value.json.return_value = {"ok": True, "user": {"id": "U999"}}

    assert lookup_user("tok", "a@b.fr") == "U999"


def test_lookup_user_returns_none_when_not_found(mocker):
    get = mocker.patch("lib.slack.httpx.get")
    get.return_value.json.return_value = {"ok": False, "error": "users_not_found"}

    assert lookup_user("tok", "a@b.fr") is None
