---
title: Index autometa_tables
schedule: daily
timeout: 3600
---

Recrée les index d'`autometa_tables_db` et rafraîchit les statistiques (`ANALYZE`). Les tables sont reconstruites périodiquement par le DAG `populate_matometa_db` de pilotage-airflow (`if_exists="replace"`), ce qui supprime les index ; ce cron les recrée après le chargement. La liste des index vit dans `cron.py` (`INDEXES`).

Tolérance aux pannes : chaque statement s'exécute en AUTOCOMMIT ; un échec isolé (table absente, colonne renommée) est logué sans bloquer les suivants. Le script raise en fin de run si au moins un statement a échoué — `web.cron` remonte `failure` à Sentry et Slack.

Si le DAG termine après l'heure du cron, les index de la journée ne réapparaissent qu'au run suivant (ou via un déclenchement manuel depuis `/cron`).
