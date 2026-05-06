# Actes métiers — Indicateur transverse

Objectif central de la Plateforme : augmenter le volume des actes métiers réalisés
par les utilisateurs professionnels sur l'ensemble des services.

Un "acte métier" est une action à valeur métier significative : orientation d'un
bénéficiaire, candidature, mise en relation, distribution d'un outil, etc.

**Dashboard interactif :** `/interactive/actes-metier/`
**Script de génération :** `/app/data/scripts/actes_metier_data_v5.py`

---

## Structure de la donnée

Granularité : `mois × source × type_acte × categorie_acte × type_structure`

| Colonne | Valeurs |
|---------|---------|
| `mois` | YYYY-MM |
| `source` | `rdvi`, `emplois`, `GPS`, `dora`, `monrecap`, `marche`, `data-inclusion` |
| `type_acte` | Voir tableau par source ci-dessous |
| `categorie_acte` | `Accompagnement` ou `Support` |
| `type_structure` | Code normalisé — voir section Type de structure |
| `north_star` | `true` si l'acte est qualifiant pour la North Star |
| `traite` | `true` si l'acte est traité (réponse reçue, sans contrainte de délai) |
| `nombre_actes` | Entier |

---

## North Star — définition et consolidation

### Définition métier

La North Star mesure le nombre de mises en relation traitées dans les 30 jours
suivant leur initiation, tous services confondus. Elle agrège uniquement les actes
dont `north_star = true`.

| Source | Condition `north_star = true` |
|--------|-------------------------------|
| RDV-i | Invitation avec RDV effectivement réservé (`nb_with_rdv > 0`) |
| Emplois | Candidature traitée (`état` sorti de la file d'attente) ET `date_traitement - date_candidature ≤ 30 jours` |
| Dora | Orientation avec statut `VALIDÉE` ou `REFUSÉE` |
| Marché | Diffusion d'offre avec au moins un SIAE matché (`siae_count > 0`) |
| Autres | `false` — ces actes n'entrent pas dans la North Star |

Le champ `traite` est distinct : il indique qu'une réponse a été donnée, sans
contrainte de délai (utile pour calculer les taux de réponse et les funnels).

### Consolidation des données

Certains actes North Star sont enregistrés avec un délai par rapport à leur date
d'initiation (ex. : une candidature traitée le 28 du mois suivant est comptée
dans le mois de candidature). Les derniers mois ont donc des comptages incomplets
jusqu'à ce que les délais soient écoulés.

**Règle de consolidation :** un mois M est dit "consolidé" si
`fin_du_mois_M + lag ≤ date_de_génération_du_fichier`.

Le lag appliqué **dépend de l'usage** :

| Usage | Lag | Exemple avec `generated_at = 2026-05-06` |
|-------|-----|------------------------------------------|
| Moy. mensuelle NS (KPI card) | 70 jours | Mois consolidés : jusqu'à jan. 2026 |
| Taux R1→NS (KPI card) | 70 jours | Idem |
| Croissance NS (KPI card) | 30 jours | Mois consolidés : jusqu'à fév. 2026 |
| Volume actes hors NS | Aucun | Tous les mois complets |

Les graphiques "Aperçu" et le tableau "Détail" affichent les **volumes bruts** sans
consolidation (les données récentes sont complètes pour tous les actes hors NS).
Seules les cartes KPI de l'onglet North Star appliquent la consolidation.

---

## Type de structure

Les actes sont ventilés par type d'organisation émettrice. Le mapping est défini
dans `STRUCT_MAP` (script v5) à partir des codes retournés par chaque source.

| Code normalisé | Description |
|----------------|-------------|
| `FRANCE_TRAVAIL` | France Travail (ex-Pôle Emploi) |
| `MISSION_LOCALE` | Mission locale |
| `CAP_EMPLOI` | Cap emploi |
| `CONSEIL_DEPARTEMENTAL` | Conseil départemental |
| `DELEGATAIRE_RSA` | Délégataire RSA |
| `CCAS_CIAS` | CCAS / CIAS |
| `JUSTICE_PROBATION` | SPIP / PJJ |
| `TS_HEBERGEMENT` | Structures d'hébergement (CHU, CHRS, CPH, CADA…) |
| `SIAE` | Structure d'insertion par l'activité économique |
| `PLIE` | PLIE |
| `E2C_EPIDE_AFPA` | E2C, Épide, AFPA, organismes de formation |
| `TS_SPECIALISES` | Structures spécialisées (CIDFF, CSAPA, AGEFIPH, FINESS…) |
| `CAF_MSA` | CAF / MSA |
| `AUTRES_INSERTION` | Autres structures d'insertion (PIJ-BIJ, OACAS…) |
| `Autre` | Non classifiable ou plateforme générique |
| `Inconnu` | Pas de type disponible dans la source |

