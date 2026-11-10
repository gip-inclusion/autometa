---
source: [metabase:stats, metabase:dora, metabase:rdvi, metabase:datalake, autometa_tables_db, matomo]
verifie_le: 2026-11-10
---
# Actes métiers — Indicateur transverse

Objectif central de la PDI : augmenter le volume des actes métiers réalisés
par les utilisateurs professionnels sur l'ensemble des services.

Un « acte métier » est une action à valeur métier significative : orientation d'un
bénéficiaire, candidature, mise en relation, distribution d'un outil, etc.

L'acte métier est l'**unité de compte unique** et le **North Star** (étape Impact) du funnel bizdev — voir [glossaire AARRI](../bizdev/glossaire.md). Ce fichier est la source de vérité de la liste des types d'actes.

**Dashboard interactif :** `/interactive/actes-metier/`
**Calcul :** le `cron.py` du TDB lance `actes_metier_update.py` le 1er de chaque mois. Ce fichier décrit ce que calculent les scripts de production au 2026-11-06 ; en cas d'écart, le script fait foi.

## Structure de la donnée

`data.json` couvre une fenêtre glissante de 14 mois. Granularité :
`mois × source × type_acte × north_star × north_star_70 × traite × type_structure × departement`.

| Colonne | Valeurs |
|---------|---------|
| `mois` | YYYY-MM, mois de l'acte |
| `source` | `rdvi`, `emplois` (La plateforme), `GPS`, `dora`, `marche`, `monrecap`, `data-inclusion` |
| `type_acte` | Libellés exacts dans les tableaux ci-dessous, apostrophes typographiques (’) comprises |
| `categorie_acte` | `Accompagnement` (action directe auprès d'un bénéficiaire) ou `Support` (action qui la prépare ou la facilite) |
| `north_star` | Acte de rang 1 ayant reçu un retour humain, selon la règle de l'acte (tableaux ci-dessous). Seules les candidatures ont une condition de délai : réponse dans les 30 jours |
| `north_star_70` | Idem avec un délai de **59** jours pour les candidatures, malgré son nom ; égal à `north_star` pour les autres actes |
| `traite` | Candidatures : réponse reçue, quel que soit le délai ; autres actes : égal à `north_star` |
| `type_structure` | Type de la structure qui fait l'acte (`FRANCE_TRAVAIL`, `MISSION_LOCALE`, `SIAE`, `CONSEIL_DEPARTEMENTAL`…, `Autre`, `Inconnu`) |
| `departement` | Code INSEE (`75`, `2A`, `971`) ou `Inconnu` |
| `nombre_actes` | Entier ; estimé pour les actes par proxy |

`yoy_ref` porte, pour le mois situé 12 mois avant M-2, les actes de rang 1 en North Star : c'est la référence de la croissance annuelle, hors fenêtre.

## Rangs et North Star

Le rang n'est pas une colonne : il découle du type d'acte.

| Rang | Sens |
|------|------|
| 1 — Intermédiation | Mise en contact effective entre acteurs : candidatures, prolongations de PASS IAE, invitations à un RDV, orientations, intentions d'orientation, diffusion d'offre du Marché |
| 2 — Engagement pro | Usage des outils d'accompagnement : recherches, diagnostics, GPS, Mon Récap, bilans de fin de parcours |
| 3 — Qualité de l'offre | Création et mise à jour de fiches (offres, services, structures) |

**North Star = actes de rang 1 ayant reçu un retour humain**, selon la règle propre à chaque acte (colonne « North Star » des tableaux). La référence est `north_star` (candidatures traitées dans les 30 jours) ; `north_star_70` (59 jours pour les candidatures) sert au volume consolidé de l'onglet North Star. « Intention d'orientation » est de rang 1 mais jamais North Star, et sort du taux rang 1 → North Star.

Un indicateur North Star ne retient que des **mois consolidés** : mois dont la fin date d'au moins 30 jours (59 jours pour `north_star_70`) à la génération des données.

## Mise à jour des données

- Le 1er de chaque mois, le mois écoulé entre dans la fenêtre, et chaque mois est recalculé quand 30 puis 59 jours se sont écoulés depuis sa fin : les délais de traitement s'y complètent.
- Les actes de mise à jour d'une fiche déjà présents ne sont pas recalculés, sauf s'ils valaient 0 : ils sont datés par la dernière modification, qu'une modification ultérieure déplacerait.
- Mon Récap est recalculé sur toute la fenêtre.
- Si le total d'actes baisse de plus de 10 %, `data.json` n'est pas écrit.
- Chaque mois, les données sont recopiées dans la table `pdi_actes_metier_snapshot_annuel` (schéma `matometa`, datalake), sans la colonne `traite`. L'historique de croissance annuelle au-delà de la fenêtre en est tiré.
- Les actes ajoutés en novembre 2026 (prolongations, orientations RDV-i et data·inclusion, bilans) ont été recalculés sur toute la fenêtre et dans le snapshot depuis avril 2025.

---

## Liste des actes par source

### RDV-Insertion

**Instance :** rdvi · **DB :** 2 (invitations) ; `autometa_tables_db`, schéma `raw_rdvi` (orientations)

| Type acte | Catégorie | Rang | Donnée, date | North Star |
|-----------|-----------|------|--------------|------------|
| Invitation à un RDV d’orientation | Accompagnement | 1 | Invitations, date de création ; type selon la catégorie de motif | Le suivi de l'invitation compte au moins un RDV, sans condition de délai (même antérieur à l'invitation) |
| Invitation à un RDV d’accompagnement | Accompagnement | 1 | idem | idem |
| Invitation à un Entretien SIAE | Accompagnement | 1 | idem | idem |
| Invitation à un Autre RDV | Accompagnement | 1 | idem | idem |
| Orientation vers service | Accompagnement | 1 | `orientations` et `post_rdv_orientations` (ces dernières depuis mai 2026), date de création | **Proxy** : 80 % comptées traitées (taux moyen des RDV d'orientation) ; l'acceptation par l'usager n'est pas tracée |

Type de structure : type de l'organisation. Département : celui de l'invitation, ou de l'organisation pour les orientations.

---

### La plateforme (ex-Emplois)

**Instance :** stats · **DB :** 2 ; `autometa_tables_db` (prolongations, bilans) ; Matomo site 117 (recherches)

| Type acte | Catégorie | Rang | Donnée, date | North Star |
|-----------|-----------|------|--------------|------------|
| Candidature auprès d’un employeur solidaire | Accompagnement | 1 | `candidatures_echelle_locale`, date de candidature, hors candidatures injectées par l'IA | Réponse (ni nouvelle, ni en attente, ni à l'étude) dans les 30 jours |
| Prolongation de PASS IAE | Accompagnement | 1 | `raw_emplois.prolongations`, date de création | Toujours (accordée à la demande) |
| Diagnostic IAE | Accompagnement | 2 | `public.candidats`, date du diagnostic, candidats distincts | — |
| Création d’un bilan de fin de parcours | Accompagnement | 2 | `raw_emplois.bilans_accompagnement_v0`, date de création (heure de Paris) ; depuis le 28/10/2026 | — |
| Consultation d’un bilan de fin de parcours | Support | 2 | Lectures réussies par un membre d'une organisation prescriptrice, collectées dans Datadog par le TDB `fin-parcours-adoption` ; un couple bilan × lecteur compte une fois, au mois de la première lecture | — |
| Recherche d’offre d’emploi | Support | 2 | Matomo : **visites** comportant une page `/search/employers/results` | — |
| Recherche d’offre de service, hors emploi solidaire | Support | 2 | Matomo : visites comportant une page `/search/services/results` ; depuis janvier 2026 | — |
| Création offre d’emploi | Support | 3 | `fiches_de_poste`, date de création | — |
| Mise à jour offre d’emploi | Support | 3 | `fiches_de_poste`, date de dernière modification, si postérieure à la création | — |
| Création employeur solidaire | Support | 3 | `structures`, date d'inscription | — |

