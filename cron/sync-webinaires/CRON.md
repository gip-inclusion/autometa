---
title: Synchronisation des webinaires Grist
schedule: daily
timeout: 300
batch: synchros
---

Recopie les webinaires et leurs inscriptions depuis Grist vers le datalake, et met à jour les compteurs de synchronisation.

Le code vit dans `lib/webinaires.py` ; ce dossier n'est qu'un point d'entrée pour le lanceur de crons. Le timeout de 300 s est large : la synchronisation dure une dizaine de secondes depuis l'optimisation des upserts par lots.

La tâche tourne dans le lot `synchros` (02:00 UTC), avec toutes les tâches qui recopient une source externe dans nos tables. Tant qu'elle était hors du lanceur, aucun run n'était enregistré : `last_cron_success("sync-webinaires")` renvoyait toujours `None` et la source Grist s'affichait comme jamais synchronisée.
