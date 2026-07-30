---
title: Générer les embeddings des conversations
schedule: daily
timeout: 600
cron: false
---

Génère les embeddings des messages de conversation (`user`, `assistant`, `report`).

Le code est dans `cron/generate-conversation-embeddings/cron.py`. Il appelle le
générateur dans `web/conversation_embeddings/`.

Le cron ne travaille que sur les messages à traiter : ceux qui n'ont pas encore
d'embedding, ou ceux dont le contenu a changé. Il prend au plus
`EMBEDDING_CRON_LIMIT` messages par run, donc un backfill peut s'étaler sur
plusieurs nuits.

Si le job échoue, rien n'est marqué comme terminé. Les mêmes messages seront
repris au prochain run.

Ce job a sa propre ligne dans `cron.json` et tourne en conteneur `XL`.

Pour l'éteindre, ajouter `cron: false` dans ce front-matter.