Département d'une candidature : celui de l'organisation prescriptrice, à défaut celui de la SIAE employeuse. Prolongation : SIAE déclarante. Consultation de bilan : organisation du lecteur.

Les recherches comptent des visites, jamais des pages vues : chaque filtre ou page de résultats compterait une fois de plus. Le département d'une recherche d'offre d'emploi est estimé en répartissant le total selon la dimension Matomo 4 (`UserDepartment`) des visites concernées ; le reste demeure `Inconnu`. Pour la recherche d'offre de service, département et type restent `Inconnu`.

---

### GPS (Mon Suivi)

| Type acte | Catégorie | Rang | Donnée, date |
|-----------|-----------|------|--------------|
| Consultation groupe de suivi | Support | 2 | Jusqu'au 31/08/2026 : `gps_logs_users` (stats, DB 2), vues `gps:group_memberships`, `gps:group_beneficiary`, `gps:display_contact_info`, `gps:old_group_list`. Depuis le 01/09/2026 : événements Matomo du site 117, collectés chaque jour |
| Mise à jour groupe de suivi | Support | 2 | Mêmes sources, toutes les autres vues |

**Rupture de série au 1er septembre 2026** : GPS a rejoint La plateforme et ses logs ne sont plus alimentés. Les deux sources n'ont pas été rapprochées. Juillet et août 2026 sont fortement sous-estimés (les logs ne captent plus qu'une partie de l'activité), le 29 au 31 août 2026 n'a aucune donnée, les volumes Matomo sont très faibles du 1er au 8 septembre 2026 (montée en charge probable du marquage) et nuls le 7 septembre.

