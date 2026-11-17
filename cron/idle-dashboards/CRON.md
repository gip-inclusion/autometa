---
title: Tableaux de bord sans visite
schedule: weekly
timeout: 1800
batch: maintenance
---

Liste dans le canal d'alertes Slack les tableaux de bord créés il y a plus de 45 jours que personne n'a ouverts depuis : ni dans l'app (Matomo sur 45 jours, Datadog sur ses 30 jours de rétention), ni sur leur publication de production (Matomo). Rien n'est archivé : la liste sert à décider. Ne tourne qu'en production. Voir `web/idle_dashboards.py`.
