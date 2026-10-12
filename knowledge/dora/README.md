---
source: metabase:dora
verifie_le: 2026-10-12
---
# Dora Metabase

- **URL:** https://metabase.dora.inclusion.gouv.fr
- **Database:** `dora-analytics` (PostgreSQL)
- **Instance name:** `dora`

## Route de requête

Une question Dora se traite d'abord dans `autometa_tables_db`, selon le skill `autometa_tables_db`, qui en désigne les tables de référence Dora (`fct_dora__imer`, `fct_dora__orientations`) et, pour le détail, les tables brutes du schéma `raw_dora`. Cette fiche documente le **Metabase Dora** (instance `dora`, base 2) : c'est le dernier repli, quand `autometa_tables_db` ne couvre pas le besoin, et il s'annonce à l'utilisateur. Le calcul de l'iMER à la main décrit plus bas vise les tables du Metabase Dora ; si `raw_dora` en porte des copies (noms de tables à confirmer dans le catalogue), les y interroger évite de quitter `autometa_tables_db`.

Le périmètre de `fct_dora__imer` n'est documenté nulle part dans le dépôt (composantes de l'iMER retenues, connectés et anonymes) : à confirmer dans `documentation.doc_autometa_tables` avant de comparer ses chiffres à ceux de cette fiche.

## Qu'est-ce que Dora ?
Dora is a directory of social services for support professionals — it covers social barriers in general (housing, mobility, health, etc.), for any public in difficulty, not specifically the IAE public.

## Related Knowledge

Dora has two knowledge files:

| File | Content |
|------|---------|
| **This file** (`knowledge/dora/README.md`) | Metabase database: structures, services, orientations, iMER, search data, SQL queries |
| `knowledge/sites/dora.md` | Matomo web analytics: traffic baselines, events, funnels, segments |

**Use this file** for: querying the database, understanding the domain model, search analytics by organization, content freshness.

**Use `knowledge/sites/dora.md`** for: visitor counts, bounce rates, event tracking, user journeys, Matomo segments.

## Access

The API key (`METABASE_DORA_API_KEY`) has database query access but limited collection permissions:
- Can execute SQL queries on all tables
- Cannot view dashboards or cards (18 dashboards, 163+ cards exist but return 403)

To get full access, the API key needs to be added to a group with collection permissions in Metabase admin.

## Querying Dora Metabase

### Base 2

`database_id` vaut 2 par défaut pour toutes les instances (`lib/metabase.py`) ; le passer explicitement reste sans risque.

```python
from lib.query import CallerType, execute_metabase_query

result = execute_metabase_query(
    instance="dora",
    caller=CallerType.AGENT,
    sql="SELECT COUNT(*) FROM structures_structure",
    database_id=2,
)
```

### Case-sensitive table names

The `int_iMER` table name is case-sensitive in PostgreSQL. Use quotes:

```sql
-- CORRECT
SELECT * FROM public_intermediate."int_iMER" LIMIT 10

-- WRONG - will error "relation does not exist"
SELECT * FROM public_intermediate.int_imer LIMIT 10
```

## Domain Model

Dora is a directory of social services (services d'insertion) that connects professionals (prescribers) with services for their beneficiaries.

### Core Entities

```
Structure (25,298)
    └── Service (37,514)
            └── Orientation (11,220)
                    └── Beneficiary (usager)

User (50,947)
    ├── Prescriber (accompagnateur) - orients beneficiaries to services
    └── Provider (offreur) - manages structures/services
```

**Structure:** An organization (association, public service, company) that provides social services. Has a typology (ASSO, ACI, EI, CCAS, etc.) and location.

**Service:** A specific offering from a structure. Has categories/themes, location, criteria, and can accept orientations. Services are searchable by location + theme + subtheme.

**Orientation:** A formal request from a prescriber to orient a beneficiary towards a service. Statuses, as defined by Dora (`OrientationStatus`, `back/dora/orientations/models.py`):
- `VALIDÉE` (5,020) - Accepted
- `EXPIRÉE` (4,907) - Expired without response
- `REFUSÉE` (709) - Rejected
- `OUVERTE` (367) - Open/pending
- `MODÉRATION_EN_COURS`, `MODÉRATION_REJETÉE` - In moderation

Counts from January 2026. An earlier version of this file wrote the statuses without accents; the Dora model uses accents. À confirmer dans la base analytique (`SELECT DISTINCT status FROM orientations_orientation`) avant de filtrer sur un statut.

> **IMPORTANT:** Orientations are only ONE component of the broader **iMER** indicator.
> When a user asks about Dora's impact or activity, always present iMER (not just
> orientations). See "Key Metrics" below for the full definition.

