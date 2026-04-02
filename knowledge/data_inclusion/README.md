# data·inclusion — Datawarehouse

Base PostgreSQL (+PostGIS) consolidant l'offre d'insertion sociale et professionnelle en France. 110k structures, 180k services, 17 sources. Code source : `gip-inclusion/data-inclusion`.

## Architecture pipeline

```
Producteurs (17 APIs externes)
    ↓  Airflow DAGs (import vers schémas source bruts)
Schémas source bruts (dora, soliguide, emplois_de_linclusion, ...)
    ↓  dbt staging
public_staging (stg_*)
    ↓  dbt intermediate (mapping → union → enrichissement → validation → dédup)
public_intermediate (int_*)
    ↓  dbt marts (contrats, index)
public_marts (marts_*)
    ↓  Airflow DAGs (export)
Parquet → S3 → API data·inclusion
```

## Schémas PostgreSQL

| Schéma | Tables | Contenu |
|---|---|---|
| `<source>` (ex: `dora`, `soliguide`) | Tables JSON brutes importées par Airflow |
| `public_staging` | 143 | Tables `stg_<source>__<entité>` nettoyées |
| `public_intermediate` | 140 | Mappings, unions, enrichissements, finals, dédup |
| `public_marts` | 22 | Tables publiées |
| `public_schema` | 18 | Tables d'énumération (thématiques, publics, modes, typologies) |
| `public` | 20 | Tables API (events, requests) + spatial_ref_sys |
| `processings` | | Fonctions PL/Python (géocodage, dédup, scoring) |

## Sources et volumes (public_marts)

| Source (slug) | Structures | Services |
|---|---|---|
| soliguide | 25 680 | 91 432 |
| emplois-de-linclusion | 17 415 | — |
| mediation-numerique | 15 145 | 15 145 |
| ma-boussole-aidants | 14 132 | 14 302 |
| monenfant | 13 920 | 13 920 |
| dora | 12 340 | 20 026 |
| cd35 | 3 617 | 778 |
| carif-oref | 2 488 | 6 044 |
| mes-aides | 1 862 | 1 862 |
| fredo | 1 681 | 3 048 |
| france-travail | 885 | 8 850 |
| reseau-alpha | 766 | 1 133 |
| action-logement | 120 | 2 640 |
| agefiph | 20 | 920 |
| mission-locale | 6 | 60 |
| **Total** | **110 077** | **180 160** |

## Schéma `public_staging` (143 tables)

Tables `stg_<source>__<entité>` + tables de jonction `stg_<source>__<entité>__<relation>`.

### Sources de données

| Source | Tables principales | Tables de jonction |
|---|---|---|
| action_logement | structures [14], services [24] | services__frais, modes_accueil, modes_mobilisation, mobilisable_par, publics, thematiques; structures__reseaux_porteurs |
| agefiph | structures [14], services [11] | services_thematiques |
| annuaire_du_service_public | etablissements [16], adresses [15] | pivots, site_internets, telephones |
| carif_oref | actions [21], formations [8], organismes_formateurs [3] | adresses, coordonnees, formacode_v14, formations__contacts, actions__publics |
| cd35 | organisations [17] | organisations__profils, organisations__thematiques, profils, thematiques |
| dora | structures [21], services [31] | 13 tables de jonction (justificatifs, modes_accueil, modes_orientation_*, pre_requis, profils, publics, thematiques, types, labels_*) |
| emplois_de_linclusion | organisations [16], siaes [16] | — |
| france_travail | agences [14], services [24] | 6 tables de jonction |
| fredo | structures [13] | categories, emails, telephones, frais, publics, services, types |
| ma_boussole_aidants | structures [19], solutions [3] | structures__services, structures__situations |
| mediation_numerique | structures [19] | dispositifs, frais, mediateurs, modalites_acces, modalites_accompagnement, prises_en_charge, publics, services |
| mes_aides | aides [24], garages [21], permis_velo [26] | ~15 tables de jonction |
| mission_locale | structures [16], offres [11] | structures_offres, offres__liste_des_profils |
| monenfant | creches [24] | communes_desservies |
| reseau_alpha | structures [10], formations [20] | adresses, contacts, horaires, publics, competences_linguistiques, criteres_scolarisation, objectifs |
| soliguide | lieux [37], services [24] | categories, sources, phones, publics (+ admin, familiale, gender, other) |
| un_jeune_une_solution | benefits [7], institutions [3] | — |

