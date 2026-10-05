---
title: Synchronisation de l'inventaire Metabase
schedule: daily
timeout: 600
batch: synchros
---

Recopie depuis l'API Metabase l'inventaire des cartes et des tableaux de bord de chaque instance, vers les tables de cache de la base applicative.

Le code vit dans `skills/sync_metabase/scripts/sync_inventory.py` ; ce dossier n'est qu'un point d'entrée pour le lanceur de crons.

La tâche tourne dans le lot `synchros` (02:00 UTC), avec toutes les tâches qui recopient une source externe dans nos tables, avant les tableaux de bord de 06:00. Durée observée en production : de 54 s à 3 min 42 s, d'où un timeout à 600 s.

Le lot `synchros` n'a pas de budget : seul `tableaux-internes` en porte un, parce que lui seul grandit sans qu'aucun fichier du dépôt ne le borne. Un budget de lot borne d'ailleurs le *démarrage* d'une tâche, pas sa fin — la dernière lancée juste avant la limite va jusqu'au bout de son timeout.