**User:** Platform users with main activities:
- `accompagnateur` (17,407) - Prescribers who orient beneficiaries
- `accompagnateur_offreur` (17,260) - Both prescriber and provider
- `offreur` (3,841) - Service providers only
- `autre` (5,517) - Other roles

### Key Metrics

#### iMER — Dora's primary impact indicator

**iMER (Intention de Mise en Relation)** is the key metric used by the Dora team to
measure service impact. It captures ALL meaningful interactions between users and
services/structures — not just formal orientations.

> **When a user asks about Dora activity, usage, or impact, present iMER as the primary
> indicator by default**, and state the distinction with orientations, which alone
> undercount actual usage by a factor of ~11x.

#### Orientations vs iMER

| Indicator | What it measures | Count | Use when |
|-----------|-----------------|------:|----------|
| **Orientations** | Formal requests sent via Dora | 11,533 | Analyzing the orientation workflow (validation rates, response times) |
| **iMER** | All meaningful intent signals | 128,799 | Measuring Dora's overall impact and usage (**preferred**) |

Orientations represent only **9%** of total iMER. The remaining 91% are mobilisations
(see « What records a mobilisation » below) and structure info views (contact page
consultations — phone, email).

#### The 5 components of iMER

As of Jan 2026 — 128,799 total:

| # | Component | Source table | Count | % | Description |
|---|-----------|-------------|------:|--:|-------------|
| 1 | Mobilisations (connected) | `stats_mobilisationevent` | 32,537 | 25% | Mobilisations by logged-in users |
| 2 | Orientations | `orientations_orientation` | 11,533 | 9% | Formal orientation requests |
| 3 | Structure info views (connected) | `stats_structureinfosview` | 6,275 | 5% | Contact page views by logged-in users |
| 4 | Mobilisations (anonymous) | `stats_mobilisationevent` | 29,697 | 23% | Mobilisations by anonymous visitors |
| 5 | Structure info views (anonymous) | `stats_structureinfosview` | 48,757 | 38% | Contact page views by anonymous visitors |

#### What records a mobilisation

Dora has no « interest » button. A `MobilisationEvent` (table `stats_mobilisationevent`) is recorded by
`trackMobilisation` (`front/src/lib/utils/stats.ts` in `gip-inclusion/dora`) when:

- a logged-in user clicks « Orienter votre bénéficiaire » (or « Faire une demande ») in the « Mobiliser ce service » box of a service page;
- a logged-in user lands on the orientation form after logging in;
- someone, logged in or not, displays the coordonnées of a service whose contact details are public (« tracking comme MER » in `orienter/contact-info.svelte`);
- someone follows an external mobilisation link (column `external_link`).

The service page guards against recording the same mobilisation twice. Services coming from data·inclusion record a `DiMobilisationEvent` instead (table `stats_dimobilisationevent`, not counted in the components above). Verified against Dora `main` @ `6e82bc9` on 2026-10-12; the counts above predate that check.

**Why structure info views matter:** `stats_structureinfosview` tracks when a user
accesses a structure's contact information (phone number, email, address). This is a
strong intent signal — the user is looking to contact the structure directly, bypassing
the formal orientation process. These views represent **43%** of all iMER.

**Connected vs anonymous breakdown:**
- Connected users: 50,345 (39%)
- Anonymous visitors: 78,454 (61%)

#### Filters applied per component

| Component | Filter |
|-----------|--------|
| Mobilisations (connected) | `user_id IS NOT NULL`, `is_staff = FALSE`, `user_kind IN ('accompagnateur', 'accompagnateur_offreur', 'offreur')` |
| Orientations | All orientations (no filter) |
| Structure info views (connected) | `is_logged = TRUE`, `is_staff = FALSE`, `is_structure_member = FALSE`, `is_structure_admin = FALSE`, `user_kind != 'autre' OR user_kind IS NULL` |
| Mobilisations (anonymous) | `user_id IS NULL` |
| Structure info views (anonymous) | `is_logged = FALSE`, same staff/member/admin exclusions |

