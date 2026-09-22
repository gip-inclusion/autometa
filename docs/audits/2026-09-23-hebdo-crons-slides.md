---
marp: true
paginate: true
title: Crons & jobs — hebdo du 23/09
---

# Crons & jobs

Ce qui cassait, ce qui change, ce qui reste ouvert

Hebdo du 23/09 — branche `cdarnispro/audit-cron-jobs` (non commitée, non relue)

---

## `okr-q3-2026` : ce n'est pas un problème du lundi

Le conteneur du lot `default` est **tué (exit 137, SIGKILL) 10 jours sur 12 depuis le 10/09**.

| Jour | Sortie du lot `default` | Runs planifiés en base |
|---|---|---|
| 05 → 09/09 | exit 0, 36 à 64 min | ~155/jour |
| 10, 11/09 | **exit 137** après 5 min | 14 |
| 12, 13/09 | exit 0 | 163 |
| 14 → 22/09 | **exit 137** chaque jour | 6 à 16 |

- Tué pendant `autometa-releases` (10, 11, 14 → 20/09), pendant `suggest-tags` le 21/09.
- Aucune ligne `failure` : le runner meurt avec la tâche. **Tout est « success »** en base, zéro alerte Slack.
- Seuls les ~8 premiers tableaux de bord (ordre alphabétique) tournent encore : **plus de 100 sur 130** ne se rafraîchissent plus depuis le 14/09, pas seulement `okr-q3-2026`.

Sources : `scalingo logs-archives`, table `cron_runs` (lecture seule). Les chiffres de Pierre se recoupent exactement (planifiés + manuels).

---

## La cause : piste, pas diagnostic

- Lot `default` en conteneur **M (512 Mo)**. Le web tourne en **XL**.
- Les runs manuels d'`autometa-releases` (21-22/09, exécutés dans le process web) **réussissent**.
- exit 137 est la signature habituelle d'un dépassement mémoire. **Non prouvé** : aucun message OOM dans les logs.

Hebdomadaire = pas de rattrapage : un lundi raté coûte une semaine. `is_due` en heure de Paris ne pose pas de problème ici (06:00 UTC = 08:00 Paris, même jour). La branche ne change pas ce point.

---

## Et les deux orphelins échouent tous les jours

Vu en cherchant les interruptions, illustre F8 :

| Tâche | Sortie | Depuis |
|---|---|---|
| `sync-sites` | exit 1 : `UniqueViolation` sur `matomo_segments_pkey` | au moins le 03/09, chaque jour |
| `sync-webinaires` | exit 1 : `NOT NULL` violé sur `webinar_id` | au moins le 03/09, chaque jour |
| `sync-inventory` | exit 0 | |

Personne ne l'a vu : ni `cron_runs`, ni Slack, ni `/cron`.
À noter aussi : ~17 tableaux de bord échouent chaque jour, même quand le lot va au bout.

---

## Ce qui cassait (audit du 16/09, 21 constats)

```
AVANT (main)
02:00  sync-sites        ┐
03:00  sync-inventory    ├─ hors runner : pas de trace, pas d'alerte
04:00  sync-webinaires   ┘
06:00  [default, M]  8 système → 117 TDB → 38 publications
                     en série, sans budget ; une panne emporte la suite
06:00  [xl, XL]      embeddings
```

- Panne S3 = « 0 tableau de bord à rafraîchir », lot déclaré réussi (F1)
- Une exception emporte les tâches suivantes, sans trace (F2)
- Logs des tâches jamais envoyés à Datadog, stacktrace tronquée en premier (F5, F7)
- Désactiver une tâche depuis l'UI : annulé au déploiement suivant (F6)
- Run manuel exécuté dans le handler HTTP : site bloqué jusqu'à 10 min (F13)

---

## Ce qui a changé (13 constats fermés : F1 à F10, F13, F16, F19)

```
APRÈS (branche)
02:00  [externes]              sync-sites → sync-inventory
04:00  [grist]                 sync-webinaires
06:00  [systeme]               8 tâches du dépôt          ┐
06:00  [tableaux, budget 1500s] TDB → publications         ├ 3 conteneurs
06:00  [xl, XL]                embeddings                 ┘ en parallèle
```

- Isolation par tâche, ligne en base dans tous les cas, check-in Sentry fermé même sur exception
- Logs vers Datadog en direct, en JSON, avec plafond de volume ; la fin des deux flux conservée en base
- Les 12 tâches système ont un point d'entrée commun, garanti par un test structurel
- Désactivation stockée en base, conservée au déploiement ; lot inconnu = découverte en échec
- Run manuel lancé dans un conteneur one-off Scalingo, le web n'est plus bloqué
- Corrigés en route : runner qui se figeait sur un processus orphelin, jeton Scalingo transmis aux `cron.py` de TDB

