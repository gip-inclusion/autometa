---
title: Synchronisation des baselines Matomo
schedule: daily
timeout: 300
batch: synchros
---

Recopie depuis l'API Matomo les baselines, dimensions personnalisées, événements et segments des huit sites, vers les tables de cache de la base applicative. Lues ensuite par l'application (`sources_registry`, `warmup`), jamais par un autre cron.

Le code vit dans `skills/sync_sites/scripts/sync_sites.py` ; ce dossier n'est qu'un point d'entrée pour le lanceur de crons.

La tâche tourne dans le lot `synchros` (02:00 UTC), avec toutes les tâches qui recopient une source externe dans nos tables : elles passent avant les tableaux de bord de 06:00 qu'elles alimentent, et n'empilent pas leur charge sur cette fenêtre. Durée observée en production : 5 à 7 s.
