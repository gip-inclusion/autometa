---
title: Check S3 backup
schedule: daily
timeout: 60
---

Vérifie que la Scaleway Function `s3-backup` a bien produit `matometa-backup/manifests/{today}.json` avec `ok: true`. Le manifest est écrit *en dernier* par le handler ; sa présence atteste que la passe est complète. Si le manifest manque ou rapporte un échec, le script raise — `web.cron` remonte `failure` à Sentry via `capture_checkin`.

Le bucket de sauvegarde est un miroir clé-pour-clé du bucket source : l'historique (versions précédentes, objets supprimés) vient du versioning du bucket, pas de copies datées. Voir `infra/scaleway/s3_backup/` pour la function et le provisionnement du bucket — profondeur d'historique configurable via `RETENTION_DAYS`.
