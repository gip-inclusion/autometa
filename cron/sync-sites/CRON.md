---
title: Synchronisation des baselines Matomo
schedule: daily
timeout: 300
batch: externes
---

Recopie depuis l'API Matomo les baselines, dimensions personnalisées, événements et segments des huit sites, vers les tables de cache de la base applicative. Lues ensuite par l'application (`sources_registry`, `warmup`), jamais par un autre cron.

Le code vit dans `skills/sync_sites/scripts/sync_sites.py` ; ce dossier n'est qu'un point d'entrée pour le lanceur de crons.

La tâche partage le batch `externes` avec `sync-inventory`, donc la ligne de `cron.json` à 02:00 UTC : les deux s'enchaînent dans le même conteneur. Ce n'est pas un détail d'implémentation : les tâches `sync-*` restent étalées à 02h, à l'écart de Grist (04h) et de la fenêtre de 06:00 **exprès** (commit `9bb8255`), pour ne pas empiler leur charge sur les autres lots. Passer par un batch lui donne l'historique `cron_runs`, le check-in Sentry, l'alerte Slack et le timeout, sans toucher à cet étalement. Durée observée en production : 5 à 7 s.