The reference Metabase question for iMER is **question #295** (not accessible via our
API key — SQL definition documented below in "Computing iMER").

#### ⚠️ Limitation of the int_iMER intermediate table

The pre-computed table `public_intermediate."int_iMER"` only contains **components 1
and 2** (mobilisations + orientations by connected users). It does NOT include:
- Structure info views (components 3 and 5) — 43% of total iMER
- Anonymous mobilisations (component 4) — 23% of total iMER

**For full iMER counts, query the source tables directly** using the SQL below.
Use `int_iMER` only for quick breakdowns of connected-user mobilisations/orientations.

#### Computing iMER

**All components (no category filter):**
```sql
-- Component 1: Mobilisations by connected users
SELECT COUNT(DISTINCT me.id)
FROM stats_mobilisationevent me
WHERE me.user_id IS NOT NULL
AND me.is_staff = FALSE
AND me.user_kind IN ('accompagnateur', 'accompagnateur_offreur', 'offreur');

-- Component 2: Orientations
SELECT COUNT(DISTINCT o.id) FROM orientations_orientation o;

-- Component 3: Structure info views (connected)
SELECT COUNT(DISTINCT siv.id)
FROM stats_structureinfosview siv
WHERE siv.is_staff = FALSE
AND siv.is_structure_member = FALSE
AND siv.is_structure_admin = FALSE
AND (siv.user_kind != 'autre' OR siv.user_kind IS NULL)
AND siv.is_logged = TRUE;

-- Component 4: Mobilisations by anonymous users
SELECT COUNT(DISTINCT me.id)
FROM stats_mobilisationevent me
WHERE me.user_id IS NULL;

-- Component 5: Structure info views (anonymous)
SELECT COUNT(DISTINCT siv.id)
FROM stats_structureinfosview siv
WHERE siv.is_staff = FALSE
AND siv.is_structure_member = FALSE
AND siv.is_structure_admin = FALSE
AND (siv.user_kind != 'autre' OR siv.user_kind IS NULL)
AND siv.is_logged = FALSE;
```

#### With geographic filter (e.g., Île-de-France):
-- For mobilisations:
```sql
AND me.structure_department IN ('75','77','78','91','92','93','94','95')
```

-- For orientations (join prescriber structure):
```sql
JOIN structures_structure ps ON o.prescriber_structure_id = ps.id
... AND ps.department IN ('75','77','78','91','92','93','94','95')
```

-- For structure info views:
```sql
AND siv.structure_department IN ('75','77','78','91','92','93','94','95')
```

#### With category filter (e.g., "freins périphériques"):
-- For mobilisations: add JOINs to service categories
```sql
SELECT COUNT(DISTINCT me.id)
FROM stats_mobilisationevent me
JOIN services_service_categories ssc ON me.service_id = ssc.service_id
JOIN services_servicecategory sc ON ssc.servicecategory_id = sc.id
WHERE sc.value IN ('mobilite', 'famille', 'logement-hebergement',
                   'equipement-et-alimentation', 'difficultes-financieres',
                   'sante', 'numerique')
AND me.user_id IS NOT NULL
AND me.is_staff = FALSE
AND me.user_kind IN ('accompagnateur', 'accompagnateur_offreur', 'offreur');
```

-- For orientations: same pattern
```sql
SELECT COUNT(DISTINCT o.id)
FROM orientations_orientation o
JOIN services_service_categories ssc ON o.service_id = ssc.service_id
JOIN services_servicecategory sc ON ssc.servicecategory_id = sc.id
WHERE sc.value IN (...);
```

-- For structure info views: join via structure → service → category
```sql
SELECT COUNT(DISTINCT siv.id)
FROM stats_structureinfosview siv
JOIN services_service s ON siv.structure_id = s.structure_id
JOIN services_service_categories ssc ON s.id = ssc.service_id
JOIN services_servicecategory sc ON ssc.servicecategory_id = sc.id
WHERE sc.value IN (...)
AND siv.is_staff = FALSE
AND siv.is_structure_member = FALSE
AND siv.is_structure_admin = FALSE
AND (siv.user_kind != 'autre' OR siv.user_kind IS NULL)
AND siv.is_logged = TRUE;  -- or FALSE for anonymous
```

