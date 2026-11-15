---
title: Balayeur S3
schedule: weekly
timeout: 1800
batch: maintenance
---

Efface du bucket ce que plus rien ne référence : snapshots des publications retirées depuis plus d'un mois, fichiers déposés dont la conversation a disparu, temporaires et bytecode oubliés dans `interactive/`. Seuls les objets que rien n'a modifiés depuis un mois sont concernés, et un préfixe que la base ne référence pas du tout est laissé intact.

Tant que `S3_JANITOR_DELETE` ne vaut pas `true`, le balayeur ne fait que lister (dry run). Il ne tourne qu'en production : le bucket de staging porte aussi les fichiers des review apps, que sa base ne connaît pas. Chaque passage est rendu dans le canal d'alertes Slack, la liste des fichiers en fil. Voir `web/s3_janitor.py`.
