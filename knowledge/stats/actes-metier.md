# Actes métiers — Indicateur transverse

Objectif central de la Plateforme : augmenter le volume des actes métiers réalisés
par les utilisateurs professionnels sur l'ensemble des services.

Un « acte métier » est une action à valeur métier significative : orientation d'un
bénéficiaire, candidature, mise en relation, distribution d'un outil, etc.

**Dashboard interactif :** `/interactive/actes-metier/`
**Conversation source :** `aa66951a` (Page stat V2)
**Script de génération :** `/app/data/scripts/actes_metier_data_v3.py`

## Structure de la donnée

Granularité : `mois × source × type_acte × categorie_acte × statut × departement`

| Colonne | Valeurs |
|---------|---------|
| `mois` | YYYY-MM |
| `source` | rdvi, emplois, GPS, dora, monrecap, marche |
| `type_acte` | Voir tableau par source ci-dessous |
| `categorie_acte` | `Accompagnement` ou `Support à l'accompagnement` |
| `statut` | `Accompli et accepté`, `Accompli et refusé`, `En cours` |
| `departement` | Code INSEE (ex. `75`, `59`, `971`) ou `Inconnu` |
| `nombre_actes` | Entier |

## Catégories

| Catégorie | Description |
|-----------|-------------|
| **Accompagnement** | Action directe auprès d'un bénéficiaire |
| **Support à l'accompagnement** | Action qui facilite ou prépare l'accompagnement |

## Règles de calcul

### Consolidation temporelle (North Star uniquement)

Certains actes changent de statut après la date de réalisation (ex. : une candidature
initialement « en attente » peut être acceptée ou refusée des semaines plus tard).
Pour mesurer la performance North Star, des délais de consolidation sont appliqués.

| Calcul | Périmètre | Délai appliqué |
|--------|-----------|----------------|
| Volume North Star (KPI principal) | Actes NS uniquement | 70 jours |
| Croissance mensuelle North Star | Actes NS uniquement | 30 jours |
| Croissance mensuelle moyenne (hors NS) | Tous les actes | Aucun |
| Comparaison 3 derniers mois vs 3 précédents | Tous les actes | Aucun |
| Volumes et taux hors NS | Tous les actes | Aucun |

**Règle pratique :** seuls les calculs qui pilotent la North Star utilisent des mois
consolidés. Tous les autres indicateurs (croissance, comparaisons, treemap) utilisent
les données complètes jusqu'au mois le plus récent disponible.

Exemple avec `generated_at = 2026-05-06` :
- Mois consolidés NS (70 j) : jusqu'à février 2026
- Mois consolidés croissance NS (30 j) : jusqu'à mars 2026
- Derniers 3 mois (hors NS) : février, mars, avril 2026
- 3 mois précédents (hors NS) : novembre 2025, décembre 2025, janvier 2026

---

## Liste des actes par source

### RDV-Insertion

**Instance :** rdvi · **DB :** 2
**Table :** `rdvi.participations` + `rdvi.rdvs` + `rdvi.motif_categories`

| Type acte | Catégorie | Statuts possibles |
|-----------|-----------|-------------------|
| RDV d'orientation | Accompagnement | Accompli et accepté, Accompli et refusé, En cours |
| RDV d'accompagnement | Accompagnement | Accompli et accepté, Accompli et refusé, En cours |
| Entretien SIAE | Accompagnement | Accompli et accepté, Accompli et refusé, En cours |
| Autre RDV | Accompagnement | Accompli et accepté, Accompli et refusé, En cours |

Mapping statut : `seen` → Accompli et accepté · `unknown` → En cours · autres → Accompli et refusé

---

### Les Emplois — Candidatures

**Instance :** stats · **DB :** 2
**Table :** `candidatures_echelle_locale`

| Type acte | Catégorie | Statuts possibles |
|-----------|-----------|-------------------|
| Candidature auprès d'un employeur solidaire | Accompagnement | Accompli et accepté, Accompli et refusé, En cours |

