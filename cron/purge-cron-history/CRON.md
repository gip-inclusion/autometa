---
title: Purger l'historique des crons
schedule: daily
timeout: 300
batch: maintenance
---

`cron_runs` n'avait aucune rétention : jusqu'à 50 Ko de sortie par run, conservés indéfiniment. La
sortie, qui fait l'essentiel du poids, sert au diagnostic d'un échec récent : elle est vidée au-delà
de 30 jours. Statut et durée restent un an pour l'historique, puis les runs et les passages de lot
(`cron_batch_runs`) sont supprimés.
