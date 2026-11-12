---
source: [metabase:stats, metabase:dora, metabase:rdvi, metabase:datalake, autometa_tables_db, matomo, datadog]
verifie_le: 2026-11-06
---
# Actes métiers — Indicateur transverse

Objectif central de la Plateforme : augmenter le volume des actes métiers réalisés
par les utilisateurs professionnels sur l'ensemble des services.

Un « acte métier » est une action à valeur métier significative : orientation d'un
bénéficiaire, candidature, mise en relation, distribution d'un outil, etc.

L'acte métier est l'**unité de compte unique** et le **North Star** (étape Impact) du funnel bizdev — voir [glossaire AARRI](../bizdev/glossaire.md). Ce fichier est la source de vérité de la liste des types d'actes.

**Tableau de bord :** `/interactive/actes-metier/`. Le pipeline, ses scripts et le format de `data.json` sont décrits dans `data/interactive/actes-metier/APP.md` : la référence pour l'implémentation, c'est ce fichier-là.
**Snapshot historique :** `matometa.pdi_actes_metier_snapshot_annuel` (datalake), depuis avril 2025 (mars 2025 incomplet).

## Structure de la donnée

Granularité : `mois × source × type_acte × north_star × north_star_70 × traite × type_structure × departement`

| Colonne | Valeurs |
|---------|---------|
| `mois` | YYYY-MM |
| `source` | `rdvi`, `emplois`, `GPS`, `dora`, `monrecap`, `marche`, `data-inclusion` |
| `type_acte` | Voir la liste ci-dessous |
| `categorie_acte` | `Accompagnement` (action directe auprès d'un bénéficiaire) ou `Support` (action qui facilite ou prépare l'accompagnement) |
| `north_star` | Acte de rang 1 traité en **30 jours** au plus |
| `north_star_70` | Acte de rang 1 traité en **59 jours** au plus (le nom de la colonne est historique) |
| `traite` | Acte de rang 1 traité, quel que soit le délai (absent du snapshot) |
| `type_structure` | Type normalisé de la structure qui réalise l'acte (FRANCE_TRAVAIL, SIAE, CONSEIL_DEPARTEMENTAL…, `Autre`) |
| `departement` | Code INSEE (ex. `75`, `2A`, `971`) ou `Inconnu` |
| `nombre_actes` | Entier |

## Rangs

| Rang | Sens | Actes |
|------|------|-------|
| **R1 — Intermédiation** | Mise en contact effective entre acteurs | Candidatures, prolongations de PASS IAE, invitations RDV-i, orientations vers service, intentions d'orientation, diffusions d'offre Marché |
| **R2 — Engagement pro** | Usage des outils par les accompagnateurs | Diagnostics IAE, recherches, GPS, Mon Récap, bilans de fin de parcours |
| **R3 — Qualité de l'offre** | Fraîcheur et complétude de l'offre référencée | Créations et mises à jour d'offres, de services et de structures |

## North Star

**Définition :** acte de rang 1 qui a reçu un retour humain (traité).

**Délai de référence : 30 jours.** Toujours utiliser la North Star à 30 jours (`north_star`)
dans les analyses, sauf demande explicite contraire. La variante longue (`north_star_70`)
est calculée à **59 jours**, pas 70 : son nom de colonne est resté, mais le délai a changé.
Elle ne sert qu'au volume de la carte « North Star » du tableau de bord, sur des mois consolidés.