### Référentiels

| Tables | Taille |
|---|---|
| stg_sirene__stock_etablissement [2 cols] | 3.7 GB |
| stg_sirene__etablissement_historique [4 cols] | 8.4 GB |
| stg_sirene__etablissement_succession [3 cols] | 1.2 GB |
| stg_decoupage_administratif__communes [9 cols] | 9.6 MB |
| stg_decoupage_administratif__departements [3 cols] | 48 kB |
| stg_decoupage_administratif__regions [3 cols] | 32 kB |
| stg_decoupage_administratif__epcis [2 cols] | 184 kB |
| stg_decoupage_administratif__arrondissements [7 cols] | 16 kB |
| stg_decoupage_administratif__communes_associees_deleguees [9 cols] | 376 kB |
| stg_etat_civil__prenoms [1 col] | 520 kB |

### Colonnes staging Dora (source principale)

**stg_dora__structures** (21 cols) : id, nom, source, siret, lien_source, date_maj (timestamptz), adresse, complement_adresse, commune, code_postal, code_insee, latitude (float), longitude (float), telephone, courriel, site_web, presentation_resume, presentation_detail, horaires_ouverture, accessibilite, typologie.

**stg_dora__services** (31 cols) : id, nom, source, structure_id, lien_source, date_maj (timestamptz), adresse, complement_adresse, commune, code_postal, code_insee, latitude (float), longitude (float), telephone, courriel, contact_nom_prenom, presentation_resume, presentation_detail, frais, frais_autres, publics_precisions, recurrence, formulaire_en_ligne, prise_rdv, zone_diffusion_type, zone_diffusion_code, zone_diffusion_nom, modes_orientation_accompagnateur_autres, modes_orientation_beneficiaire_autres, temps_passe_semaines (int), temps_passe_duree_hebdomadaire (float).

Les tables de jonction staging (`stg_dora__services__thematiques`, etc.) ont 2 colonnes : `id` (FK service) + `value`.

## Schéma `public_intermediate` (140 tables)

Toutes les tables utilisent le suffixe `_v1`.

### Mappings (`int_<source>__<entité>_v1`)

Chaque source produit 3 modèles standardisés. Colonnes détaillées pour Dora (même schéma pour les autres sources) :

**int_dora__structures_v1** (14 cols) : source, id, adresse_id, nom, description, siret, date_maj (date), lien_source, telephone, courriel, site_web, horaires_accueil, accessibilite_lieu, reseaux_porteurs (array).

**int_dora__services_v1** (27 cols) : source, id, structure_id, adresse_id, nom, description, date_maj (date), lien_source, conditions_acces, thematiques (array), modes_accueil (array), modes_mobilisation (array), mobilisable_par (array), mobilisation_precisions, publics (array), publics_precisions, type, frais, frais_precisions, nombre_semaines (int), volume_horaire_hebdomadaire (float), zone_eligibilite (array), contact_nom_prenom, courriel, telephone, lien_mobilisation, horaires_accueil.

**int_dora__adresses_v1** (9 cols) : source, id, adresse, complement_adresse, commune, code_postal, code_insee, latitude (float), longitude (float).

Sources : action_logement, agefiph, carif_oref, cd35, dora, emplois_de_linclusion, france_travail, fredo, ma_boussole_aidants, mediation_numerique, mes_aides (garages + aides + permis_velo), monenfant, reseau_alpha, soliguide.

