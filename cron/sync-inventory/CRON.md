---
title: Synchronisation de l'inventaire Metabase
schedule: daily
timeout: 600
batch: externes
---

Recopie depuis l'API Metabase l'inventaire des cartes et des tableaux de bord de chaque instance, vers les tables de cache de la base applicative.

Le code vit dans `skills/sync_metabase/scripts/sync_inventory.py` ; ce dossier n'est qu'un point d'entrée pour le lanceur de crons.

La tâche partage le batch `externes` avec `sync-sites`, donc la ligne de `cron.json` à 02:00 UTC : les deux s'enchaînent dans le même conteneur au lieu d'empiler Matomo et Metabase sur la fenêtre de 06:00, pour les mêmes raisons d'étalement de charge que `sync-sites` (commit `9bb8255`). Durée observée en production : de 54 s à 3 min 42 s, d'où un timeout à 600 s.

Le lot `externes` n'a pas de budget : seul `tableaux` en porte un, parce que lui seul grandit sans qu'aucun fichier du dépôt ne le borne. Un budget de lot borne d'ailleurs le *démarrage* d'une tâche, pas sa fin — la dernière lancée juste avant la limite va jusqu'au bout de son timeout.
