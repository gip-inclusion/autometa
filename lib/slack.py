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


def member_channels(token: str) -> tuple[set[str] | None, set[str]]:
    """Ids and names of the channels the app is a member of, or None when its scopes forbid listing them, with the scopes it was granted."""
    found, cursor = set(), ""
    while True:
        data = httpx.get(
            "https://slack.com/api/users.conversations",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "types": "public_channel,private_channel",
                "exclude_archived": "true",
                "limit": 200,
                "cursor": cursor,
            },
            timeout=10,
        ).json()
        if data.get("error") == "missing_scope":
            return None, set(data.get("provided", "").split(","))
        if not data.get("ok"):
            raise RuntimeError(f"Slack refuse de lister les canaux de l'application : {data.get('error')}")
        found |= {c["id"] for c in data["channels"]} | {c["name"] for c in data["channels"]}
        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            return found, set()
