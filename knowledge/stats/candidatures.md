# Candidatures — Emplois de l'Inclusion

Table de référence pour toutes les analyses sur les candidatures du service Emplois.

**Base Metabase :** Stats · `database_id = 2`
**Table :** `public.candidatures_echelle_locale`
**Volumétrie :** ~2,6 millions de lignes
**Mise à jour :** quotidienne

## Champ clé : `état`

Le champ `état` indique l'avancement du traitement par l'employeur.

⚠️ **Seuls certains états envoient un retour au candidat :**

| État | Retour au candidat |
|------|--------------------|
| `Nouvelle candidature` | ❌ Non |
| `Candidature en attente` | ❌ Non |
| `Candidature à l'étude` | ❌ Non |
| `Candidature acceptée` | ✅ Oui |
| `Candidature refusée` | ✅ Oui |
| `Embauché ailleurs` | ✅ Oui |
| `Embauche annulée` | ✅ Oui |
| `Vivier de candidatures` | ✅ Oui |
| `Action préalable à l'embauche` | ✅ Oui |

Pour les taux de réponse, voir [knowledge/README.md](../README.md) : utiliser une fenêtre
fixe (ex : réponse dans les 30 jours) et exclure les candidatures trop récentes.

## Colonnes principales

### Identifiants et dates

| Colonne | Description |
|---------|-------------|
| `id` | Identifiant unique (uuid) |
| `date_candidature` | Date de dépôt de la candidature |
| `date_traitement` | Date de traitement par l'employeur |
| `date_embauche` | Date d'embauche (si acceptée) |
| `date_début_contrat` | Date de début de contrat |

### Délais

| Colonne | Description |
|---------|-------------|
| `délai_prise_en_compte` | Délai entre dépôt et première prise en compte |
| `délai_de_réponse` | Délai entre dépôt et réponse finale |
| `temps_de_reponse` | Délai de réponse en jours (numérique) |
| `temps_de_prise_en_compte` | Délai de prise en compte en jours (numérique) |
| `temps_de_reponse_intervalle` | Tranche de délai (ex : "< 7 jours") |

### Structure employeuse

| Colonne | Description |
|---------|-------------|
| `id_structure` | FK vers `public.structures_v0` |
| `nom_structure` | Nom de la structure |
| `type_structure` | Type de SIAE (ACI, EI, AI, ETTI, GEIQ...) |
| `département_structure` | Département de la structure |
| `zone_emploi` | Zone d'emploi |
| `epci` | EPCI |
| `bassin_emploi_structure` | Bassin d'emploi |

### Prescripteur

| Colonne | Description |
|---------|-------------|
| `id_org_prescripteur` | FK vers `public.organisations_v0` |
| `nom_org_prescripteur` | Nom de l'organisation prescriptrice |
| `type_org_prescripteur` | Type d'organisation prescriptrice |

### Candidat

| Colonne | Description |
|---------|-------------|
| `id_candidat` | FK vers `public.candidats` |
| `hash_nir` | NIR anonymisé |
| `tranche_age` | Tranche d'âge |
| `genre_candidat` | Genre |
| `auteur_diag_candidat` | Auteur du diagnostic |

### Contexte

| Colonne | Description |
|---------|-------------|
| `origine` | Origine de la candidature |
| `origine_détaillée` | Origine détaillée |
| `motif_de_refus` | Motif si refus |
| `mode_attribution_pass_iae` | Mode d'attribution du PASS IAE |

## Jointures

Cette table est dénormalisée : la plupart des analyses n'ont pas besoin de jointures supplémentaires.

```sql
-- Taux de réponse à 30 jours par mois (comparable dans le temps)
SELECT
    DATE_TRUNC('month', date_candidature) AS mois,
    COUNT(*) AS nb_candidatures,
    COUNT(*) FILTER (
        WHERE état NOT IN ('Nouvelle candidature', 'Candidature en attente', 'Candidature à l''étude')
        AND temps_de_reponse <= 30
    ) AS nb_reponses_30j,
    ROUND(
        COUNT(*) FILTER (
            WHERE état NOT IN ('Nouvelle candidature', 'Candidature en attente', 'Candidature à l''étude')
            AND temps_de_reponse <= 30
        ) * 100.0 / COUNT(*), 1
    ) AS taux_reponse_30j
FROM public.candidatures_echelle_locale
WHERE date_candidature < CURRENT_DATE - INTERVAL '30 days'  -- exclure les récentes
GROUP BY 1
ORDER BY 1 DESC;

-- Candidatures par type de structure, dernier mois complet
SELECT
    type_structure,
    COUNT(*) AS nb_candidatures,
    COUNT(*) FILTER (WHERE état = 'Candidature acceptée') AS nb_acceptees,
    ROUND(
        COUNT(*) FILTER (WHERE état = 'Candidature acceptée') * 100.0 / COUNT(*), 1
    ) AS taux_acceptation
FROM public.candidatures_echelle_locale
WHERE DATE_TRUNC('month', date_candidature) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
GROUP BY type_structure
ORDER BY nb_candidatures DESC;
```

## Attention : date de référence

Selon l'analyse, choisir la bonne date de référence :

| Objectif | Date à utiliser |
|----------|-----------------|
| Activité des candidats | `date_candidature` |
| Résultats effectifs | `date_embauche` ou `date_traitement` |
| Délais de traitement | `date_candidature` + `temps_de_reponse` |

L'écart entre `date_candidature` et `date_embauche` peut dépasser 30 jours.
Voir [knowledge/README.md](../README.md).
