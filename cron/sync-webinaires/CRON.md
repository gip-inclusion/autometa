---
title: Synchronisation des webinaires Grist
schedule: daily
timeout: 300
batch: grist
---

Recopie les webinaires et leurs inscriptions depuis Grist vers le datalake, et met à jour les compteurs de synchronisation.

Le code vit dans `lib/webinaires.py` ; ce dossier n'est qu'un point d'entrée pour le lanceur de crons. Le timeout de 300 s est large : la synchronisation dure une dizaine de secondes depuis l'optimisation des upserts par lots.

La tâche garde son créneau de 04:00 UTC via son propre batch, comme `sync-sites` et `sync-inventory` gardent les leurs (commit `9bb8255`). Tant qu'elle était hors du lanceur, aucun run n'était enregistré : `last_cron_success("sync-webinaires")` renvoyait toujours `None` et la source Grist s'affichait comme jamais synchronisée.