Mapping statut :
- Accompli et accepté : `Candidature acceptée`, `Embauché ailleurs`, `Action préalable à l'embauche`, `Embauche annulée`
- Accompli et refusé : `Candidature déclinée`, `Candidature en vivier`
- En cours : tous les autres états (en attente, à l'étude, etc.)

---

### Les Emplois — Recherche d'offre

**Instance :** Matomo · **ID site :** 117
**Méthode :** vues de page sur `/search/employers/results`

| Type acte | Catégorie | Statut |
|-----------|-----------|--------|
| Recherche d'offre | Support à l'accompagnement | Accompli et accepté |

**Note :** Cet acte est tracé via Matomo (pas de table DB). Le département est estimé
par enrichissement — voir section « Dimension territoriale » ci-dessous.

---

### GPS (Mon Suivi)

**Instance :** stats · **DB :** 2
**Table :** `gps_logs_users` (filtre : `group_id IS NOT NULL` et `view_name != 'gps:group_list'`)

| Type acte | Catégorie | Statut |
|-----------|-----------|--------|
| Consultation groupe de suivi | Support à l'accompagnement | Accompli et accepté |
| Mise à jour groupe de suivi | Support à l'accompagnement | Accompli et accepté |

Mapping type :
- Consultation : `gps:group_memberships`, `gps:group_beneficiary`, `gps:display_contact_info`, `gps:old_group_list`
- Mise à jour : tous les autres `view_name`

---

### Dora — Orientations

**Instance :** dora · **DB :** 2
**Table :** `public_intermediate.int_orientation_user_service`

| Type acte | Catégorie | Statuts possibles |
|-----------|-----------|-------------------|
| Orientation vers service | Accompagnement | Accompli et accepté, Accompli et refusé, En cours |

Mapping statut : `VALIDÉE` → accepté · `REFUSÉE`/`EXPIRÉE` → refusé · autres → En cours

---

### Dora — iMER (intention de mise en relation)

**Instance :** dora · **DB :** 2
**Table :** `public_intermediate.int_iMER`
**Filtre :** `user_kind IN ('accompagnateur', 'accompagnateur_offreur', 'offreur')`

| Type acte | Catégorie | Statut |
|-----------|-----------|--------|
| Mise en relation (iMER) | Support à l'accompagnement | Accompli et accepté |

---

### Dora — Mise à jour fiche service

**Instance :** dora · **DB :** 2
**Table :** `services_service`
**Filtre :** `last_editor_id IS NOT NULL`

| Type acte | Catégorie | Statut |
|-----------|-----------|--------|
| Mise à jour fiche service | Support à l'accompagnement | Accompli et accepté |

---

### Mon Récap — Distribution

**Instance :** stats · **DB :** 2
**Table :** `monrecap."Commandes"`

| Type acte | Catégorie | Statut |
|-----------|-----------|--------|
| Distribution carnet Mon Récap | Accompagnement | Accompli et accepté |

**⚠️ Proxy :** Faute de données directes, l'acte est estimé à 10 % des carnets
distribués sur une fenêtre glissante de 9 mois (taux de distribution moyen).

---

### Mon Récap — Remplissage

**Instance :** stats · **DB :** 2
**Table :** `monrecap."Commandes"`

| Type acte | Catégorie | Statut |
|-----------|-----------|--------|
| Remplissage carnet Mon Récap | Support à l'accompagnement | Accompli et accepté |

**⚠️ Proxy :** Estimé à partir d'un taux de remplissage moyen de 62 % par carnet,
réparti sur une fenêtre de 6 à 16 mois après distribution.

---

### Le Marché — Diffusion d'offre

**Instance :** stats · **DB :** 6
**Table :** `tenders_tender`
**Filtre :** `kind IN ('TENDER', 'PROJ', 'QUOTE')` et `status IN ('SUBMITTED', 'SENT')`

| Type acte | Catégorie | Statuts possibles |
|-----------|-----------|-------------------|
| Diffusion d'offre inclusive | Support à l'accompagnement | Accompli et accepté, En cours |

Mapping statut : `SENT` → accepté · autres → En cours

---

### Le Marché — Mise à jour fiche entreprise

**Instance :** stats · **DB :** 6
**Table :** `siaes_siaeoffer` + `siaes_siae`

| Type acte | Catégorie | Statut |
|-----------|-----------|--------|
| Mise à jour fiche entreprise | Support à l'accompagnement | Accompli et accepté |

---

## Dimension territoriale

### Couverture par source

| Source | Actes couverts | Méthode | Taux géolocalisation |
|--------|---------------|---------|---------------------|
| RDV-Insertion | Tous | Champ `departement` en DB | ~95 % |
| Les Emplois — Candidatures | Candidature... | Département candidat en DB | ~90 % |
| Les Emplois — Recherche d'offre | Recherche d'offre | Estimation via Matomo dim. 4 | ~71 % |
| GPS | Tous | Département structure en DB | ~85 % |
| Dora | Tous | Département structure en DB | ~90 % |
| Mon Récap | Tous | Département structure en DB | ~80 % |
| Le Marché | Tous | Département structure en DB | ~85 % |

### Enrichissement « Recherche d'offre » via Matomo dimension 4

**Problème :** l'acte « Recherche d'offre » (source `emplois`) est tracé via Matomo comme
vue de page sur `/search/employers/results`. L'événement Matomo ne capture pas le
département de l'utilisateur — toutes les lignes étaient stockées avec `departement='Inconnu'`.

**Solution (appliquée depuis mai 2026) :** la dimension custom Matomo 4 (`UserDepartment`,
action-scoped) filtrée sur la page de résultats donne la distribution des visites
géolocalisées par département. Cette distribution est appliquée au volume mensuel total
de l'acte comme proxy de ventilation.

| Paramètre | Valeur |
|-----------|--------|
| Site | emplois (idSite=117) |
| Dimension | 4 (UserDepartment) |
| Segment | `pageUrl=@/search/employers/results` |
| Métrique | `nb_visits` par département |
| `filter_limit` | 200 |

**Méthode de calcul :**
1. Pour chaque mois, requête Matomo dim4 → distribution `{dept: fraction_du_total_visites}`
2. Seules les visites avec département connu (hors `Value not defined`) contribuent à la distribution
3. Chaque fraction est appliquée au volume mensuel total de l'acte
4. Le volume résiduel (arrondi) est conservé en `Inconnu`

**Résultats observés (13 mois, avril 2025 – avril 2026) :**
- ~71 % des actes géolocalisés (102–104 départements selon les mois)
- ~29 % conservés en `Inconnu` (sessions sans dimension département)
- Le Nord (59) est le premier département (~5–8 % du total géolocalisé)

**Limites :**
- Distribution proxy (visiteurs de la page), pas attribution exacte par acte
- Un visiteur qui consulte la page plusieurs fois dans le mois compte plusieurs fois
- Ne couvre pas « Recherche de service » (déjà géolocalisé à 95 % via DB)

---

## Services non couverts

| Service | Raison |
|---------|--------|
| Pilotage | Pas d'acte métier direct identifié |
| data·inclusion | Accès Metabase non disponible au moment de la création |
| Communauté | Non inclus dans la V1 |
| Plateforme (inclusion.gouv.fr) | Non inclus dans la V1 |

---

## Mise à jour des données

Le script `/app/data/scripts/actes_metier_data_v3.py` génère le fichier
`/app/data/interactive/actes-metier/data.json` utilisé par le dashboard.

Après chaque regénération de `data.json`, relancer l'enrichissement département :

```bash
cd /app && python data/interactive/actes-metier/enrich_dept.py