**Conversion funnel:**
1. Search (634,827 search views)
2. Service view (1,767,429 service views)
3. iMER (128,799 intent signals) — of which:
    - Mobilisations: 62,234 (connected + anonymous)
    - Structure info views: 55,032 (connected + anonymous)
    - Orientations: 11,533
4. Orientation validated (5,020 VALIDÉE)

### Content Freshness

Whether a service or structure has been recently updated is an important quality metric.

**Service freshness (as of Jan 2025):**
| Last updated | Services |
|--------------|----------|
| Last 30 days | 2,606 |
| 30-90 days | 4,557 |
| 90-180 days | 7,546 |
| 6-12 months | 7,281 |
| Over 1 year | 15,524 |

**Structure freshness:**
| Last updated | Structures |
|--------------|------------|
| Last 30 days | 432 |
| 30-90 days | 1,353 |
| 90-180 days | 2,368 |
| 6-12 months | 3,592 |
| Over 1 year | 17,553 |

Key date fields on `services_service`: `creation_date`, `modification_date`, `publication_date`, `suspension_date`, `update_frequency`.

## Database Schema

### Schemas

| Schema | Purpose |
|--------|---------|
| `public` | Core application tables |
| `public_intermediate` | Pre-computed analytics (dbt models) |
| `matomo` | Matomo tracking data |

### Core Tables (public)

| Table | Records | Description |
|-------|---------|-------------|
| `structures_structure` | 25,298 | Organizations providing services |
| `services_service` | 37,514 | Service offerings |
| `users_user` | 50,947 | Platform users |
| `orientations_orientation` | 11,533 | Orientation requests (1 of 5 iMER components) |
| `services_servicecategory` | 23 | Service themes/categories |
| `stats_mobilisationevent` | 71,128 | Mobilisation/interest events (2 of 5 iMER components: connected + anonymous) |
| `stats_structureinfosview` | ~55,000 | Structure contact page views — phone, email, address (2 of 5 iMER components: connected + anonymous) |
| `stats_serviceview` | 1,767,429 | Service page views |
| `stats_searchview` | 634,827 | Search events |
| `stats_pageview` | 6,858,377 | General page views |

### Analytics Tables (public_intermediate)

Pre-computed tables for dashboards:

| Table | Description |
|-------|-------------|
| `int_iMER` | **Partial** iMER data: only mobilisations + orientations by connected users (63,328 records). See "⚠️ Limitation" above. |
| `int_monthly_user_iMER` | Monthly iMER aggregations per user |
| `int_monthly_user_orientations` | Monthly orientations per user |
| `int_monthly_user_mobilisations` | Monthly mobilisations per user |
| `int_monthly_user_service_views` | Monthly service views per user |
| `int_orientation_user_service` | Orientation details with user/service data (132 fields) |
| `int_orientations_following_mobilisation` | Conversion tracking |
| `int_prescribers` | Prescriber profiles (38,480 records, 54 fields) |
| `int_service_structure` | Service with structure data |
| `int_service_categories` | Services with category data |
| `int_structure_*` | Structure aggregations |

### Matomo Tables

| Table | Description |
|-------|-------------|
| `mtm_share_service_tracking` | Service share tracking from Matomo |

## Service Categories

| ID | Slug | Label |
|----|------|-------|
| 15 | acces-aux-droits-et-citoyennete | Acces aux droits & citoyennete |
| 7 | accompagnement-social-et-professionnel-personnalise | Accompagnement social et professionnel personnalise |
| 5 | apprendre-francais | Apprendre le Francais |
| 34 | choisir-un-metier | Choisir un metier |
| 1 | creation-activite | Creation d'activite |
| 6 | gestion-financiere | Gestion financiere |
| 8 | handicap | Handicap |
| 11 | illettrisme | Illettrisme |
| 10 | logement-hebergement | Logement et hebergement |
| 13 | mobilite | Mobilite |
| 2 | numerique | Numerique |
| 35 | preparer-sa-candidature | Preparer sa candidature |
| 14 | remobilisation | Remobilisation |
| 9 | sante | Sante |

## Structure Typologies

