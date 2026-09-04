---
name: datadog_logs
description: Lire les logs applicatifs Datadog (site EU) — compter, échantillonner, agréger par facette, ou dumper en masse pour analyse locale. Lecture seule. À utiliser dès qu'une question porte sur le comportement réel d'une application en production que Matomo ne voit pas : paramètres d'URL, filtres, codes HTTP, vues Django, utilisateurs connectés.
---

# Datadog Logs — lecteur des logs applicatifs

Accès **lecture seule** à l'API Logs de Datadog (`api.datadoghq.eu`). Complète Matomo : là où Matomo décrit le parcours déclaré côté navigateur, Datadog décrit la **requête réellement reçue par le serveur**, query string comprise.

## Portée de la clé — à savoir

Le jeton est **strictement limité à la lecture des logs** (permission `logs_read_data`). Vérifié par sondage : recherche et agrégation répondent 200 ; métriques, dashboards, monitors, hosts, APM, incidents, synthetics, SLO, utilisateurs, facturation **et même la configuration des logs** (index, pipelines) renvoient 403. La clé ne peut pas non plus s'introspecter, donc cette liste est empirique, pas déclarative.

## Limites

- **Rétention : 30 jours.** `now-60d` et `now-90d` renvoient exactement les mêmes totaux que `now-30d` — il n'y a rien de plus ancien. Le client refuse `--days > 30` plutôt que de mentir.
- **Débit : 3 requêtes / 10 s** (~1 080/h), quota `logs_public_search_api`, **global à l'org**. Le client se cale dessus avec un token bucket partagé ; augmenter `--workers` ne va pas plus vite, ça évite seulement de laisser le quota inutilisé. Ordre de grandeur : ~1 000 événements par requête, donc **~16 min pour 300 000 événements**.
- **Lecture seule, sans persistance.** Chaque commande appelle l'API. Pour une analyse répétée, faire `--dump` une fois et travailler sur le fichier.

## Commandes

```bash
# Combien d'événements, et combien d'utilisateurs distincts
.venv/bin/python skills/datadog_logs/scripts/query.py \
    --query 'service:itou-prod @http.method:GET' --days 7 --distinct '@usr.id'

# Échantillon d'événements bruts (pour découvrir la forme des logs)
.venv/bin/python skills/datadog_logs/scripts/query.py \
    --query 'service:itou-prod' --days 1 --search --limit 5

# Répartition par facette (une ou plusieurs)
.venv/bin/python skills/datadog_logs/scripts/query.py \
    --query 'service:itou-prod @http.status_code:200' --days 7 \
    --group-by '@http.url_details.view_name' --distinct '@usr.id' --top 40

# Dump massif en JSONL, pour analyser en local
.venv/bin/python skills/datadog_logs/scripts/query.py \
    --query 'service:itou-prod @usr.id:*' --days 30 --chunk 5 \
    --dump /tmp/logs.jsonl --field http.url --field usr.id
```

Sortie : JSON sur stdout. `--dump` écrit un JSONL (une ligne par événement) et renvoie un récapitulatif.

## Ce que contiennent les logs `itou-prod`

Les logs Django structurés (`django_datadog_logger`) portent, en plus du message :

| Facette | Contenu |
|---|---|
| `@http.url_details.view_name` | nom de la vue Django — identité propre de la page, préférable au chemin |
| `@http.url_details.queryString.<param>` | paramètres d'URL, **une facette par paramètre** |
| `@http.url` | **URL brute complète**, query string incluse |
| `@usr.id`, `@usr.kind` | utilisateur connecté ; `kind` vaut `job_seeker`, `professional`, `itou_staff` |
| `@usr.organization_type` | `companies.Company`, `prescribers.PrescriberOrganization`, `institutions.Institution` |
| `@http.status_code`, `@http.method`, `commitId` | code retour, verbe, et **commit déployé** |