### Unions

**int__union_structures_v1** (15 cols, 93 MB, 110k lignes) : source, id, adresse_id, nom, date_maj (date), lien_source, siret, telephone, courriel, site_web, description, horaires_accueil, accessibilite_lieu, reseaux_porteurs (array), hash_id.

**int__union_services_v1** (30 cols, 317 MB, 180k lignes) : source, id, structure_id, adresse_id, nom, description, date_maj (date), lien_source, type, thematiques (array), frais, frais_precisions, frais_autres, publics (array), publics_precisions, conditions_acces, telephone, courriel, contact_nom_prenom, modes_accueil (array), modes_mobilisation (array), mobilisable_par (array), lien_mobilisation, mobilisation_precisions, zone_eligibilite (array), zone_eligibilite_type, volume_horaire_hebdomadaire (float), nombre_semaines (int), horaires_accueil, _extra (jsonb).

int__union_adresses_v1 (10 cols, 20 MB), int__union_contacts_v1 (5 cols, 21 MB), int__union_urls_v1 (1 col, 38 MB).

### Enrichissements

**int__geocodages_v1** (15 cols, 30 MB, 128k lignes) : adresse_id, input_adresse, input_code_postal, input_code_insee, input_commune, commune, adresse, code_postal, code_commune, code_arrondissement, score (float), type, longitude (float), latitude (float), geocoded_at (timestamp).

**int__sirets_v1** (5 cols, 5.3 MB) : id, siret, statut, date_fermeture (date), siret_successeur.

**int__courriels_verifies_v1** (3 cols, 1.6 MB) : courriel, has_hardbounced, was_objected_to.

int__courriels_personnels_v1 (1 col), int__contacts_v1 (6 cols), int__urls_v1 (6 cols), int__adresses_v1 (12 cols).

### Finals

Les colonnes de `int__structures_v1` et `int__services_v1` sont les mêmes que les marts (voir section `public_marts`) sans les flags qualité `_is_valid`, `_is_closed`, etc. qui sont ajoutés au passage en marts.

**int__erreurs_validation_v1** (9 cols, 605 lignes) : id, source, resource_type, schema_version, model_class, type, loc, msg, input (jsonb).

**int__criteres_qualite_v1** (5 cols, 212 MB) : service_id, nom_critere, score_critere, score_ligne, schema_version.

### Déduplication

**int__doublons_structures_v1** (5 cols, 2.6 MB, 21k lignes) : cluster_id, structure_id, source, score (float), size (bigint).

**int__doublons_paires_structures_v1** (6 cols) : cluster_id, structure_id_1, structure_id_2, source_1, source_2, size.

int__doublons_nb_mono_source_v1 (3 cols), int__doublons_nb_cross_source_v1 (6 cols).

## Schéma `public_marts` (22 tables)

### Tables principales v1

**marts__structures_v1** (26 cols, 101 MB, 110 077 lignes)

| Colonne | Type | Nullable |
|---|---|---|
| id | text | NOT NULL |
| siret | text | nullable |
| nom | text | nullable |
| commune | text | nullable |
| code_postal | text | nullable |
| code_insee | text | nullable |
| adresse | text | nullable |
| complement_adresse | text | nullable |
| longitude | double precision | nullable |
| latitude | double precision | nullable |
| telephone | text | nullable |
| courriel | text | nullable |
| site_web | text | nullable |
| description | text | nullable |
| source | text | NOT NULL |
| date_maj | date | nullable |
| lien_source | text | nullable |
| horaires_accueil | text | nullable |
| accessibilite_lieu | text | nullable |
| reseaux_porteurs | text[] | nullable |
| _cluster_id | text | nullable |
| _has_valid_address | boolean | NOT NULL |
| _has_pii | boolean | NOT NULL |
| _in_opendata | boolean | NOT NULL |
| _is_valid | boolean | NOT NULL |
| _is_closed | boolean | NOT NULL |