| Code | Count | Description |
|------|-------|-------------|
| ASSO | 2,228 | Association |
| ACI | 1,985 | Atelier et Chantier d'Insertion |
| EI | 1,291 | Entreprise d'Insertion |
| FT | 1,023 | France Travail (ex-Pole Emploi) |
| CCAS | 876 | Centre Communal d'Action Sociale |
| EA | 811 | Entreprise Adaptee |
| AI | 648 | Association Intermediaire |
| ETTI | 638 | Entreprise de Travail Temporaire d'Insertion |
| ML | 458 | Mission Locale |
| OF | 406 | Organisme de Formation |

## Search Data

Search is the main entry point: users search by location + theme (category) + optional subtheme.

### Tables

| Table | Description |
|-------|-------------|
| `stats_searchview` | Raw search events (634,827 total) |
| `stats_searchview_categories` | Join table linking searches to categories |
| `public_intermediate.int_searchview_user` | Enriched view with user details |

### stats_searchview Columns

| Column | Description |
|--------|-------------|
| `date` | Search timestamp |
| `city_code`, `department` | Location searched |
| `num_results` | Total results returned |
| `num_di_results` | Results from Data Inclusion (national registry) |
| `num_di_results_top10` | DI results in top 10 |
| `results_slugs_top10` | Service slugs of top 10 results |
| `is_logged`, `user_kind` | User context |
| `user_id` | Links to `users_user` (NULL if anonymous) |

### Linking Searches to Users and Organizations

Searches can be linked to specific users and their structures. About 30% of searches come from logged-in users.

**Key join path:**
```
stats_searchview.user_id
  → structures_structuremember.user_id
    → structures_structure.id
```

**Basic search with user's organization:**
```sql
SELECT
    sv.date,
    sv.department,
    sv.num_results,
    u.email,
    s.name as structure_name,
    s.typology
FROM stats_searchview sv
JOIN structures_structuremember sm ON sv.user_id = sm.user_id
JOIN structures_structure s ON sm.structure_id = s.id
JOIN users_user u ON sv.user_id = u.id
WHERE sv.date >= '2025-01-01'
ORDER BY sv.date DESC
```

**Top organizations by search volume:**
```sql
SELECT
    s.name as structure_name,
    s.typology,
    s.department,
    COUNT(*) as searches
FROM stats_searchview sv
JOIN structures_structuremember sm ON sv.user_id = sm.user_id
JOIN structures_structure s ON sm.structure_id = s.id
WHERE sv.date >= '2025-01-01'
GROUP BY s.id, s.name, s.typology, s.department
ORDER BY searches DESC
LIMIT 25
```

**Searches aggregated by organization type:**
```sql
SELECT
    COALESCE(NULLIF(s.typology, ''), '(non renseigne)') as typology,
    COUNT(DISTINCT s.id) as orgs,
    COUNT(*) as searches
FROM stats_searchview sv
JOIN structures_structuremember sm ON sv.user_id = sm.user_id
JOIN structures_structure s ON sm.structure_id = s.id
WHERE sv.date >= '2025-01-01'
GROUP BY 1
ORDER BY searches DESC
```

**Or use the pre-joined intermediate table (for user details only, no structure):**
```sql
SELECT
    event_date,
    event_num_results,
    user_email,
    user_main_activity
FROM public_intermediate.int_searchview_user
WHERE user_id IS NOT NULL
ORDER BY event_date DESC
```

### Top Searching Organizations (2025)

**By individual organization:**
| Structure | Type | Dept | Searches |
|-----------|------|------|----------|
| Departement de la Drome | CD | 26 | 2,634 |
| Conseil Departemental de la Somme | CD | 80 | 1,734 |
| DGAS Direction Generale Adjointe (Vienne) | CD | 86 | 1,486 |
| Departement du Loiret | CD | 45 | 1,081 |
| Departement de la Vienne | CD | 86 | 1,066 |

**By organization type:**
| Type | Orgs | Searches |
|------|------|----------|
| France Travail (FT) | 938 | 65,369 |
| (non renseigne) | 825 | 27,660 |
| Conseil Departemental (CD) | 51 | 16,103 |
| Association (ASSO) | 665 | 15,631 |
| Autre | 448 | 15,198 |
| ACI | 359 | 7,152 |
| MDS | 15 | 6,917 |
| DEPT | 57 | 4,398 |
| Cap Emploi | 90 | 3,111 |
| CCAS | 157 | 2,754 |
| Mission Locale (ML) | 197 | 2,433 |

