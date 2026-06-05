---
title: Rafraîchir les données RPE (France Travail / DigDash)
schedule: daily
timeout: 600
---

Rafraîchit le cache du tableau de bord RPE (`pilotage-rpe.francetravail.org`) dans le schéma `matometa` : login httpx, mise à jour des cubeIds (qui tournent à chaque rebuild côté France Travail), du catalogue (datasets, dimensions, mesures) et des « données faciles » (marginales géo/temps). Voir `lib.rpe.refresh`. Échec → alerte Slack avec la cause probable (valeurs de build GWT obsolètes).
