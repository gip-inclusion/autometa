---
title: Contexte des équipes pour la rédaction de tickets
schedule: daily
timeout: 300
batch: synchros
---

Relit chaque nuit, dans le Backlog unifié, les équipes produit actives, leurs épics actifs et
leurs titres de tickets récents, et les range dans `dashboard_storage.backlog_contexte`. Le skill
`rediger_ticket` s'en sert pour recommander l'équipe et l'épic d'un ticket sans relire Notion à
chaque conversation. Le code vit dans `lib/backlog_stockage.py`.

On y range des noms d'équipes et d'épics, et des titres de tickets (texte libre, déjà visibles de tous dans Notion).
