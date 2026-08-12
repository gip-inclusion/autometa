---
title: Synchroniser le vocabulaire de tags depuis Notion
schedule: daily
timeout: 120
---

Recopie la base Notion « Gestion des tags » dans la table `tags` — sens unique, Notion fait foi sur le vocabulaire, la base sur les assignations. Voir `lib.tag_sync.sync_tags`. Les lignes invalides (facette inconnue, slug vide, doublon) sont rejetées et remontées sur Slack sans bloquer les autres. Un fetch vide ou anormalement réduit est refusé : le vocabulaire reste inchangé.

Signale aussi sur Slack les termes proposés depuis l'application et encore en attente : la relecture et la promotion se font dans Notion, ajouter la ligne suffit — la synchro suivante l'adopte par son slug et retire l'état « proposé ».