France Travail dominates (65k searches from 938 agencies). Conseils Departementaux are heavy users relative to their count (16k from 51 orgs).

### 2025 Search Statistics

**Monthly volume:**
| Month | Searches |
|-------|----------|
| 2025-01 | 32,669 |
| 2025-02 | 32,943 |
| 2025-03 | 32,631 |
| 2025-04 | 31,422 |
| 2025-05 | 25,738 |
| 2025-06 | 30,678 |
| 2025-07 | 29,257 |
| 2025-08 | 22,170 |
| 2025-09 | 30,733 |
| 2025-10 | 36,196 |
| 2025-11 | 32,169 |
| 2025-12 | 30,220 |

**Top searched categories (2025):**
| Category | Searches |
|----------|----------|
| Apprendre le Francais | 51,395 |
| Mobilite | 38,250 |
| Accompagnement social et professionnel | 27,728 |
| Logement et hebergement | 26,921 |
| Trouver un emploi | 26,278 |
| Numerique | 21,373 |
| Acces aux droits & citoyennete | 17,885 |
| Choisir un metier | 16,525 |
| Famille | 16,403 |
| Sante | 15,138 |

**Top departments (2025):**
| Dept | Searches |
|------|----------|
| 59 (Nord) | 19,893 |
| 75 (Paris) | 15,022 |
| 26 (Drome) | 14,070 |
| 13 (Bouches-du-Rhone) | 13,907 |
| 93 (Seine-Saint-Denis) | 12,594 |

**User breakdown (2025):**
| User type | Searches | % |
|-----------|----------|---|
| Anonymous | 271,992 | 70% |
| Accompagnateur | 52,282 | 13% |
| Accompagnateur_offreur | 40,435 | 10% |
| Autre | 18,965 | 5% |
| Offreur | 6,733 | 2% |

**Results distribution (2025):**
| Bucket | Searches |
|--------|----------|
| 0 results | 1,354 (0.3%) |
| 1-10 | 34,056 |
| 11-50 | 133,345 |
| 51-100 | 93,764 |
| 101-500 | 85,706 |
| 500+ | 42,182 |

**Zero-result searches** are rare (0.3%), mostly in "Equipement et alimentation" category (731 cases) - potential coverage gap.

**Data Inclusion integration:** 83% of searches return DI results (324,071 vs 66,336 without).

## Sample Queries

### Monthly orientations
```sql
SELECT TO_CHAR(creation_date, 'YYYY-MM') as month,
       COUNT(*) as orientations
FROM orientations_orientation
WHERE creation_date >= '2025-01-01'
GROUP BY 1
ORDER BY 1
```

### iMER by kind
```sql
SELECT kind, COUNT(*) as count
FROM public_intermediate."int_iMER"
GROUP BY kind
ORDER BY count DESC
```

### Active prescribers (with orientations)
```sql
SELECT COUNT(DISTINCT prescriber_id)
FROM orientations_orientation
WHERE creation_date >= '2025-01-01'
```

### Services by category
```sql
SELECT sc.value as category, COUNT(*) as services
FROM services_service s
JOIN services_service_categories ssc ON s.id = ssc.service_id
JOIN services_servicecategory sc ON ssc.servicecategory_id = sc.id
GROUP BY sc.value
ORDER BY services DESC
```

### Monthly searches
```sql
SELECT TO_CHAR(date, 'YYYY-MM') as month, COUNT(*) as searches
FROM stats_searchview
WHERE date >= '2025-01-01'
GROUP BY 1
ORDER BY 1
```

### Searches by category
```sql
SELECT sc.label, COUNT(*) as searches
FROM stats_searchview_categories svc
JOIN services_servicecategory sc ON svc.servicecategory_id = sc.id
JOIN stats_searchview sv ON svc.searchview_id = sv.id
WHERE sv.date >= '2025-01-01'
GROUP BY sc.label
ORDER BY searches DESC
```