**marts__services_v1** (39 cols, 345 MB, 180 160 lignes)

| Colonne | Type | Nullable |
|---|---|---|
| id | text | NOT NULL |
| structure_id | text | NOT NULL |
| source | text | NOT NULL |
| nom | text | nullable |
| conditions_acces | text | nullable |
| description | text | nullable |
| type | text | nullable |
| thematiques | text[] | nullable |
| frais | text | nullable |
| frais_precisions | text | nullable |
| publics | text[] | nullable |
| publics_precisions | text | nullable |
| commune, code_postal, code_insee, adresse, complement_adresse | text | nullable |
| longitude, latitude | double precision | nullable |
| horaires_accueil | text | nullable |
| lien_source | text | nullable |
| telephone, courriel, contact_nom_prenom | text | nullable |
| date_maj | date | nullable |
| lien_mobilisation | text | nullable |
| mobilisable_par, modes_accueil, modes_mobilisation, zone_eligibilite | text[] | nullable |
| volume_horaire_hebdomadaire | double precision | nullable |
| nombre_semaines | integer | nullable |
| score_qualite | double precision | nullable |
| _has_valid_address, _has_pii, _in_opendata, _is_valid | boolean | NOT NULL |
| _extra | jsonb | nullable |

### Tables de jonction v1

| Table | FK | Colonne |
|---|---|---|
| marts__services_thematiques_v1 | service_id | value |
| marts__services_publics_v1 | service_id | value |
| marts__services_modes_accueil_v1 | service_id | value |
| marts__services_modes_mobilisation_v1 | service_id | value |
| marts__services_mobilisable_par_v1 | service_id | value |
| marts__structures_reseaux_porteurs_v1 | structure_id | value |


## Schéma `public_schema` — énumérations

| Table | Lignes | Colonnes |
|---|---|---|
| thematiques_v1 | 69 | value, label, description |
| publics_v1 | 14 | value, label, description |
| modes_accueil_v1 | 2 | value, label, description |
| modes_mobilisation_v1 | | value, label, description |
| personne_mobilisatrice_v1 | | value, label, description |
| reseaux_porteurs_v1 | | value, label, description |
| types_de_services_v1 | | value, label, description |
| typologies_de_structures | 92 | value, label, description |
| frais_v1, labels_nationaux, zones_de_diffusion_types | | value, label, description |

## Schémas source bruts (Airflow)

Chaque producteur a son propre schéma contenant les données JSON brutes importées par les DAGs Airflow :

`action_logement`, `agefiph`, `annuaire_du_service_public`, `carif_oref`, `cd35`, `dora`, `emplois_de_linclusion`, `france_travail`, `fredo`, `ma_boussole_aidants`, `mediation_numerique`, `mes_aides`, `mission_locale`, `monenfant`, `reseau_alpha`, `soliguide`, `un_jeune_une_solution`, `decoupage_administratif`, `etat_civil`, `sirene`, `insee`.

## Raisons de disparition d'une donnée

1. **Non importée** — le DAG Airflow n'a pas extrait la donnée (schéma source brut vide)
2. **Filtrée au staging** — absente de `public_staging.stg_<source>__*`
3. **Non mappée** — absente de `public_intermediate.int_<source>__*_v1`
4. **Absente de l'union** — absente de `public_intermediate.int__union_*_v1`
5. **Géocodage échoué** — score BAN < seuil dans `int__geocodages_v1`
6. **SIRET fermé** — `_is_closed = true` dans `int__structures_v1`
7. **Invalidée** — `_is_valid = false`, erreurs dans `int__erreurs_validation_v1`
8. **Dédupliquée** — absorbée dans un cluster (`int__doublons_structures_v1`)
9. **Exclue de l'opendata** — `_in_opendata = false` (PII détecté)
