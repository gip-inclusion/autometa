"""Slack API helpers: user lookup and message posting."""

import httpx


def lookup_user(token: str, email: str) -> str | None:
    resp = httpx.get(
        "https://slack.com/api/users.lookupByEmail",
        headers={"Authorization": f"Bearer {token}"},
        params={"email": email},
        timeout=10,
    )
    data = resp.json()
    return data["user"]["id"] if data.get("ok") else None


def post_message(token: str, channel: str, text: str) -> bool:
    resp = httpx.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}"},
        json={"channel": channel, "text": text},
        timeout=10,
    )
    return resp.json().get("ok", False)
