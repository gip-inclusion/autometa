"""Rappel quotidien des PR ouvertes : backlog puis ancienneté, sans les brouillons, du lundi au vendredi."""

from datetime import date

import pytest

from web import pr_reminder

TODAY = date(2026, 11, 17)


def pr(number: int, created_at: str, labels: tuple[str, ...] = (), draft: bool = False, title: str = "") -> dict:
    return {
        "number": number,
        "title": title or f"PR {number}",
        "draft": draft,
        "author": "dev",
        "created_at": f"{created_at}T09:00:00Z",
        "labels": list(labels),
        "url": f"https://github.com/gip-inclusion/autometa/pull/{number}",
    }


def link(number: int) -> str:
    return f"<https://github.com/gip-inclusion/autometa/pull/{number}|#{number} PR {number}>"


def test_message_puts_backlog_first_then_the_oldest():
    pulls = [pr(306, "2026-11-12"), pr(258, "2026-11-10", ("backlog",)), pr(251, "2026-10-07", ("review-app",))]

    assert pr_reminder.message(pulls, TODAY) == "\n".join([
        ":eyes: 3 PR ouvertes, à traiter dans cet ordre",
        f"• {link(258)} · @dev · ouverte il y a 7 j",
        f"• {link(251)} · @dev · ouverte il y a 41 j",
        f"• {link(306)} · @dev · ouverte il y a 5 j",
    ])


def test_message_agrees_with_a_single_pull():
    assert pr_reminder.message([pr(306, "2026-11-17")], TODAY) == "\n".join([
        ":eyes: 1 PR ouverte",
        f"• {link(306)} · @dev · ouverte il y a 0 j",
    ])


def test_message_is_none_without_pulls():
    assert pr_reminder.message([], TODAY) is None


def test_message_escapes_slack_markup_in_titles():
    text = pr_reminder.message([pr(1, "2026-11-17", title="a <b> & c")], TODAY)

    assert "|#1 a &lt;b&gt; &amp; c>" in text


def test_remind_lists_every_open_pull_but_drafts(mocker):
    mocker.patch.object(
        pr_reminder.github, "pulls", return_value=[pr(1, "2026-11-01", draft=True), pr(2, "2026-11-02")]
    )
    notify = mocker.patch.object(pr_reminder, "notify_alert_channel")

    pr_reminder.remind(TODAY)

    [text] = notify.call_args.args
    assert "#2 PR 2" in text
    assert "#1 PR 1" not in text


@pytest.mark.parametrize(
    ("today", "pulls"),
    [(date(2026, 11, 21), [pr(3, "2026-11-03")]), (date(2026, 11, 22), [pr(3, "2026-11-03")]), (TODAY, [])],
)
def test_remind_posts_nothing_on_weekends_or_without_pulls(mocker, today, pulls):
    listed = mocker.patch.object(pr_reminder.github, "pulls", return_value=pulls)
    notify = mocker.patch.object(pr_reminder, "notify_alert_channel")

    pr_reminder.remind(today)

    notify.assert_not_called()
    assert listed.called is (today.weekday() < 5)
