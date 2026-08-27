# Intégration Tally

Document de conception. Tally (tally.so) est un outil de formulaires/sondages. Les instances Autometa disposent d'une clé API vers leur compte Tally. Objectif : utiliser les réponses de formulaires comme **source de données** pour l'analyse et les tableaux de bord, au même titre que Matomo, Metabase ou RPE.

Ce document décrit le **quoi** et le **pourquoi**, par phases. Le code reste la référence d'implémentation.

## État des décisions

| Sujet | Décision |
|---|---|
| Modélisation de la source | **Source unique** (une clé, pas d'instances), comme `livestorm`. Le workspace est un **argument runtime**, pas une instance. |
| Pattern client | Comme `lib/rpe.py` : un `TallyClient` utilisé **directement** par le skill ; signaux émis dans le client. Pas de façade `lib.query` (réservée aux sources SQL/Matomo/Metabase). |
| Première étape | Skill **lecteur**, lecture seule, **sans persistance**. |
| Schéma de cache (phase 2) | `dashboard_storage` (comme `lib/rpe.py`), accessible aux TDB via `/api/query`. |
| Architecture de cache (phase 2) | Deux colonnes stables (`raw_json` + snapshot de schéma) + **vues** par formulaire. Pas de table EAV physique. |
| Synchronisation (phase 2) | Cron régulier **ou** rafraîchissement paresseux avant requête. Allowlist de formulaires. |
| Écriture de formulaires (`PATCH`) | Phase ultérieure, sous garde explicite. |
| Webhooks | Phase ultérieure, en **déclencheur** et non en transport de données. |

## Surface de l'API Tally

- Base `https://api.tally.so`, authentification **Bearer** (`Authorization: Bearer tly-…`).
- **Limite : 100 requêtes/minute.** La doc recommande les webhooks plutôt que le polling intensif.
- Endpoints utiles :
  - `GET /forms` — liste (pagination `page`/`limit` max 500 ; filtre `workspaceIds[]`). Chaque formulaire porte `id`, `name`, `workspaceId`, `status` (`BLANK|DRAFT|PUBLISHED|DELETED`), `numberOfSubmissions`, `isClosed`, `createdAt`, `updatedAt`.
  - `GET /forms/{id}/questions` — schéma courant.
  - `GET /forms/{id}/submissions` — réponses, paginées par `page`/`limit` **ou** curseur `afterId` ; filtres `filter=all|completed|partial`, `startDate`/`endDate` (ISO 8601). La réponse **embarque à la fois** `questions[]` (schéma courant) et `submissions[].responses[]` (réponses indexées par `questionId`, dont le type de `answer` **varie selon le type de champ**).
  - `PATCH /forms/{id}` — modification (phase ultérieure).
  - CRUD `webhooks` (phase ultérieure).

### Portée de la clé API — **point de sécurité**

La clé est liée à un **compte utilisateur**, pas à un workspace ni à l'organisation. Elle agit *au nom de cet utilisateur* et hérite de ses permissions : elle voit **tous les workspaces dont ce compte est membre**, au rôle de ce compte, et cesse de fonctionner si l'utilisateur est retiré de l'organisation.

Conséquence : le rayon d'action de la clé est « tout ce que ce compte peut lire ». C'est pour cette raison que l'audit et la confidentialité (cf. plus bas) sont structurants dès qu'on persiste des données. C'est aussi pourquoi le workspace est un argument de filtrage runtime — le skill rend ce rayon **visible** dès la phase 1.

## Architecture cible et réutilisation

L'analogue le plus proche existe déjà : `lib/rpe.py` (API externe → client dédié → skill direct) et `lib/webinaires.py` (sync d'un outil de formulaires tiers → DB). `livestorm` fournit le patron d'une source à simple clé API.

| Préoccupation | Réutilisation | Note |
|---|---|---|
| Client HTTP | `lib/matomo.py`, `GristClient` | `httpx.Client(transport=HTTPTransport(retries=2))`, `timeout=` explicite, header Bearer. |
| Config / clé | `livestorm` | Bloc `tally:` dans `config/sources.yaml`, `TALLY_API_KEY` lu via `web/config.py`. |
| Observabilité | `lib/api_signals.py` | `emit_api_signal(source="tally", …)` émis dans le client (n'imprime qu'en contexte conversation agent). |
| Selftest | `_check_livestorm` | `_check_tally` ping `GET /forms?limit=1`, enregistré dans `_check_specs`. |
| Cache (phase 2) | `lib/rpe.py` (`dashboard_storage`) | Tables hors Alembic, `MetaData(schema="dashboard_storage")` + `create_all`. |
| Sync cron (phase 2) | `cron/refresh-rpe/` | `cron/sync-tally/` appelant `lib.tally.sync()`. |
| Skill | `skills/rpe/` | `skills/tally/` (`SKILL.md` + `scripts/query.py`), importe `TallyClient` directement. |

