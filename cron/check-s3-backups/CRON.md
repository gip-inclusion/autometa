---
title: Check S3 backup
schedule: daily
timeout: 60
---

Vérifie que le snapshot quotidien de `matometa` a bien été poussé dans `matometa-backup/backup/{today}/` par la Scaleway Function `s3-backup`. Si le préfixe est vide ou absent, le script raise — `web.cron` remonte `failure` à Sentry via `capture_checkin`, ce qui déclenche l'alerte.

Voir `infra/scaleway/s3_backup/` pour la function qui produit le snapshot.
