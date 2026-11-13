"""Historique de l'utilisateur courant : chercher dans ses conversations, relire une conversation citée par son lien."""

import argparse
import re
import sys

from web import config
from web.database import store

# Why: comme les routes de partage, une conversation ne s'ouvre que par son identifiant complet, jamais par un préfixe.
CONVERSATION_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--search", metavar="TEXT", help="Current user's conversations containing every word")
    action.add_argument("--show", metavar="LINK", help="Print a conversation from its link or full id")
    args = parser.parse_args()

    user_email = config.agent_user_email()
    if not user_email:
        print("Error: missing env var AUTOMETA_USER_EMAIL", file=sys.stderr)
        sys.exit(2)

    if args.show:
        match = CONVERSATION_ID.search(args.show)
        conversation = match and store.get_conversation(match.group(), include_messages=True)
        if not conversation:
            print(f"Error: conversation not found: {args.show}", file=sys.stderr)
            sys.exit(1)
        print(f"# {conversation.title or 'Sans titre'} ({conversation.user_id})")
        for message in conversation.messages:
            print(f"\n--- {message.type} {message.created_at:%Y-%m-%d %H:%M}\n{message.content}")
        return

    ids = store.search_conversation_ids_by_keyword(args.search, user_id=user_email, limit=20)
    for conversation, _ in store.list_ranked_conversations_with_tags(ids, user_id=user_email):
        if conversation.id != config.agent_conversation_id():
            print(f"{conversation.updated_at:%Y-%m-%d}  /explorations/{conversation.id}  {conversation.title or ''}")


if __name__ == "__main__":
    main()
