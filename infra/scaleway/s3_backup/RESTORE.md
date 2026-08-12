# Restaurer depuis la sauvegarde S3

`matometa-backup/mirror/` est un miroir clé-pour-clé de `matometa`. Il ne contient qu'un seul état : le dernier passage. Tout retour en arrière passe par les **versions** du bucket — un objet écrasé garde ses versions précédentes, un objet supprimé à la source garde ses versions derrière un *delete marker*. La profondeur de cet historique est fixée par `RETENTION_DAYS` (30 jours par défaut) ; au-delà, les versions sont définitivement expirées.

Le manifest du jour (`manifests/{date}.json`) atteste qu'un passage est allé au bout : `ok: true`, le nombre d'objets et la taille attendus. C'est le point de départ de toute restauration — vérifier d'abord *quel* jour est fiable.

Identifiants et endpoint : ceux de la function (`config.py`, variables `S3_*` du service Scaleway) — les mêmes que ceux du miroir, avec accès lecture sur `matometa` et écriture sur `matometa-backup`.

## Granularité réelle

Les dates portées par les versions du miroir sont celles de la **copie** (le passage de 3h), pas celles de la modification à la source. La résolution d'une restauration « à l'instant T » est donc de l'ordre de la journée, et une modification faite puis annulée entre deux passages ne laisse aucune version : elle est invisible pour la sauvegarde.

## Restaurer un objet

1. Lister les versions de la clé dans le bucket de sauvegarde (`list_object_versions`, préfixe `mirror/<clé>`). La réponse sépare `Versions` et `DeleteMarkers` : les fusionner et les trier par `LastModified` pour reconstituer la chronologie réelle.
2. Choisir l'entrée la plus récente **antérieure ou égale** à l'instant visé. Si c'est un *delete marker*, l'objet était supprimé à la source à ce moment-là.
3. Recopier cette version vers `matometa` (`copy_object` avec la source `?versionId=`).

`copy_object` échoue au-delà de 5 Go — un objet plus gros doit être repris en multipart (`upload_part_copy`). Aucun objet de cette taille n'existe aujourd'hui ; la même limite s'applique au miroir lui-même, qui le signalerait par un manifest `ok: false`.

## Restaurer le bucket à un instant T

Même logique, appliquée à toutes les clés : pour chaque clé du miroir, résoudre la version la plus récente antérieure à T, puis recopier. Les clés dont la version résolue est un *delete marker* doivent être supprimées de la source, pas recopiées — sans quoi la restauration ressuscite des objets supprimés avant T.

À faire dans un sens seulement : restaurer vers `matometa`, jamais l'inverse. Une restauration écrase la source. `matometa` est lui aussi versionné (propriété du bucket, configurée hors de cette function) : à vérifier avant de commencer, car c'est le seul filet en cas de fausse manœuvre.

## Ce qui n'est pas couvert

Le miroir vit dans le même projet Scaleway et sous les mêmes identifiants que la source : il protège d'un écrasement, d'une suppression applicative ou d'un bug de cron, pas de la perte du compte. Une copie hors projet reste à faire.

## Répétition

Une sauvegarde dont la restauration n'a jamais été exécutée est une hypothèse. À rejouer périodiquement, sur une clé de test, en vérifiant que les octets restaurés correspondent à ceux attendus — et à refaire après tout changement du handler ou de la politique de cycle de vie.