| Acte de rang 1 | Règle « traité » |
|----------------|------------------|
| Candidature auprès d'un employeur solidaire | Réponse (acceptée, refusée…) dans le délai, hors injection IA |
| Prolongation de PASS IAE | Toujours traitée : 100 % comptées, accordées à la demande en moins de 30 jours |
| Invitation à un RDV (RDV-i) | Invitation suivie d'un RDV réservé |
| Orientation vers service — Dora et Emplois | Statut `VALIDÉE` ou `REFUSÉE` |
| Orientation vers service — RDV-i | **Proxy** : 80 % traitées (taux moyen des RDV d'orientation), l'acceptation par l'usager n'étant pas tracée |
| Orientation vers service — data·inclusion | **Proxy** : 55 % traitées (taux de traitement moyen des orientations Dora sur 12 mois) |
| Diffusion d'offre inclusive (Marché) | Offre reçue par au moins une SIAE (`siae_count > 0`) |
| Intention d'orientation (iMER) | Jamais : exclue du taux North Star, elle ne peut pas être traitée par définition |

Les taux par proxy sont appliqués mois par mois, et les volumes sont répartis en entiers par la méthode des plus forts restes.

### Consolidation temporelle

Le statut d'un acte de rang 1 évolue après sa création : une candidature peut recevoir sa réponse des semaines plus tard.
Le mois M n'est donc comparable qu'une fois son délai écoulé.

| Calcul | Périmètre | Mois retenus |
|--------|-----------|--------------|
| Croissance mensuelle et annuelle North Star (**référence**) | `north_star` (30 j) | Mois dont la fin date de plus de 30 jours |
| Volume North Star (carte KPI) | `north_star_70` (59 j) | Mois dont la fin date de plus de 59 jours |
| Volumes, taux et comparaisons hors North Star | Tous les actes | Aucun délai |

## Liste des actes

L'acte « Orientation vers service » a quatre sources : Dora, Emplois, RDV-i et data·inclusion. Elles se somment sous un même libellé, et le filtre par source permet de les séparer.

### RDV-Insertion (`rdvi`)

| Acte | Cat. · Rang | Table | Notes |
|------|-------------|-------|-------|
| Invitation à un RDV d'orientation / d'accompagnement / Entretien SIAE / Autre RDV | Accompagnement · R1 | Metabase rdvi : `rdvi.invitations` + `follow_ups` + `participations` + `rdvs` + `motif_categories` | Date = création de l'invitation · département de l'invitation · type = organisation |
| Orientation vers service | Accompagnement · R1 | `raw_rdvi.orientations` (orientation directe, sans RDV) + `raw_rdvi.post_rdv_orientations` (orientation décidée à l'issue d'un RDV) | Les deux sources sont sommées sans distinction · date = `created_at` · département et type de l'organisation (via le RDV pour le post-RDV) · North Star par proxy à 80 % · **le post-RDV n'existe que depuis mai 2026**, d'où une rupture de série |

### Les Emplois (`emplois`)

| Acte | Cat. · Rang | Table | Notes |
|------|-------------|-------|-------|
| Candidature auprès d'un employeur solidaire | Accompagnement · R1 | `candidatures_echelle_locale` | Hors `injection_ai` · type et département de l'organisation prescriptrice |
| Prolongation de PASS IAE | Accompagnement · R1 | `raw_emplois.prolongations` | Date = `date_de_création` · département de la SIAE déclarante, type `SIAE` · 100 % North Star · ~1 400 à 2 900 par mois |
| Orientation vers service, Intention d'orientation | Accompagnement · R1 / Support · R1 | `fct_dora__orientations`, `fct_dora__imer` (`origin_source = 'emplois'`) | Depuis juillet 2026 |
| Diagnostic IAE | Accompagnement · R2 | `candidats` (`date_diagnostic`) | Comptage distinct |
| Recherche d'offre d'emploi | Support · R2 | Matomo, site 117, visites sur `/search/employers/results` | Département estimé via la dimension 4 (voir « Dimension territoriale ») |
| Recherche d'offre de service, hors emploi solidaire | Support · R2 | Matomo, site 117, visites sur `/search/services/results` | Depuis janvier 2026 · département × type estimés via les dimensions 4 × 3 |
| Création d'un bilan de fin de parcours | Accompagnement · R2 | `raw_emplois.bilans_accompagnement_v0` | Date = `date_de_création` (heure de Paris) · type et département de la SIAE auteure · **depuis le 28/10/2026** |
| Consultation d'un bilan de fin de parcours | Support · R2 | Lectures Datadog de la page du bilan, stockées dans `dashboard_storage.fin_parcours_bilan_vues` par le tableau de bord `fin-parcours-adoption` | Un couple bilan × prescripteur compte **une fois**, au mois de sa première lecture réussie (HTTP 200, membre d'une organisation prescriptrice) · type et département de l'organisation du lecteur · depuis le 28/10/2026 |
| Création employeur solidaire | Support · R3 | `structures` (`date_inscription`) | |
| Création / Mise à jour offre d'emploi | Support · R3 | `fiches_de_poste` | Mise à jour : `date_dernière_modification > date_création` |

### GPS (`GPS`)

| Acte | Cat. · Rang | Table | Notes |
|------|-------------|-------|-------|
| Consultation groupe de suivi, Mise à jour groupe de suivi | Support · R2 | Jusqu'au 31/08/2026 : `gps_logs_users` · depuis le 01/09/2026 : événements Matomo du site 117, collectés chaque jour | **Rupture de série en septembre 2026** · juillet et août 2026 sous-estimés |

### Dora (`dora`)

| Acte | Cat. · Rang | Table | Notes |
|------|-------------|-------|-------|
| Orientation vers service | Accompagnement · R1 | `fct_dora__orientations` | North Star = `VALIDÉE` ou `REFUSÉE` |
| Intention d'orientation (iMER partiel) | Support · R1 | `fct_dora__imer`, utilisateurs accompagnateurs ou offreurs | ⚠️ Ce n'est pas l'iMER complet de `knowledge/dora/README.md` : ses orientations recouvrent l'acte ci-dessus, et sommer les deux fait un double compte |
| Recherche d'offre de service, hors emploi solidaire | Support · R2 | `raw_dora.stats_searchview` | Une ligne par recherche, utilisateurs anonymes inclus |
| Création ou diffusion offre de service, Mise à jour offre de service | Support · R3 | `services_service` | La mise à jour exige `last_editor_id` non nul |
| Création structure, Mise à jour d'une structure d'offre de service | Support · R3 | `structures_structure` | |

