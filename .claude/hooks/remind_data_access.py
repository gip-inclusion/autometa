#!/usr/bin/env python3
"""UserPromptSubmit hook : rappelle de vérifier l'accès réel aux sources de données avant de répondre."""

import json

MESSAGE = (
    "Garde-fou données : si cette demande s'appuie sur une source de données externe "
    "(code d'un dépôt GitHub, Matomo, Metabase, autometa_tables_db, data·inclusion, "
    "Dora staging, RPE, Notion, Zendesk, Tally, Datadog...), vérifie l'accès réel via "
    "le skill ou l'outil correspondant avant de répondre. Si l'accès ne peut pas être "
    "vérifié (source non couverte, requête en échec, dépôt ou fichier introuvable), "
    "dis-le explicitement à l'utilisateur plutôt que d'halluciner une réponse."
)


def main():
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": MESSAGE}}))


if __name__ == "__main__":
    main()
