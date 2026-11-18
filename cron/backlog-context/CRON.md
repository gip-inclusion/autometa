---
title: Contexte des équipes pour la rédaction de tickets
schedule: daily
timeout: 300
batch: synchros
---

Relit, dans le Backlog unifié, les statuts et types de tickets, les équipes produit actives, leurs
épics actifs et leurs titres de tickets récents, et les range dans `dashboard_storage.backlog_context`. Le skill
`draft_ticket` s'en sert pour recommander l'équipe et l'épic d'un ticket sans relire Notion à
chaque conversation. Le code vit dans `lib/backlog_storage.py`.

On y range des noms de statuts, de types, d'équipes et d'épics, et des titres de tickets (texte libre, déjà visibles de tous dans Notion).
