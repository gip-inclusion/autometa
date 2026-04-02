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

## Colonnes des tables brutes (schéma `dora`)

Les données brutes sont en jsonb (colonne `data`). Accès via `data->>'field'`. **Ne pas faire de requêtes information_schema** — les colonnes sont documentées ici.

**dora.services** (44 clés) : id, nom, source, structure_id, lien_source, date_maj, date_creation, date_suspension, presentation_resume, presentation_detail, adresse, complement_adresse, commune, code_postal, code_insee, latitude, longitude, telephone, courriel, contact_nom_prenom, contact_public, thematiques, types, publics, publics_precisions, profils, modes_accueil, modes_orientation_accompagnateur, modes_orientation_accompagnateur_autres, modes_orientation_beneficiaire, modes_orientation_beneficiaire_autres, frais, frais_autres, justificatifs, pre_requis, cumulable, formulaire_en_ligne, prise_rdv, recurrence, zone_diffusion_type, zone_diffusion_code, zone_diffusion_nom, temps_passe_duree_hebdomadaire, temps_passe_semaines.

**dora.structures** (27 clés) : id, nom, source, siret, parent_siret, rna, lien_source, date_maj, presentation_resume, presentation_detail, adresse, complement_adresse, commune, code_postal, code_insee, latitude, longitude, telephone, courriel, site_web, horaires_ouverture, accessibilite, typologie, thematiques, labels_nationaux, labels_autres, antenne.

## Performance

Chaque requête ouvre un tunnel SSH (~200ms overhead). Pour minimiser les allers-retours :
- **Combiner plusieurs SELECT dans une seule requête** plutôt que de faire des requêtes séparées
- **Ne jamais interroger information_schema** — les schémas sont documentés dans `knowledge/data_inclusion/README.md`
- Aller directement aux tables pertinentes plutôt que d'explorer

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

## Investigation : un service Dora ne remonte pas dans la recherche

Procédure systématique. À chaque étape, si la donnée est trouvée, passer à l'étape suivante. Si absente, **c'est là que la donnée est perdue** — conclure.

**Important** : une donnée peut être présente dans les marts mais absente des résultats de recherche Dora. L'API data·inclusion applique ses propres filtres (validité, géolocalisation, rayon, thématiques, etc.) en plus du contenu des tables. Quand la donnée est dans les marts mais pas dans les résultats :
- Vérifier les flags (`_is_valid`, `_in_opendata`, `_has_valid_address`, `_is_closed`)
- Vérifier que le géocodage a un score suffisant et que les coordonnées sont cohérentes avec la commune recherchée
- Consulter le code source de l'API dans `gip-inclusion/data-inclusion` (dossier `api/`) pour comprendre les filtres appliqués par la route `/search/services` : filtrage géographique (rayon, département), filtrage par thématique, exclusions sur les flags qualité
- Consulter le code dbt (`pipeline/dbt/models/`) pour comprendre les transformations et exclusions à chaque couche

### Étape 1 — Identifier le service Dora

Depuis l'URL Dora (`/services/<slug>`), extraire le nom de la structure et/ou le nom du service. Si un code INSEE est dans l'URL de recherche (`city=<code>`), le noter.

### Étape 2 — Trace rapide (une seule requête)

Lancer cette requête combinée en premier pour savoir immédiatement à quel niveau la donnée se trouve ou disparaît. Adapter le filtre (`nom ILIKE`, `code_postal LIKE`, etc.) selon le cas :

```sql
SELECT 'brut' as couche, data->>'id' as id, data->>'nom' as nom, NULL as is_valid
FROM dora.services WHERE data->>'nom' ILIKE '%mot-clé%'
UNION ALL
SELECT 'staging', id, nom, NULL
FROM public_staging.stg_dora__services WHERE nom ILIKE '%mot-clé%'
UNION ALL
SELECT 'intermediate', id, nom, NULL
FROM public_intermediate.int_dora__services_v1 WHERE nom ILIKE '%mot-clé%'
UNION ALL
SELECT 'union', id, nom, NULL
FROM public_intermediate.int__union_services_v1 WHERE source = 'dora' AND nom ILIKE '%mot-clé%'
UNION ALL
SELECT 'finals', id, nom, _is_valid::text
FROM public_intermediate.int__services_v1 WHERE source = 'dora' AND nom ILIKE '%mot-clé%'
UNION ALL
SELECT 'marts', id, nom, _is_valid::text
FROM public_marts.marts__services_v1 WHERE source = 'dora' AND nom ILIKE '%mot-clé%'
```

Si la donnée apparaît dans une couche mais pas la suivante, c'est là qu'elle est perdue. Approfondir ensuite avec les requêtes ciblées ci-dessous.

### Étape 3 — Requêtes ciblées par couche

**Marts** (ce que l'API retourne) :

```sql
SELECT svc.id, svc.nom, svc.commune, svc.thematiques, svc._is_valid, svc._in_opendata, s.nom as structure
FROM public_marts.marts__services_v1 svc
JOIN public_marts.marts__structures_v1 s ON s.id = svc.structure_id
WHERE svc.source = 'dora' AND svc.code_postal LIKE '85%'
```

**Finals** (après validation + dédup) :

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
SELECT data->>'id' as id, data->>'nom' as nom, data->>'siret' as siret, data->>'lien_source' as lien_source
FROM dora.structures
WHERE data->>'nom' ILIKE '%nom de la structure%'
LIMIT 10
```

```sql
SELECT data->>'id' as id, data->>'nom' as nom, data->>'structure_id' as structure_id, data->>'lien_source' as lien_source
FROM dora.services
WHERE data->>'nom' ILIKE '%nom du service%'
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
