---
title: Rattraper les objets restés sans suggestion de tags
schedule: weekly
timeout: 900
---

Filet de rattrapage, **pas** un backfill. Le taguage normal se fait à la création : l'agent pose les tags des tableaux de bord et des rapports via les skills, et les conversations sont taguées par un appel court au modèle dès le premier message. Ce cron ne ramasse que ce qui est passé au travers — création sans tags, appel LLM en échec et jamais réessayé — par petits lots et sur un budget de temps.

Il écrit dans `dashboard_storage.tag_suggestions` **et pose les tags** : la trace sert à relire après coup ce que le modèle a proposé, pas à valider avant. Les termes encore « proposés » (créés depuis l'application, pas encore promus dans Notion) sont exclus du vocabulaire soumis au modèle.

Le rattrapage du corpus existant relève d'un run **autometa-jobs**, pas de ce cron : `lib.tag_suggestions.export_for_job` publie les objets à taguer comme jeu de données présigné, et `lib.tag_suggestions.ingest_job_output` réinjecte l'artefact CSV du worker après filtrage sur le vocabulaire.