---

## Ce que la branche change pour `okr-q3-2026`, sans enjoliver

Mieux :
- Tableaux de bord et tâches système séparés : le kill du 21/09 (`suggest-tags`) n'emporterait plus les TDB.
- Logs dans Datadog : l'arrêt net et la dernière tâche lancée se voient.

Pas mieux :
- `autometa-releases` est dans `tableaux`, **encore en M**. Si c'est lui, tout ce qui suit la lettre « a » saute toujours.
- Un SIGKILL du conteneur ne produit **ni `skipped` ni alerte Slack** : `skipped` ne couvre que le dépassement de budget.

Moins bien, à corriger avant fusion :
- **Budget de 1500 s trop court.** Les jours où le lot est allé au bout, TDB + publications ont pris **2150 à 3150 s**. Avec 1500 s, 28 à 52 TDB et les 38 publications seraient `skipped` chaque jour. `okr-q3-2026` démarrait à 1482 s le 07/09.
  Le design partait de « 1 à 10 min observées » : c'étaient des lots tués.
- « Prochaine exécution » (page d'un TDB) affiche 06:00 heure de Paris, alors que le départ réel est à 06:00 UTC, soit 08:00 à Paris en été.

---

## Proposé avant fusion

1. Budget du lot `tableaux` : 3600 s, ou retiré en attendant la mesure.
2. `"size"` de la ligne `tableaux` : L ou XL (une ligne de `cron.json`, coût Scalingo à vérifier).
3. Diagnostic du 137 : rejouer `autometa-releases` dans un one-off M en surveillant la mémoire. Lance un conteneur de prod, donc **accord de l'équipe d'abord**.
4. Réparer `sync-sites` et `sync-webinaires`. Le message d'erreur de `sync-webinaires` recopie les lignes insérées (e-mails d'inscrits) dans les logs.
5. Vérifier dans Sentry ce que les check-ins restés ouverts ont signalé depuis le 10/09.
6. Relecture humaine : zones critiques (`web/models.py`, `alembic/`, `web/s3.py`, `cron.json`).

---

## Ce qui reste ouvert

- Constats non traités : F11 (DDL hors Alembic), F12 (pas de rétention sur `cron_runs`), F14 (S3 séquentiel), F15 (boto3 sans timeout ni retry), F17 (`cleanup-dashboards` toujours en simulation), F18 (code mort), F20 (`limit` non borné), F21 (run manuel sans auteur), J1 à J3 (jobs).
- **La cause des kills n'est pas établie.** La branche rend une partie des pannes visible, elle n'en évite aucune.
- Branche **ni commitée ni relue** : 55 fichiers. Au 22/09 : `make lint` vert, 1969 tests unit verts. Suite avec Postgres et Redis (2810) : pas relancée depuis le dernier changement.
- Run manuel inactif tant que `SCALINGO_API_TOKEN` n'est pas posé. Jeton à créer depuis `ops.autometa@inclusion.gouv.fr`, pas depuis un compte perso : décision d'équipe.

---

## Prefect : éléments de discussion

Faits :
- `cron.json` : 5 lignes max chez Scalingo, les 5 sont prises. Relevable sur demande au support.
- Les `cron.py` des TDB sont écrits par l'agent et stockés **sur S3, hors dépôt** : ni revue ni diff. Ce problème existe quel que soit l'ordonnanceur choisi.
- L'incident actuel ressemble à un problème de mémoire : un ordonnanceur ne le résout pas, mais il le **rend visible** (run « crashed » détecté).

| | Scalingo + branche | Ordonnanceur externe (Prefect…) |
|---|---|---|
| Isolation, budget, logs Datadog, état durable | oui | oui |
| Kill du conteneur détecté | non (Sentry seulement) | oui |
| Dépendances, reprises, backfill | non | oui |
| Interface d'exploitation | `/cron` en lecture | oui |
| Coût | relecture + correctifs ci-dessus | infra à déployer et authentifier, migration de 130 `cron.py` |

---

## Options à trancher en équipe

- **A.** Fusionner la branche corrigée, rester sur Scalingo. Demander une 6e ligne au support si besoin.
- **B.** A, plus un dépôt git pour les `cron.py` de TDB (revue, diff), sans changer d'ordonnanceur.
- **C.** Pilote Prefect sur un périmètre réduit (les tableaux de bord, par exemple), comparé à A sur un mois.
- **D.** Migration complète vers un ordonnanceur externe.

Questions : qui exploite l'outil au quotidien ? Qui revoit du code généré par l'agent ? Combien vaut un rafraîchissement manqué ?
