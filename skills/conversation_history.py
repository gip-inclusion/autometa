"""Historique de l'utilisateur courant : chercher dans ses conversations, relire une conversation citée par son lien."""

import argparse
import re
import sys

from web import config
from web.database import store
from web.helpers import CONV_ID, validate_conv_id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--search", metavar="TEXT", help="Current user's conversations containing every word")
    action.add_argument("--show", metavar="LINK", help="Print a conversation from its link or its id")
    args = parser.parse_args()
    if args.search is not None and not args.search.split():
        parser.error("--search needs at least one word")

    user_email = config.agent_user_email()
    if not user_email:
        print("Error: missing env var AUTOMETA_USER_EMAIL", file=sys.stderr)
        sys.exit(2)

    if args.show:
        cited = args.show.strip()
        # Why: comme les routes de partage, une conversation ne s'ouvre que par son identifiant complet, jamais par un
        # préfixe ; 8 caractères ne la désignent que dans une de ses adresses, pas comme un mot (`datasets`) ; et une
        # adresse, sur n'importe quel site, ne compte que si elle désigne une conversation.
        ids = (
            [cited]
            if validate_conv_id(cited)
            else re.findall(rf"/(?:c/|explorations/|explorations\?conv=)({CONV_ID.pattern})(?![\w-])", cited)
        )
        conversation = next(filter(None, (store.get_conversation(i, include_messages=True) for i in ids)), None)
        if not conversation:
            print(f"Error: conversation not found: {args.show}", file=sys.stderr)
            sys.exit(1)
        print(f"# {conversation.title or 'Sans titre'} ({conversation.user_id})")
        # Why: les appels d'outils et leurs sorties noieraient les échanges, que l'agent tronque au-delà d'une taille.
        for message in (m for m in conversation.messages if m.type in ("user", "assistant", "report")):
            print(f"\n--- {message.type} {message.created_at:%Y-%m-%d %H:%M}\n{message.content}")
        return

    ids = store.search_conversation_ids_by_keyword(args.search, user_id=user_email, limit=20)
    for conversation, _ in store.list_ranked_conversations_with_tags(ids, user_id=user_email):
        if conversation.id != config.agent_conversation_id():
            print(f"{conversation.updated_at:%Y-%m-%d}  /c/{conversation.id}  {conversation.title or ''}")


if __name__ == "__main__":
    main()
