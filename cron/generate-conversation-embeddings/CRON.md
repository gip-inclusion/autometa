---
title: Générer les embeddings des conversations
schedule: daily
timeout: 600
batch: xl
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

Le chargement du modèle coûte environ 1 Go, ce qui ne tient pas dans le conteneur du lot
ordinaire. D'où `batch: xl` : la tâche est exécutée par la ligne `python -m web.cron --batch xl`
de `cron.json`, qui demande un conteneur `XL`. Son échec reste ainsi isolé des autres tâches
de la nuit.

Pour l'éteindre, ajouter `cron: false` dans ce front-matter.
