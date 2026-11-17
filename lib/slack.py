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


def post_message(token: str, channel: str, text: str, thread_ts: str | None = None) -> str | None:
    """Poste le message, en réponse au fil `thread_ts` s'il est donné ; renvoie son `ts`, ou None en cas d'échec."""
    payload = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    resp = httpx.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=10,
    )
    data = resp.json()
    return data.get("ts") if data.get("ok") else None
