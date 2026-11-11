---
title: Faire tourner les agents
schedule: daily
timeout: 3600
batch: maintenance
---

Le seul cron des agents (skill `agents`) : aucun agent n'a de cron à lui. Pour chaque agent
actif, livre ses runs terminés depuis le passage précédent, puis, si sa cadence tombe
aujourd'hui (jours de la semaine de sa cadence), enchaîne ses préparations (connecteurs
Notion, GitHub, URL, S3, dernière sortie d'un cron existant) et ses fichiers, son run, ses
sous-agents, la livraison et le rangement dans ses fichiers. Le worker de chaque run est un conteneur
jetable : un agent est déclenché, pas allumé. Un agent en échec n'empêche pas les autres ; la
tâche sort en échec et les nomme.