## Pièges — tous rencontrés en vrai

**`queryString` écrase les paramètres répétés.** `?states=new&states=processing` est stocké comme `"processing"` : une seule valeur, la dernière. La présence du paramètre et le comptage par utilisateur restent justes, mais toute sélection multiple est aplatie. Dès que les **valeurs** comptent, dumper **`@http.url`** et parser en local (`urllib.parse.parse_qs`). C'est la raison d'être du champ par défaut du dump.

**La présence d'un paramètre ne vaut pas usage.** Les formulaires sérialisent tous leurs champs, vides compris : `?states=new&archived=&start_date=&end_date=`. Filtrer sur `:?*` (valeur non vide), jamais `:*`. Sur les candidatures des Emplois, l'écart était d'un facteur 40 (842 « utilisateurs » de `start_date` contre 18 réels).

**Un `group_by` non trié renvoie les N premières valeurs par ordre alphabétique**, pas les plus grosses. Le tri par volume exige `sort: {aggregation: count, order: desc, type: "measure"}` — et `type: "measure"` est **obligatoire** : sans lui l'API répond 400 « Field 'aggregation' is invalid ». Le helper `by_count()` de `lib/datadog.py` encapsule cette forme ; `--group-by` s'en sert.

**Un `group_by` écarte les événements dépourvus de la facette.** Grouper par `@usr.organization_type` fait disparaître les candidats, qui n'ont pas d'organisation — une page candidat sortait à 0 hit. Prendre les totaux dans une agrégation **sans** `group_by`, et ne se servir du `group_by` que pour la ventilation.

**Le trafic anonyme des pages publiques est massivement robotique.** Sur la recherche d'employeurs : 47 000 hits/jour depuis 2 351 IP, avec beaucoup de 429. Ajouter `@usr.id:*` pour se limiter aux utilisateurs connectés, sauf à vouloir précisément mesurer les robots.

**Le commit déployé n'est pas `master`.** `commitId` donne le SHA réellement en production. Les noms de champs d'un formulaire peuvent avoir changé depuis : lire le code avec `git show <commitId>:<fichier>`, sinon la moitié des paramètres mesurés paraissent inconnus.

## Piège applicatif : la valeur par défaut est toujours dans l'URL

Le plus coûteux, et il n'est pas côté Datadog. **Un filtre présent dans l'URL n'a pas forcément été choisi par l'utilisateur.** Trois mécanismes distincts posent une valeur sans la moindre interaction :

1. **Valeur initiale du formulaire** — `distance=25` sur la recherche d'employeurs est le `initial` du champ ; 2 029 des 3 949 « utilisateurs » du filtre ne l'ont jamais quittée.
2. **Redirection de la vue** — la liste des fiches salarié redirige vers `?status=NEW&status=REJECTED` quand aucun filtre n'est passé, d'où un taux de filtrage apparent de 100 %.
3. **Lien entrant pré-rempli** — les tuiles du tableau de bord employeur pointent sur `?states=new&states=processing`, et le menu des prolongations sur `?only_pending=on`. Ce dernier filtre tombe à **0 %** d'usage réel une fois le lien neutralisé.

Règle de comptage retenue : un contrôle n'est « utilisé » que s'il porte **au moins une valeur hors de son jeu par défaut**. Les champs obligatoires (la ville d'une recherche) et les tris sont exclus du taux de filtrage — ce sont la requête elle-même, pas un affinage. Avant de conclure quoi que ce soit sur un filtre, chercher dans le code qui construit des liens vers la page (`reverse(..., query={...})`) et les `initial=` du formulaire.

## Configuration

`DATADOG_API_KEY`, `DATADOG_APP_KEY`, et `DATADOG_SITE` (défaut `datadoghq.eu`), lues via `web/config.py`. Le client vit dans `lib/datadog.py` et peut donc servir aussi bien à un `cron.py` de tableau de bord qu'à ce CLI.
