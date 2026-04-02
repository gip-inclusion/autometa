---
name: data_inclusion
description: Query the data·inclusion datawarehouse to trace data through the dbt pipeline (staging → intermediate → marts)
---

# data·inclusion

Interroge le datawarehouse data·inclusion (PostgreSQL via tunnel SSH) pour tracer des données à travers le pipeline dbt. 110k structures, 180k services, 17 sources.

## Contexte : Dora et data·inclusion

Dora (dora.inclusion.gouv.fr) utilise l'API data·inclusion comme backend de recherche. Quand un utilisateur cherche un service sur Dora via `/recherche?...`, Dora appelle l'API data·inclusion route `/search/services`. Les résultats viennent des tables `public_marts` du datawarehouse.

Conséquence : si un service existe dans Dora mais ne remonte pas dans la recherche, c'est qu'il n'est pas (ou plus) dans le pipeline data·inclusion. Il faut remonter le pipeline pour trouver où la donnée a été perdue.

### URLs Dora

- Service : `dora.inclusion.gouv.fr/services/<slug>` — le slug identifie le service dans Dora
- Recherche : `dora.inclusion.gouv.fr/recherche?cats=<thématique>&city=<code_insee>&...` — appelle `/search/services` sur l'API data·inclusion

## Documentation

- `knowledge/data_inclusion/README.md` — architecture complète, schémas, tables, colonnes, volumes
- `lib/data_inclusion.py` — client (tunnel SSH + psycopg2)
- Code source dbt : `gip-inclusion/data-inclusion` (branche main)

## Schémas PostgreSQL

| Schéma | Contenu |
|---|---|
| `<source>` (ex: `dora`, `soliguide`) | Données JSON brutes importées par Airflow (`data` colonne jsonb) |
| `public_staging` | 143 tables `stg_<source>__*` nettoyées par dbt |
| `public_intermediate` | 140 tables `int_*` : mappings, unions, enrichissements, finals, dédup |
| `public_marts` | 22 tables `marts__*_v1` publiées |
| `public_schema` | 18 tables d'énumération (thématiques, publics, modes, typologies) |
| `public` | Tables API (events, requests, `api__search_services_events_v1`) |

## Usage

```python
from lib.query import execute_data_inclusion_query, CallerType

result = execute_data_inclusion_query(
    sql="SELECT id, source, nom FROM public_marts.marts__structures_v1 WHERE siret = '12345678901234'",
    caller=CallerType.AGENT,
)

if result.success:
    print(result.data)  # {"columns": [...], "rows": [...], "row_count": N}
```

Chaque appel ouvre un tunnel SSH, exécute la requête, et ferme tout.

## Investigation : un service Dora ne remonte pas dans la recherche

Procédure systématique. À chaque étape, si la donnée est trouvée, passer à l'étape suivante. Si absente, **c'est là que la donnée est perdue** — conclure.

**Important** : une donnée peut être présente dans les marts mais absente des résultats de recherche Dora. L'API data·inclusion applique ses propres filtres (validité, géolocalisation, rayon, thématiques, etc.) en plus du contenu des tables. Quand la donnée est dans les marts mais pas dans les résultats :
- Vérifier les flags (`_is_valid`, `_in_opendata`, `_has_valid_address`, `_is_closed`)
- Vérifier que le géocodage a un score suffisant et que les coordonnées sont cohérentes avec la commune recherchée
- Consulter le code source de l'API dans `gip-inclusion/data-inclusion` (dossier `api/`) pour comprendre les filtres appliqués par la route `/search/services` : filtrage géographique (rayon, département), filtrage par thématique, exclusions sur les flags qualité
- Consulter le code dbt (`pipeline/dbt/models/`) pour comprendre les transformations et exclusions à chaque couche

### Étape 1 — Identifier le service Dora

Depuis l'URL Dora (`/services/<slug>`), extraire le nom de la structure et/ou le nom du service. Si un code INSEE est dans l'URL de recherche (`city=<code>`), le noter.

### Étape 2 — Chercher dans les marts (ce que l'API retourne)

Par nom de structure :

```sql
SELECT id, source, nom, siret, _is_valid, _is_closed, _in_opendata, _cluster_id
FROM public_marts.marts__structures_v1
WHERE source = 'dora' AND nom ILIKE '%nom de la structure%'
```

Par code INSEE (département entier ou commune) :

```sql
SELECT s.id, s.nom, svc.id as service_id, svc.nom as service_nom, svc.thematiques
FROM public_marts.marts__structures_v1 s
JOIN public_marts.marts__services_v1 svc ON svc.structure_id = s.id
WHERE s.source = 'dora' AND svc.code_insee = '85151'
```

Par thématique dans une zone :

```sql
SELECT svc.id, svc.nom, svc.commune, s.nom as structure
FROM public_marts.marts__services_v1 svc
JOIN public_marts.marts__structures_v1 s ON s.id = svc.structure_id
JOIN public_marts.marts__services_thematiques_v1 t ON t.service_id = svc.id
WHERE t.value LIKE 'mobilite%' AND svc.code_postal LIKE '85%'
```

**Si absent des marts** → la donnée a été perdue en amont. Continuer.

### Étape 3 — Chercher dans les finals intermediate

```sql
SELECT id, source, nom, adresse_id, _is_valid, _is_closed
FROM public_intermediate.int__structures_v1
WHERE source = 'dora' AND nom ILIKE '%nom de la structure%'
```

Si présent avec `_is_valid = false` :

```sql
SELECT resource_type, type, loc, msg, input
FROM public_intermediate.int__erreurs_validation_v1
WHERE id = 'dora--<uuid>'
```

