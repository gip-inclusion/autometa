"""Demander à Autometa depuis Slack : une mention ou le raccourci ouvre une conversation, y joue un tour, répond dans le fil."""

from web.stores.records import Conversation

# L'adresse de l'espace Slack de l'application, que l'écoute lit à son démarrage ; vide tant qu'elle ne tourne pas.
workspace = {"url": ""}


def thread_url(conv: Conversation) -> str:
    """L'adresse du fil Slack d'une conversation ; celle de son canal tant que l'espace Slack n'est pas connu."""
    if not workspace["url"]:
        return f"https://slack.com/app_redirect?channel={conv.slack_channel}"
    ts = conv.slack_thread_ts or ""
    return (
        f"{workspace['url'].rstrip('/')}/archives/{conv.slack_channel}/p{ts.replace('.', '')}"
        f"?thread_ts={ts}&cid={conv.slack_channel}"
    )
