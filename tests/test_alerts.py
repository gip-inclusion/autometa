"""Tests for web/alerts.py — shared Slack alert helper."""

import pytest

from web import alerts, config
from web.environment import Environment


@pytest.fixture
def slack_configured(monkeypatch):
    monkeypatch.setattr(config, "SLACK_BOT_TOKEN", "tok")
    monkeypatch.setattr(config, "SLACK_ALERT_CHANNEL", "C0TEST")
    monkeypatch.setattr(config, "ENV", Environment.PROD)
    monkeypatch.setattr(config, "APP_NAME", "matometa")


def test_notify_alert_channel_posts_to_configured_channel_naming_the_app(mocker, slack_configured):
    post = mocker.patch("web.alerts.post_message", return_value=True)

    alerts.notify_alert_channel("hello world")

    post.assert_called_once_with("tok", "C0TEST", "[matometa] hello world")


@pytest.mark.parametrize("token,channel", [("", "C0TEST"), ("tok", "")])
def test_notify_alert_channel_silent_without_config(mocker, monkeypatch, slack_configured, token, channel):
    monkeypatch.setattr(config, "SLACK_BOT_TOKEN", token)
    monkeypatch.setattr(config, "SLACK_ALERT_CHANNEL", channel)
    post = mocker.patch("web.alerts.post_message", return_value=True)

    alerts.notify_alert_channel("hello")

    post.assert_not_called()


@pytest.mark.parametrize("env", [Environment.DEV, Environment.REVIEW, Environment.STAGING])
def test_notify_alert_channel_silent_off_prod(mocker, monkeypatch, slack_configured, env):
    monkeypatch.setattr(config, "ENV", env)
    post = mocker.patch("web.alerts.post_message", return_value=True)

    alerts.notify_alert_channel("hello")

    post.assert_not_called()


def test_pytest_harness_leaves_slack_unconfigured(mocker):
    """Le conftest neutralise Slack : aucune invocation de pytest ne peut poster une vraie alerte."""
    post = mocker.patch("web.alerts.post_message", return_value=True)

    alerts.notify_alert_channel("hello")

    post.assert_not_called()


def test_notify_alert_channel_swallows_slack_errors(mocker, slack_configured, caplog):
    mocker.patch("web.alerts.post_message", side_effect=RuntimeError("boom"))

    alerts.notify_alert_channel("hello")

    assert "boom" in caplog.text or "alert" in caplog.text.lower()


def test_notify_alert_channel_logs_when_delivery_fails(mocker, slack_configured, caplog):
    mocker.patch("web.alerts.post_message", return_value=False)

    alerts.notify_alert_channel("hello")

    assert "not delivered" in caplog.text.lower() or "slack" in caplog.text.lower()