### Étape 4 — Chercher dans le staging dbt

```sql
SELECT id, nom, lien_source
FROM public_staging.stg_dora__structures
WHERE nom ILIKE '%nom de la structure%'
```

```sql
SELECT id, nom, structure_id, lien_source
FROM public_staging.stg_dora__services
WHERE nom ILIKE '%nom du service%'
```

### Étape 5 — Chercher dans les données brutes Airflow

Les données brutes sont stockées en jsonb dans la colonne `data` :

```sql
SELECT data->>'name' as nom, data->>'slug' as slug, data->>'siret' as siret
FROM dora.structures
WHERE data->>'name' ILIKE '%nom de la structure%'
LIMIT 10
```

```sql
SELECT data->>'name' as nom, data->>'slug' as slug, data->>'structure' as structure_id
FROM dora.services
WHERE data->>'name' ILIKE '%nom du service%'
LIMIT 10
```

**Si absent des données brutes** → le DAG Airflow n'a pas importé cette donnée depuis l'API Dora. C'est un problème d'import en amont du pipeline dbt.

### Étape 6 — Vérifier la déduplication

```sql
SELECT d.cluster_id, d.structure_id, d.score, d.size, s.nom, s.source
FROM public_intermediate.int__doublons_structures_v1 d
JOIN public_intermediate.int__structures_v1 s ON s.id = d.structure_id
WHERE d.cluster_id = (
    SELECT cluster_id FROM public_intermediate.int__doublons_structures_v1
    WHERE structure_id = 'dora--<uuid>'
)
```

### Étape 7 — Vérifier le géocodage

```sql
SELECT g.*, s.adresse, s.code_postal, s.commune
FROM public_intermediate.int__geocodages_v1 g
JOIN public_intermediate.int__structures_v1 s ON g.adresse_id = s.adresse_id
WHERE s.id = 'dora--<uuid>'
```

### Étape 8 — Vérifier le SIRET

```sql
SELECT siret, statut, date_fermeture, siret_successeur
FROM public_intermediate.int__sirets_v1
WHERE siret = '<siret>'
```

## Recherche par critères

### Par SIRET

```sql
SELECT id, source, nom, _is_valid, _is_closed
FROM public_marts.marts__structures_v1
WHERE siret = '12345678901234'
```

### Par nom (recherche floue)

```sql
SELECT id, source, nom, siret, commune
FROM public_marts.marts__structures_v1
WHERE nom ILIKE '%mot-clé%'
LIMIT 20
```

### Par commune (code INSEE)

```sql
SELECT id, source, nom, siret
FROM public_marts.marts__structures_v1
WHERE code_insee = '75056'
```

### Services d'une structure

```sql
SELECT s.id, s.nom, s.thematiques, s.score_qualite, s._is_valid
FROM public_marts.marts__services_v1 s
WHERE s.structure_id = 'dora--<uuid>'
```

### Thématiques d'un service (via table de jonction)

```sql
SELECT t.value, th.label
FROM public_marts.marts__services_thematiques_v1 t
JOIN public_schema.thematiques_v1 th ON th.value = t.value
WHERE t.service_id = 'dora--<uuid>'
```

### Compter les services d'une source dans un département

```sql
SELECT count(*), array_agg(DISTINCT commune ORDER BY commune)
FROM public_marts.marts__services_v1
WHERE source = 'dora' AND code_postal LIKE '85%'
```

### Lister les valeurs d'une énumération

```sql
SELECT value, label FROM public_schema.thematiques_v1 ORDER BY value
SELECT value, label FROM public_schema.publics_v1 ORDER BY value
SELECT value, label FROM public_schema.typologies_de_structures ORDER BY value
```

## Diagnostic qualité

### Erreurs de validation par source

```sql
SELECT source, resource_type, count(*) as nb
FROM public_intermediate.int__erreurs_validation_v1
GROUP BY source, resource_type
ORDER BY nb DESC
```

### Taux de validité par source

```sql
SELECT source,
       count(*) as total,
       count(*) FILTER (WHERE _is_valid) as valides,
       round(100.0 * count(*) FILTER (WHERE _is_valid) / count(*), 1) as pct
FROM public_marts.marts__structures_v1
GROUP BY source
ORDER BY pct
```

### Géocodage — score par source

```sql
SELECT s.source,
       count(*) as total,
       round(avg(g.score)::numeric, 2) as score_moyen,
       count(*) FILTER (WHERE g.score < 0.5) as mauvais
FROM public_intermediate.int__structures_v1 s
LEFT JOIN public_intermediate.int__geocodages_v1 g ON g.adresse_id = s.adresse_id
GROUP BY s.source
ORDER BY score_moyen
```

### Doublons inter-sources

```sql
SELECT source_1, source_2, nb_1, nb_2, percent_1, percent_2
FROM public_intermediate.int__doublons_nb_cross_source_v1
ORDER BY nb_1 DESC
```

### Structures fermées par source

```sql
SELECT source, count(*) as fermees
FROM public_marts.marts__structures_v1
WHERE _is_closed
GROUP BY source
ORDER BY fermees DESC
```

## Tables de référence

### Sources disponibles

```sql
SELECT source, count(*) as structures
FROM public_marts.marts__structures_v1
GROUP BY source ORDER BY structures DESC
```

### Communes (découpage administratif)

```sql
SELECT code, nom, code_departement, code_region
FROM public_staging.stg_decoupage_administratif__communes
WHERE code = '75056'
```

### SIRENE (établissements — attention : 3.7 GB)

```sql
SELECT siret, etat_administratif_etablissement
FROM public_staging.stg_sirene__stock_etablissement
WHERE siret = '12345678901234'
```