---

### Dora — Orientations

**Source :** `autometa_tables_db`, `public.fct_dora__orientations`

| Type acte | Catégorie | Rang | Donnée, date | North Star |
|-----------|-----------|------|--------------|------------|
| Orientation vers service | Accompagnement | 1 | Date de création ; la `source` est l'origine de l'orientation (`dora`, ou `emplois` depuis juillet 2026) | Orientation `VALIDÉE` ou `REFUSÉE`, **sans condition de délai** |

Type et département : structure prescriptrice (Dora, ou organisation de La plateforme).

---

### Dora — iMER (intention de mise en relation)

**Source :** `autometa_tables_db`, `public.fct_dora__imer`
**Filtre :** `user_kind IN ('accompagnateur', 'accompagnateur_offreur', 'offreur', 'emplois_prescriber', 'emplois_employer')`

| Type acte | Catégorie | Rang | Donnée, date | North Star |
|-----------|-----------|------|--------------|------------|
| Intention d’orientation | Support | 1 | Date de l'iMER ; `source` `dora` ou `emplois` selon l'origine | Jamais |

⚠️ Ce calcul n'est pas l'iMER complet : il ne retient que les professionnels connectés des types filtrés. La définition de référence (cinq composantes, connectés et anonymes) est dans `knowledge/dora/README.md`, section « Key Metrics ». `fct_dora__imer` contient des orientations (`kind = 'service_orientation'`) et des mobilisations rattachées à une orientation (constaté sur septembre 2026) : sommer cet acte et « Dora — Orientations » fait un double compte. Pour une question iMER hors de ce TDB, suivre la route de `knowledge/dora/README.md`.

---

### Dora — Offre de service

**Instance :** dora · **DB :** 2 ; instance stats, DB 2, schéma `raw_dora` (recherches)

| Type acte | Catégorie | Rang | Donnée, date |
|-----------|-----------|------|--------------|
| Recherche d’offre de service, hors emploi solidaire | Support | 2 | `raw_dora.stats_searchview` : une ligne par recherche, anonymes compris, sans dédoublonnage |
| Création ou diffusion offre de service, hors emploi solidaire | Support | 3 | `services_service`, date de création |
| Mise à jour offre de service, hors emploi solidaire | Support | 3 | `services_service` modifiés par un utilisateur (`last_editor_id` renseigné), date de modification |
| Création structure, hors employeur solidaire | Support | 3 | `structures_structure`, date de création |
| Mise à jour d’une structure d’offre de service, hors employeur solidaire | Support | 3 | `structures_structure`, date de modification, si postérieure à la création |