### Zero-result searches by category
```sql
SELECT sc.label, COUNT(*) as zero_result_searches
FROM stats_searchview_categories svc
JOIN services_servicecategory sc ON svc.servicecategory_id = sc.id
JOIN stats_searchview sv ON svc.searchview_id = sv.id
WHERE sv.date >= '2025-01-01' AND sv.num_results = 0
GROUP BY sc.label
ORDER BY zero_result_searches DESC
```

### Service/structure freshness
```sql
SELECT
    CASE
        WHEN modification_date >= NOW() - INTERVAL '30 days' THEN 'Last 30 days'
        WHEN modification_date >= NOW() - INTERVAL '90 days' THEN '30-90 days'
        WHEN modification_date >= NOW() - INTERVAL '180 days' THEN '90-180 days'
        WHEN modification_date >= NOW() - INTERVAL '365 days' THEN '6-12 months'
        ELSE 'Over 1 year'
    END as freshness,
    COUNT(*) as count
FROM services_service
GROUP BY 1
ORDER BY 2 DESC
```

### iMER and orientations by organization type
```sql
-- Compare mobilisations and orientations by organization cluster
WITH imer_by_org AS (
    SELECT
        CASE
            WHEN s.typology = 'FT' THEN 'France Travail'
            WHEN s.typology IN ('CD', 'MDS', 'CCAS', 'DEPT') THEN 'Services publics generalistes'
            WHEN s.typology IN ('ML', 'CAP_EMPLOI') THEN 'Operateurs emploi'
            ELSE 'Autres'
        END as cluster,
        i.kind,
        COUNT(*) as count
    FROM public_intermediate."int_iMER" i
    JOIN structures_structuremember sm ON i.user_id = sm.user_id
    JOIN structures_structure s ON sm.structure_id = s.id
    WHERE i.date >= '2025-01-01'
    GROUP BY 1, 2
)
SELECT cluster, kind, count
FROM imer_by_org
ORDER BY cluster, kind
```

### Conversion rates by category (mobilisation → orientation)
```sql
-- Calculate conversion rate from mobilisation to orientation by service category
WITH mobs AS (
    SELECT
        i.service_categories,  -- comma-separated list
        COUNT(*) as mobilisations
    FROM public_intermediate."int_iMER" i
    WHERE i.kind = 'mobilisation' AND i.date >= '2025-01-01'
    GROUP BY 1
),
orients AS (
    SELECT
        i.service_categories,
        COUNT(*) as orientations
    FROM public_intermediate."int_iMER" i
    WHERE i.kind = 'orientation' AND i.date >= '2025-01-01'
    GROUP BY 1
)
SELECT
    COALESCE(m.service_categories, o.service_categories) as categories,
    COALESCE(m.mobilisations, 0) as mobilisations,
    COALESCE(o.orientations, 0) as orientations,
    ROUND(100.0 * COALESCE(o.orientations, 0) / NULLIF(COALESCE(m.mobilisations, 0), 0), 1) as conversion_rate
FROM mobs m
FULL OUTER JOIN orients o ON m.service_categories = o.service_categories
ORDER BY mobilisations DESC
```

### Orientation validation rate by organization type
```sql
-- Validation rate (VALIDÉE / total) by organization cluster
SELECT
    CASE
        WHEN s.typology = 'FT' THEN 'France Travail'
        WHEN s.typology IN ('CD', 'MDS', 'CCAS', 'DEPT') THEN 'Services publics'
        WHEN s.typology IN ('ML', 'CAP_EMPLOI') THEN 'Operateurs emploi'
        ELSE 'Autres'
    END as cluster,
    COUNT(*) as total_orientations,
    COUNT(*) FILTER (WHERE o.status = 'VALIDÉE') as validated,
    ROUND(100.0 * COUNT(*) FILTER (WHERE o.status = 'VALIDÉE') / COUNT(*), 1) as validation_rate
FROM orientations_orientation o
JOIN structures_structuremember sm ON o.prescriber_id = sm.user_id
JOIN structures_structure s ON sm.structure_id = s.id
WHERE o.creation_date >= '2025-01-01'
GROUP BY 1
ORDER BY total_orientations DESC
```

## Related Resources

- Site knowledge: `knowledge/sites/dora.md` (Matomo tracking, events, funnels)
- Dora website: https://dora.inclusion.gouv.fr
- GitHub: https://github.com/gip-inclusion/dora
