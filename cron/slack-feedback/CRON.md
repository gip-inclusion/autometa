---
title: Sollicitation hebdomadaire de feedback sur Slack
schedule: weekly
timeout: 300
---

Envoie un DM Slack aux personnes ayant utilisé Autometa dans les sept derniers jours, avec un lien vers le formulaire Tally de retour d'expérience.

Le code vit dans `web/slack_feedback.py` ; ce dossier n'est qu'un point d'entrée pour le lanceur de crons. Le job tournait auparavant comme tâche Scalingo dédiée (`cron.json`) le lundi à 05:00 ; il passe par le batch, donc le lundi à 06:00. Scalingo plafonne `cron.json` à cinq tâches et la place libérée revient au job d'embeddings, qui a besoin d'un conteneur `XL` que le batch n'a pas.

Sans `SLACK_BOT_TOKEN`, le script sort en erreur et `web.cron` remonte l'échec à Sentry.