---

### Le Marché

**Instance :** stats · **DB :** 6

| Type acte | Catégorie | Rang | Donnée, date | North Star |
|-----------|-----------|------|--------------|------------|
| Diffusion d’offre inclusive | Support | 1 | `tenders_tender`, `kind IN ('TENDER', 'PROJ', 'QUOTE')` et `status IN ('SUBMITTED', 'SENT')`, date de création | Besoin reçu par au moins une structure (`siae_count > 0`), sans condition de délai |
| Mise à jour fiche entreprise | Support | 3 | `siaes_siaeoffer` (prestations), date de modification | — |

Type de structure d'une diffusion : `SIAE` si l'auteur est un compte SIAE, sinon `Autre`. Département : lieu du besoin ; pour une mise à jour, celui de la structure.

⚠️ **Les besoins importés par l'API partenaire sont comptés** : ils restent `SUBMITTED` et ne sont jamais diffusés. De janvier à octobre 2026, ils font 5 048 des 5 533 diffusions comptées, aucune en North Star (319 diffusions North Star sur la période). Un volume « tous actes » du Marché est donc gonflé environ dix fois ; la North Star ne l'est pas.

---

### Mon Récap

**Instance :** stats · **DB :** 2 · **Table :** `monrecap."Commandes"`

| Type acte | Catégorie | Rang | Donnée |
|-----------|-----------|------|--------|
| Distribution carnet Mon Récap | Accompagnement | 2 | **Proxy** : 10 % des carnets expédiés sont distribués chaque mois pendant 10 mois, à partir du mois d'expédition |
| Remplissage carnet Mon Récap | Support | 2 | **Proxy** : pendant 6 mois à partir du mois d'expédition, 1,093 remplissage par mois et par carnet déjà distribué |

Date d'expédition : celle de la commande, ou à défaut la date de fabrication plus 7 jours (non saisie depuis les commandes d'avril 2026). Les volumes Mon Récap sont des estimations, pas des mesures.

---

### data·inclusion

**Instance :** datalake · **DB :** 2 · **Table :** `"stats_pdi-actes_metiers-data_inclusion"` (hebdomadaire, depuis avril 2025), hors contextes de test

| Type acte | Catégorie | Rang | Donnée | North Star |
|-----------|-----------|------|--------|------------|
| Recherche data·inclusion | Support | 2 | Recherches ; type de structure selon le contexte de l'acte | — |
| Mise à jour offre de service, hors emploi solidaire | Support | 3 | Type de structure selon le réseau porteur, `Autre` à défaut (~40 %) | — |
| Mise à jour d’une structure d’offre de service, hors employeur solidaire | Support | 3 | idem | — |
| Orientation vers service | Accompagnement | 1 | **Proxy** : 0,3 % des recherches du mois, réparties comme elles | **Proxy** : 55 % comptées traitées (taux Dora moyen sur 12 mois) |

---

## Pièges

- `north_star` vaut aussi `True` pour « Création offre d'emploi » et « Mise à jour offre d'emploi », qui sont de rang 3 : filtrer sur les actes de rang 1 avant de sommer la North Star, dans `data.json` comme dans le snapshot.
- « Orientation vers service » existe pour quatre sources (`dora`, `emplois`, `rdvi`, `data-inclusion`) : filtrer aussi sur `source`.
- Les actes par proxy (orientations RDV-i et data·inclusion, Mon Récap) sont des estimations : ne pas les présenter comme des mesures.

## Services non couverts

| Service | Raison |
|---------|--------|
| Pilotage | Pas d'acte métier direct identifié |
| Communauté | Non inclus |
| Site institutionnel (inclusion.gouv.fr) | Non inclus |
