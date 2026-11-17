---
source: [metabase:stats, metabase:datalake]
verifie_le: 2026-07-15
---
# Utilisateurs (les pros)

Les utilisateurs professionnels des services de la PDI :
employeurs, prescripteurs, inspecteurs du travail.

**Les candidats (demandeurs d'emploi) ne sont pas dans cette table** — voir [candidats.md](candidats.md).

## Source principale

**Table :** `public.utilisateurs` (instance stats, database 2 ; aussi dans `autometa_tables_db`)
**Volumétrie :** ~92 000 comptes pour ~106 000 lignes : **une ligne par rattachement** (structure, organisation ou institution), jusqu'à plusieurs centaines pour un même compte. Compter `COUNT(DISTINCT id)` et dédupliquer par `id` avant toute jointure, sinon les lignes jointes (candidatures, orientations…) sont multipliées. Contrôler le total brut contre le total après jointure.
**Scope :** Utilisateurs pros de La plateforme (ex-Emplois) exclusivement (mais les plus nombreux de la PDI).

### Colonnes clés

| Colonne | Description |
|---------|-------------|
| `id` | Identifiant du compte, répété sur chacune de ses lignes de rattachement. Égal à `@usr.id` dans les logs Datadog |
| `email` | Email |
| `type` | Vaut `professional` pour tous les comptes : ne distingue plus employeurs et prescripteurs. Le profil se lit au rattachement (voir ci-dessous) |
| `prenom`, `nom` | Identité |
| `dernière_connexion` | Date de dernière connexion |
| `id_structure` | FK → `structures_v0` (employeurs) |
| `id_organisation` | FK → `organisations_v0` (prescripteurs) |
| `id_institution` | FK → `institutions` (prescripteurs institutionnels) |

### Requêtes courantes

```sql
-- Utilisateurs actifs (connectés dans les 30 derniers jours), par rattachement
SELECT CASE WHEN id_structure IS NOT NULL THEN 'employeur'
            WHEN id_organisation IS NOT NULL THEN 'prescripteur ou orienteur'
            WHEN id_institution IS NOT NULL THEN 'institution'
            ELSE 'sans rattachement' END AS profil,
       COUNT(DISTINCT id) AS nb
FROM public.utilisateurs
WHERE dernière_connexion >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY 1 ORDER BY nb DESC;
```

> **Attention — « actif » ≠ « connecté ».** Ci-dessus, `actifs` = ≥1 connexion sur la période. Le [glossaire AARRI](../bizdev/glossaire.md) **déclasse ce proxy** : un utilisateur actif a réalisé **≥1 acte métier** sur le mois. Pour toute analyse de rétention/adoption, compter les actes métiers, pas les connexions.

### Jointures par rattachement

Chaque ligne porte au plus un rattachement. Prescripteur habilité ou orienteur : selon `organisations.habilitée`.

| Profil | Table à joindre | Clé |
|------|-----------------|-----|
| Employeur | `structures_v0` | `id_structure = structures."ID"` |
| Prescripteur ou orienteur | `organisations_v0` | `id_organisation = organisations.id` |
| Institution (inspection, DDETS, DGEFP…) | `institutions` | `id_institution = institutions.id` |

## Analyses géographiques

**Table :** `public.tmp_utilisateurs_avec_departement`

Table enrichie (un utilisateur peut apparaître plusieurs fois s'il a plusieurs structures).

```sql
-- Utilisateurs par département
SELECT departement, COUNT(DISTINCT email) as nb
FROM public.tmp_utilisateurs_avec_departement
GROUP BY departement ORDER BY nb DESC;
```

## Données cross-produits (datalake)

Pour les questions impliquant **plusieurs services** (utilisateurs communs La plateforme/Dora,
présence multi-services, etc.), utiliser la table `pdi_base_unique_tous_les_pros` dans
l'instance **datalake** (database 2). Voir [knowledge/datalake/README.md](../datalake/README.md#pdi_base_unique_tous_les_pros).

| Colonne datalake | Équivalent stats |
|------------------|------------------|
| `email` | `email` |
| `date_derniere_connexion` | `dernière_connexion` |
| `type_utilisateur` | `type` |
| `source` | (implicitement "Emplois" dans stats) |

Dashboard datalake utile : **Dashboard 24** — Utilisateurs Communs Emplois - Dora.
