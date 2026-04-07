# Actes métiers — Indicateur transverse

Objectif central de la Plateforme : augmenter le volume des actes métiers réalisés
par les utilisateurs professionnels sur l'ensemble des services.

Un "acte métier" est une action à valeur métier significative : orientation d'un
bénéficiaire, candidature, mise en relation, distribution d'un outil, etc.

**Dashboard interactif :** `/interactive/actes-metier/`
**Conversation source :** `aa66951a` (Page stat V2)
**Script de génération :** `/app/data/scripts/actes_metier_data_v3.py`

## Structure de la donnée

Granularité : `mois × source × type_acte × categorie_acte × statut`

| Colonne | Valeurs |
|---------|---------|
| `mois` | YYYY-MM |
| `source` | rdvi, emplois, GPS, dora, monrecap, marche |
| `type_acte` | Voir tableau par source ci-dessous |
| `categorie_acte` | `Accompagnement` ou `Support à l'accompagnement` |
| `statut` | `Accompli et accepté`, `Accompli et refusé`, `En cours` |
| `nombre_actes` | Entier |

## Catégories

| Catégorie | Description |
|-----------|-------------|
| **Accompagnement** | Action directe auprès d'un bénéficiaire |
| **Support à l'accompagnement** | Action qui facilite ou prépare l'accompagnement |

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

## Services non couverts

| Service | Raison |
|---------|--------|
| Pilotage | Pas d'acte métier direct identifié |
| data·inclusion | Accès Metabase non disponible au moment de la création |
| Communauté | Non inclus dans la V1 |
| Plateforme (inclusion.gouv.fr) | Non inclus dans la V1 |

## Mise à jour des données

Le script `/app/data/scripts/actes_metier_data_v3.py` génère le fichier
`/app/data/interactive/actes-metier/data.json` utilisé par le dashboard.

À relancer manuellement ou via cron pour rafraîchir les données.