### data·inclusion (`data-inclusion`)

| Acte | Cat. · Rang | Table | Notes |
|------|-------------|-------|-------|
| Recherche data·inclusion | Support · R2 | Datalake `stats_pdi-actes_metiers-data_inclusion` | Hebdomadaire, sans contextes de test · type déduit de `contexte_acte` |
| Orientation vers service (estimée) | Accompagnement · R1 | Dérivée de l'acte « Recherche data·inclusion » | **Proxy : 0,3 % des recherches** du mois, réparties par département et type comme les recherches · North Star par proxy à 55 % · ~50 à 430 par mois |
| Mise à jour offre de service, Mise à jour d'une structure d'offre de service | Support · R3 | Datalake (même table) | Type déduit de `reseaux_porteurs` (~40 % classés « Autre ») |

### Mon Récap (`monrecap`)

| Acte | Cat. · Rang | Table | Notes |
|------|-------------|-------|-------|
| Distribution carnet Mon Récap | Accompagnement · R2 | `monrecap."Commandes"` | **Proxy** : 10 % des carnets expédiés distribués chaque mois pendant 10 mois |
| Remplissage carnet Mon Récap | Support · R2 | `monrecap."Commandes"` | **Proxy** : un carnet reste actif 6 mois, × 1,093 remplissage par mois et par carnet actif |

Depuis les commandes d'avril 2026, la date d'expédition n'est plus saisie : elle est estimée à la date de fabrication + 7 jours.

### Le Marché (`marche`)

| Acte | Cat. · Rang | Table | Notes |
|------|-------------|-------|-------|
| Diffusion d'offre inclusive | Support · R1 | Metabase stats, base 6 : `tenders_tender` (`kind IN ('TENDER','PROJ','QUOTE')`, `status IN ('SUBMITTED','SENT')`) | North Star = `siae_count > 0` |
| Mise à jour fiche entreprise | Support · R3 | `siaes_siaeoffer` + `siaes_siae` | |

## Dimension territoriale

| Source / acte | Méthode | Géolocalisation |
|---------------|---------|-----------------|
| RDV-i (invitations, orientations) | Département en base | ~100 % pour les orientations |
| Emplois — candidatures, diagnostics, offres, prolongations, bilans | Département de la structure ou de l'organisation en base | ~100 % pour les prolongations et les bilans |
| Emplois — recherches (Matomo) | Proxy par la dimension Matomo 4 (`UserDepartment`), appliqué au volume du mois | ~65 à 71 % |
| GPS, Dora, Marché, Mon Récap | Département de la structure en base | 80 à 95 % |
| data·inclusion (et ses orientations estimées) | Champ département de la table du datalake | Élevée |

Les recherches Emplois sont géolocalisées par proxy : c'est la répartition des visiteurs de la page de résultats, pas une attribution acte par acte.

## Croissance annuelle et snapshot

- Le snapshot (datalake) conserve l'historique au-delà des 14 mois de `data.json`. Il n'a pas la colonne `traite`.
- Les **nouveaux actes sont réinjectés dans le snapshot depuis avril 2025**, pour que la croissance annuelle compare des périmètres homogènes. Les prolongations et les orientations RDV-i directes existent sur toute la période ; les orientations post-RDV (depuis mai 2026), les orientations estimées data·inclusion (depuis fin 2025) et les bilans (depuis octobre 2026) n'ont pas d'historique antérieur et comptent donc comme de la croissance.
- Recalcul du 6 novembre 2026 : la croissance annuelle de la North Star 30 j passe, par exemple, de +20,0 % à +21,2 % en septembre 2026 et de +18,3 % à +22,5 % en août 2026.

## Services non couverts

| Service | Raison |
|---------|--------|
| Pilotage | Pas d'acte métier direct identifié |
| Communauté | Non inclus |
| Site institutionnel (inclusion.gouv.fr) | Non inclus |

## Historique des changements

| Date | Changement |
|------|------------|
| 2026-11-06 | Ajout : prolongations de PASS IAE (R1), orientations RDV-i (R1, proxy 80 %), orientations estimées data·inclusion (R1, 0,3 % des recherches, proxy 55 %), création et consultation des bilans de fin de parcours (R2). Recalcul de la fenêtre, du snapshot depuis avril 2025 et de l'historique de croissance annuelle |
| 2026-09 | GPS : bascule des logs applicatifs vers Matomo |
| 2026-07 | Orientations et intentions d'orientation depuis les Emplois |
| — | North Star longue ramenée de 70 à 59 jours (colonne `north_star_70` conservée) ; la North Star à 30 jours devient la référence des analyses |
