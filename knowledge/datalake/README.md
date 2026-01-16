# Datalake Metabase Instance

**URL:** https://datalake.inclusion.beta.gouv.fr
**Instance name:** `datalake`

Cross-product analytics for la Plateforme de l'inclusion. Contains aggregated user data across multiple services (Emplois, Pilotage, GPS, Dora, Mon Recap, etc.).

## Usage

```python
from lib.sources import get_metabase

api = get_metabase("datalake")
result = api.execute_sql("SELECT * FROM pdi_base_unique_tous_les_pros LIMIT 10", database_id=2)
```

## Databases

| ID | Name | Description |
|----|------|-------------|
| 2 | Datalake | Main data warehouse with cross-product analytics |
| 3 | Spock | Metabase internal + company scoring data |

## Dashboards

| ID | Name | Collection |
|----|------|------------|
| 20 | Suivi de la rétention et de la croissance par cible et par produit | Indicateurs de performance |
| 21 | Recherche de contacts et structures sur la base de données commune | Moteur de recherche de contacts |
| 24 | Utilisateurs Communs Emplois - Dora | Utilisateurs Communs Emplois - Dora |

## Key Tables (Database 2: Datalake)

### Cross-Product User Data

| Table | Rows | Description |
|-------|------|-------------|
| `pdi_base_unique_tous_les_pros` | ~225k | Unified professional user base across all products |
| `statsretention_cohortes_gip` | ~4.5k | Retention cohort analysis |
| `statsretention_gip` | ~330 | Retention metrics |
| `statsretention_historisation` | ~58k | Historical retention data |

### Product-Specific Data

| Table | Rows | Description |
|-------|------|-------------|
| `gps_log_data` | ~5.5k | GPS (Mon Suivi) application logs |
| `statsgps_logs_groupes` | ~3.2k | GPS logs grouped |
| `monrecap_barometre` | ~153k | Mon Recap barometer data |
| `monrecap_commandes` | ~4.5k | Mon Recap orders |
| `monrecap_contacts` | ~3.8k | Mon Recap contacts |
| `immersion_facile_stats_support` | ~29k | Immersion Facile support stats |
| `immersion_facile_email_agences` | ~3.5k | Immersion Facile agency emails |

### Operational Data

| Table | Rows | Description |
|-------|------|-------------|
| `brevo_conso` | ~13 | Brevo email consumption |
| `webinaires_pilotage_participants` | ~3.7k | Pilotage webinar participants |
| `support_emplois_tickets_infos` | - | Support ticket info |
| `statsfile_active_gip` | ~65 | Active file stats |

### Reference Tables

| Table | Rows | Description |
|-------|------|-------------|
| `correspondance_cible_vers_cat_donnee` | ~16 | Target to data category mapping |
| `correspondance_produit_vers_axe` | ~8 | Product to axis mapping |
| `table_correspondance_domaines_pilotage` | ~2k | Pilotage domain mapping |

### Analysis Tables

| Table | Rows | Description |
|-------|------|-------------|
| `analyse_aigles` | ~483 | "Eagles" (super-users) analysis |
| `analyse_emails` | - | Email analysis |
| `analyse_event` | - | Event analysis |
| `datacube_score_v0` | ~87 | Data cube scoring |
| `stats_nps_gip` | ~261 | NPS scores |
| `stats_pdi_data` | ~161 | PDI statistics |

## Key Tables (Database 3: Spock)

Company scoring data from le Marche.

| Table | Rows | Description |
|-------|------|-------------|
| `company_score_scoredcompany` | ~15k | Scored companies with API Entreprise data |
| `company_score_ifrawconvention` | ~13k | Convention data by SIREN |
| `company_score_lemarcherawtender` | ~5.3k | Le Marche tender data |
| `company_score_domainsirenassociation` | ~1.5k | Domain to SIREN associations |

## Collections Structure

```
Root
├── Giulia (112)
│   └── Utilisateurs Communs Emplois - Dora (110) → Dashboard [24]
├── Nova (74)
│   ├── Indicateurs de performance (75) → Dashboard [20]
│   ├── Moteur de recherche de contacts (87) → Dashboard [21]
│   ├── Stats clés (117)
│   ├── Utilisateurs multiservices (95)
│   └── demandes_bizdev (94)
└── Pierre (4)
    ├── Aigles (30)
    └── Stages CIP (13)
```
