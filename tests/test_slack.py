"""Tests for lib/slack.py — Slack API helpers."""

import pytest

from lib.slack import RateLimited, lookup_user, member_channels, post_message


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


def test_member_channels_lists_ids_and_names_across_pages(mocker):
    get = mocker.patch("lib.slack.httpx.get")
    get.return_value.json.side_effect = [
        {"ok": True, "channels": [{"id": "C01", "name": "veille"}], "response_metadata": {"next_cursor": "p2"}},
        {"ok": True, "channels": [{"id": "G02", "name": "prive"}], "response_metadata": {"next_cursor": ""}},
    ]

    assert member_channels("tok") == ({"C01": "C01", "veille": "C01", "G02": "G02", "prive": "G02"}, set())
    assert [c.kwargs["params"]["cursor"] for c in get.call_args_list] == ["", "p2"]
    assert get.call_args.args[0] == "https://slack.com/api/users.conversations"
    assert get.call_args.kwargs["timeout"] == 10


def test_member_channels_without_the_scope_to_list_them_gives_the_scopes_granted(mocker):
    get = mocker.patch("lib.slack.httpx.get")
    get.return_value.json.return_value = {
        "ok": False,
        "error": "missing_scope",
        "needed": "channels:read",
        "provided": "chat:write,chat:write.public",
    }

    assert member_channels("tok") == (None, {"chat:write", "chat:write.public"})


def test_member_channels_rate_limited_raises_a_wait_not_a_refusal(mocker):
    get = mocker.patch("lib.slack.httpx.get")
    get.return_value.json.return_value = {"ok": False, "error": "ratelimited"}

    with pytest.raises(RateLimited):
        member_channels("tok")


def test_member_channels_raises_on_any_other_refusal(mocker):
    get = mocker.patch("lib.slack.httpx.get")
    get.return_value.json.return_value = {"ok": False, "error": "invalid_auth"}

    with pytest.raises(RuntimeError, match="invalid_auth"):
        member_channels("tok")