Pour **data·inclusion**, le mapping est fait via `contexte_acte` (plateforme
consommatrice de l'API) grâce à `CONTEXTE_TYPE_STRUCTURE` (script v5). Les
contextes non mappés sont classés `Autre`. Les environnements de test/démo
(`emplois-demo-widget`, `emplois-pentest-widget`, etc.) sont exclus.

---

## Période couverte

`START_DATE = "2025-04-01"` — 13 mois : avr. 2025 → avr. 2026.

Le dernier mois complet (par rapport à `NOW()`) est inclus ; le mois en cours
est exclu de toutes les requêtes (`< DATE_TRUNC('month', NOW())`).

---

## Liste des actes par source

### RDV-Insertion

**Instance :** rdvi · **DB :** 2
**Tables :** `rdvi.invitations` + `rdvi.follow_ups` + `rdvi.participations` + `rdvi.rdvs` + `rdvi.motif_categories` + `rdvi.invitations_organisations`

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Invitation à un RDV d'orientation | Accompagnement | si RDV réservé |
| Invitation à un RDV d'accompagnement | Accompagnement | si RDV réservé |
| Invitation à un Entretien SIAE | Accompagnement | si RDV réservé |
| Invitation à un Autre RDV | Accompagnement | si RDV réservé |

L'acte unitaire est l'**invitation** (pas le RDV). Pour chaque invitation, deux
lignes peuvent exister : une avec `north_star = true` (invitation avec RDV) et
une avec `north_star = false` (sans RDV). Le `type_structure` vient de
`rdvi.organisations.organisation_type`.

---

### Les Emplois — Candidatures

**Instance :** stats · **DB :** 2
**Table :** `candidatures_echelle_locale`
**Filtre :** `injection_ai = 0`

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Candidature auprès d'un employeur solidaire | Accompagnement | si traité ≤ 30 j |

- `north_star = true` : état sorti de la file d'attente ET `date_traitement - date_candidature BETWEEN 0 AND 30`
- `traite = true` : état sorti de la file d'attente (sans contrainte de délai)
- `type_structure` : `type_org_prescripteur` via `STRUCT_MAP`

---

### Les Emplois — Fiches de poste

**Instance :** stats · **DB :** 2
**Table :** `fiches_de_poste`

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Création offre d'emploi | Support | false |
| Mise à jour offre d'emploi | Support | false |

La mise à jour n'est comptée que si `date_dernière_modification > date_création`.
`type_structure` : `type_employeur` via `STRUCT_MAP`.

---

### Les Emplois — Structures

**Instance :** stats · **DB :** 2
**Table :** `structures`

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Création employeur solidaire | Support | false |

`type_structure = SIAE` systématiquement.

---

### Les Emplois — Diagnostics IAE

**Instance :** stats · **DB :** 2
**Table :** `public.candidats`

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Diagnostic IAE | Accompagnement | false |

`type_structure` : extrait de `sous_type_auteur_diagnostic` (format "Prescripteur FT"
→ code FT) via `map_struct_diag`.

---

### Les Emplois — Recherches (Matomo)

**Instance Matomo :** inclusion (site 117)
**Méthode :** `VisitsSummary.get`

| Type acte | Catégorie | North Star | Segment |
|-----------|-----------|------------|---------|
| Recherche d'offre | Support | false | `pageUrl=@/search/employers/results` |
| Recherche de service | Support | false | `pageUrl=@/search/services/results` |

`type_structure = Inconnu` (pas d'info utilisateur dans Matomo).

---

### GPS (Mon Suivi)

**Instance :** stats · **DB :** 2
**Table :** `gps_logs_users`
**Filtre :** `group_id IS NOT NULL` et `view_name != 'gps:group_list'`

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Consultation groupe de suivi | Support | false |
| Mise à jour groupe de suivi | Support | false |

Consultation : `view_name IN ('gps:group_memberships', 'gps:group_beneficiary', 'gps:display_contact_info', 'gps:old_group_list')`.
`type_structure` : `type_org` via `STRUCT_MAP`.

---

### Dora — Orientations

**Instance :** dora · **DB :** 2
**Table :** `public.orientations_orientation`

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Orientation vers service | Accompagnement | si VALIDÉE ou REFUSÉE |

`type_structure` : `prescriber_structure.typology` via `STRUCT_MAP`.

---

### Dora — Intentions d'orientation (iMER)

**Instance :** dora · **DB :** 2
**Table :** `public_intermediate."int_iMER"`
**Filtre :** `user_kind IN ('accompagnateur', 'accompagnateur_offreur', 'offreur')`

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Intention d'orientation | Support | false |

`type_structure` : typologie de la structure de l'utilisateur (via JOIN sur
`structures_structuremember`).

---

### Dora — Fiches service

**Instance :** dora · **DB :** 2
**Table :** `services_service`

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Création ou diffusion offre de service, hors emploi solidaire | Support | false |
| Mise à jour offre de service, hors emploi solidaire | Support | false |

La MAJ n'est comptée que si `last_editor_id IS NOT NULL`. `type_structure` :
typologie de la structure propriétaire du service.

---

### Dora — Structures

**Instance :** dora · **DB :** 2
**Table :** `structures_structure`

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Création structure, hors employeur solidaire | Support | false |
| Mise à jour d'une structure d'offre de service, hors employeur solidaire | Support | false |

La MAJ n'est comptée que si `modification_date > creation_date`.

---

### Dora — Recherches de service

**Instance :** dora · **DB :** 2
**Table :** `stats_searchview`

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Recherche de service | Support | false |

Uniquement les utilisateurs loggés avec une structure connue. `type_structure` :
typologie de la première structure membre de l'utilisateur.

---

### Mon Récap — Distribution et remplissage

**Instance :** stats · **DB :** 2
**Table :** `monrecap."Commandes"`

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Distribution carnet Mon Récap | Accompagnement | false |
| Remplissage carnet Mon Récap | Support | false |

**⚠️ Proxy :** Les deux actes sont estimés à partir des carnets expédiés.

- **Distribution** : 10 % des carnets expédiés, réparti linéairement sur
  10 mois glissants après expédition (hypothèse : taux de distribution de 10 %/mois).
- **Remplissage** : taux de remplissage moyen de 109,3 %, actif entre le 1ᵉʳ et
  le 6ᵉ mois après expédition (fenêtre glissante de 6 mois).

La requête remonte depuis `2024-01-01` pour capter les carnets expédiés avant
`START_DATE` dont les actes estimés tombent dans la fenêtre d'analyse.

---

### Le Marché — Diffusion d'offre

**Instance :** stats · **DB :** 6
**Table :** `tenders_tender`
**Filtre :** `kind IN ('TENDER', 'PROJ', 'QUOTE')` et `status IN ('SUBMITTED', 'SENT')`

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Diffusion d'offre inclusive | Support | si `siae_count > 0` |

`type_structure` : `SIAE` si `users_user.kind = 'SIAE'`, sinon `Autre`.

---

### Le Marché — Mise à jour fiche entreprise

**Instance :** stats · **DB :** 6
**Tables :** `siaes_siaeoffer` + `siaes_siae`

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Mise à jour fiche entreprise | Support | false |

`type_structure = SIAE` systématiquement.

---

### data·inclusion

**Instance :** datalake · **DB :** 2
**Table :** `"stats_pdi-actes_metiers-data_inclusion"`
**Exclusions :** environnements de test (`emplois-demo-widget`, `emplois-pentest-widget`, `les-emplois-demo-2026-01`, `les-emplois-review-app-2026-01`)

| Type acte | Catégorie | North Star |
|-----------|-----------|------------|
| Recherche data·inclusion | Support | false |
| Mise à jour d'une structure d'offre de service, hors employeur solidaire | Support | false |
| Mise à jour offre de service, hors emploi solidaire | Support | false |

**Type de structure via `contexte_acte` :** la colonne indique quelle plateforme
consomme l'API data·inclusion pour effectuer la mise à jour. Le mapping
`CONTEXTE_TYPE_STRUCTURE` (script v5) convertit les 47 valeurs possibles en codes
normalisés. Valeurs mappées : `france-travail` → `FRANCE_TRAVAIL`, `les-emplois`/
`emplois-de-linclusion` → `SIAE`, `soliguide`/`action-logement`/... → `TS_HEBERGEMENT`,
`france-travail`/`mes-aides-france-travail`/`pilotage-réunion-france-travail` →
`FRANCE_TRAVAIL`, `monenfant` → `CAF_MSA`, `cd35`/`cd80-widget`/`hautespyrenees-widget`
→ `CONSEIL_DEPARTEMENTAL`, etc. Non mappés : `Autre` (dont `dora` 43 %, `mediation-numerique` 6 %,
`ma-boussole-aidants` 6 %).

---

## Services non couverts

| Service | Raison |
|---------|--------|
| Pilotage | Pas d'acte métier direct identifié |
| Communauté | Non inclus |
| Plateforme (inclusion.gouv.fr) | Non inclus |

---

## Mise à jour des données

```bash
python3 /app/data/scripts/actes_metier_data_v5.py
```

Génère `/app/data/interactive/actes-metier/data.json`. Le fichier inclut
`generated_at` (horodatage de génération) et `consolidation_lag_days` (30 j par
défaut — lag de référence pour les mois consolidés hors cartes NS à 70 j).

À relancer manuellement après récupération de nouvelles données historiques ou
pour mettre à jour `START_DATE` / `MONTHS` dans le script.