## Phase 1 — Skill lecteur (lecture seule, sans persistance)

Périmètre : `lib/tally.py` (`TallyClient`) + `skills/tally/` (SKILL.md + `scripts/query.py`). **Aucune écriture DB.** Appels live uniquement.

Commandes :

- `--workspaces` — workspaces visibles par la clé (dérivés des `workspaceId` distincts de la liste des formulaires — rend le rayon d'action **visible**).
- `--list [--workspace W]` — formulaires : id, nom, workspace, statut, `numberOfSubmissions`. Le filtre workspace est appliqué côté client (évite de parier sur l'encodage de `workspaceIds[]`).
- `--schema FORM` — `questions[]` courant avec types et uuid. **Limite assumée** : sans persistance, pas d'historique, donc schéma **courant** seulement — la détection de drift est une fonctionnalité de la phase 2.
- `--submissions FORM [--filter --since --until --limit --max-pages]` — fetch paginé, sortie JSON. **Pagination auto plafonnée avec avertissement** (`MAX_SUBMISSION_PAGES`) pour ne pas épuiser silencieusement le budget 100/min sur un formulaire volumineux.

Posture limites : `httpx` avec `retries=2`, timeout explicite.

Observabilité dès cette phase : chaque appel émet `emit_api_signal(source="tally", …)` → la sidebar de l'agent montre chaque formulaire consulté. Traçabilité **côté lecture** sans persistance.

## Phase 2 — Persistance

### Le problème central : la dérive de schéma

Les formulaires Tally mutent (champs ajoutés, supprimés, renommés, retypés) **sans numéro de version**. Une table large « une colonne par question » casse au premier remaniement (chaque édition = une migration impossible à mener proprement sur un schéma hors Alembic, et un renommage est indiscernable d'un suppression+ajout). On retient donc :

- **`raw_json` (JSONB)** comme **source de vérité** des réponses — à l'abri de la dérive, aucune DDL à l'écriture.
- **Snapshot de schéma** (`tally_questions`) — historique : chaque sync upsert le `questions[]` courant ; un champ disparu garde sa ligne avec un `last_seen_at` figé. Rend la dérive **observable** et fournit la table de correspondance stable des identités.
- **Vues par formulaire** dérivées du JSONB, régénérées à partir du `questions[]` courant à chaque sync — colonnes typées de qualité « tableau de bord ».

La dérive frappe une **vue**, pas des données stockées : régénérer une vue est non destructif et gratuit. On obtient l'ergonomie de requête de la table large **et** la résistance à la dérive du JSONB, sans l'explosion de lignes ni la DDL runtime sur les données. Pas de table EAV physique.

### Schéma (illustratif)

```
tally_submissions(id, form_id, is_completed, submitted_at, respondent_id, raw_json JSONB, synced_at)
tally_questions(form_id, question_id, field_uuid, type, title, position, first_seen_at, last_seen_at)
tally_sync_meta(form_id, last_submission_id, last_synced_at, …)     -- curseur
tally_sync_log(form_id, started_at, rows_imported, triggered_by, …) -- audit des imports

CREATE VIEW tally_form_<id> AS
  SELECT id, submitted_at,
         raw_json->>'f_region'        AS region,
         (raw_json->>'f_score')::int  AS score
  FROM tally_submissions WHERE form_id = '<id>';
```

`raw_json` est **clé par identité stable** (`field_uuid`/`questionId`), **jamais par titre**. C'est ce qui rend les renommages gratuits.

### Deux identités

1. **Identité de stockage** — la clé sous laquelle une réponse vit dans `raw_json`. Doit être le `field_uuid`/`questionId` stable de Tally.
2. **Identité de présentation** — la colonne de sortie (nom + type) de la vue régénérée. C'est ce que voit le moteur de requête, recalculé à chaque sync.

Le moteur ne connaît que (2). La continuité de l'historique vient de (1) restant stable.

### Scénarios de dérive

| Scénario | Stockage (`raw_json`) | Lignée (uuid) | Colonne vue (moteur) |
|---|---|---|---|
| Renommage | inchangé | **identique** | identique si la vue est nommée sur l'uuid ; **se scinde** en deux si nommée sur le titre. |
| Retypage (text→number/email) | clé identique, valeur éventuellement coercée | **identique** | même nom, **nouveau cast** ; valeurs historiques au bord peuvent passer à NULL. |
| Ajout | nouvelle clé | nouvelle | nouvelle colonne, historique NULL avant `first_seen_at`. |
| Suppression | clé persiste dans les anciennes lignes | retirée | retirée **ou** conservée-NULL, au choix à la régénération (réversible : le stockage est intact). |

### Spectre de matérialisation

Vue simple (zéro stockage, re-parse JSONB par requête) → **vue matérialisée** (colonnes typées précalculées, rafraîchies au sync, indexables comme une vraie table) → table large « authored » (même forme mais destructive à la dérive, DDL runtime). La conception JSONB permet de se placer au premier ou deuxième cran, par formulaire. La vue matérialisée **est** la table large par formulaire, mais *dérivée* (régénérable, non destructive) plutôt qu'*écrite*.

### Synchronisation : cron régulier ou paresseux

- **Cron** : `cron/sync-tally/` parcourt les formulaires de l'allowlist, sync incrémentale via `afterId` (`filter=completed` pour le dataset d'analyse). La fraîcheur est un **réglage** (nocturne → 15 min reste trivial sur la limite de débit), pas un mur.
- **Paresseux** : « si ce formulaire (allowlisté) est périmé, lancer sa sync incrémentale puis requêter ». Réutilise le **même** chemin de code que le cron.
- **Re-sync complète** disponible en option quand le `questions[]` change et qu'on veut re-projeter l'historique depuis `raw_json`.

Chaque sync (cron ou paresseuse) écrit une ligne `tally_sync_log` → pas d'angle mort d'audit.

### Allowlist — ne pas tout synchroniser

La clé pouvant lire tout ce que le compte voit, « tout synchroniser » importerait des données non destinées à l'analyse. La persistance ne sync **qu'un ensemble explicite** de formulaires/workspaces.

## Phase 3 — Écriture de formulaires (`PATCH`)

Capacité **distincte, ultérieure, sous garde**. Écrire dans un instrument de collecte en production peut corrompre des réponses live ou casser les syncs en aval. À traiter comme une zone critique : confirmation explicite, étape dry-run/diff. Livrer la lecture d'abord.

## Phase 4 — Webhooks

Optimisation de latence, **pas** un remplacement du poller (backfill et réconciliation restent poll-only). Si un besoin temps réel concret apparaît **et** qu'un ingress public authentifié existe, ajouter les webhooks en **déclencheur** (« le formulaire X a de nouvelles données, lance sa sync ») réutilisant le chemin de sync unique. Ne jamais laisser le payload webhook devenir un second parseur/écrivain.

## Observabilité, audit, confidentialité

- **Formulaires consultés** : `emit_api_signal` dès la phase 1 (sidebar agent).
- **Formulaires importés** : n'a de sens qu'avec la persistance ; `tally_sync_log` (quoi/quand/combien/déclencheur) en est la trace.
- **RGPD / données personnelles** : dans le contexte IAE, les réponses sont très probablement des données personnelles (emails, noms, situations de candidats). La phase de persistance hérite donc de questions de rétention et d'accès : ce qu'on a le droit de stocker dans `dashboard_storage`, combien de temps, qui peut requêter. À cadrer au moment de la persistance.

## À vérifier avant de figer le schéma (phase 2)

**Tally préserve-t-il le `field_uuid` lors d'un changement de type ?** Si l'éditeur implémente « changer le type » comme *supprimer + recréer*, le retypage dégénère en suppression+ajout, la lignée casse, et « retypage = même colonne » devient faux. Non précisé par la doc publique — propriété empirique à tester sur un formulaire jetable (changer le type d'un champ, comparer l'uuid avant/après). Élément le plus structurant restant.

## Récapitulatif des fichiers

| Fichier | Phase | Rôle |
|---|---|---|
| `lib/tally.py` | 1 | Client `httpx` (+ phase 2 : logique de sync). |
| `config/sources.yaml` (bloc `tally`) + `web/config.py` (`TALLY_API_KEY`) | 1 | Clé API. |
| `web/selftest.py` (`_check_tally`) | 1 | Sonde de connectivité. |
| `skills/tally/SKILL.md` + `scripts/query.py` | 1 | Skill lecteur. |
| Tables `dashboard_storage` (`tally_*`) | 2 | Cache + snapshot + sync_meta + sync_log. |
| `cron/sync-tally/` (`CRON.md` + `cron.py`) | 2 | Sync périodique. |
| `tests/test_tally.py` | 1+ | Couverture client et sync. |
</content>
