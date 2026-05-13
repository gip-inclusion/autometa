---
title: Check S3 backup
schedule: daily
timeout: 60
---

Vérifie que la Scaleway Function `s3-backup` a bien produit `matometa-backup/backup/{today}/_MANIFEST.json` avec `ok: true`. Le manifest est écrit *en dernier* par le handler ; sa présence atteste que la copie est complète (un snapshot partiel n'a pas de manifest). Si le manifest manque ou rapporte un échec, le script raise — `web.cron` remonte `failure` à Sentry via `capture_checkin`.

Voir `infra/scaleway/s3_backup/` pour la function qui produit le snapshot (retention configurable via `RETENTION_DAYS`, défaut 30 jours).
