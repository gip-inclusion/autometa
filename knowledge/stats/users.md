# Utilisateurs (les pros)

Les utilisateurs professionnels des services de la Plateforme de l'inclusion :
employeurs, prescripteurs, inspecteurs du travail.

**Les candidats (demandeurs d'emploi) ne sont pas dans cette table** — voir [candidats.md](candidats.md).

## Source principale

**Table :** `public.utilisateurs` (instance stats, database 2)
**Volumétrie :** ~91 000 utilisateurs
**Scope :** Utilisateurs pros des Emplois exclusivement (mais les plus nombreux de la plateforme).

### Colonnes clés

| Colonne | Description |
|---------|-------------|
| `id` | Identifiant unique |
| `email` | Email |
| `type` | `employer`, `prescriber`, `labor_inspector` |
| `prenom`, `nom` | Identité |
| `dernière_connexion` | Date de dernière connexion |
| `id_structure` | FK → `structures_v0` (employeurs) |
| `id_organisation` | FK → `organisations_v0` (prescripteurs) |
| `id_institution` | FK → `institutions` (prescripteurs institutionnels) |

### Requêtes courantes

```sql
-- Utilisateurs actifs (connectés dans les 30 derniers jours)
SELECT type, COUNT(*) as nb
FROM public.utilisateurs
WHERE dernière_connexion >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY type ORDER BY nb DESC;

-- Dernière connexion par type
SELECT type,
       COUNT(*) as total,
       COUNT(*) FILTER (WHERE dernière_connexion >= CURRENT_DATE - INTERVAL '30 days') as actifs_30j,
       COUNT(*) FILTER (WHERE dernière_connexion >= CURRENT_DATE - INTERVAL '90 days') as actifs_90j
FROM public.utilisateurs
GROUP BY type;
```

### Jointures par type d'utilisateur

| Type | Table à joindre | Clé |
|------|-----------------|-----|
| `employer` | `structures_v0` | `id_structure = structures."ID"` |
| `prescriber` | `organisations_v0` | `id_organisation = organisations.id` |
| `prescriber` (institutionnel) | `institutions` | `id_institution = institutions.id` |

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

Pour les questions impliquant **plusieurs services** (utilisateurs communs Emplois/Dora,
présence multi-services, etc.), utiliser la table `pdi_base_unique_tous_les_pros` dans
l'instance **datalake** (database 2). Voir [knowledge/datalake/README.md](../datalake/README.md#pdi_base_unique_tous_les_pros).

| Colonne datalake | Équivalent stats |
|------------------|------------------|
| `email` | `email` |
| `date_derniere_connexion` | `dernière_connexion` |
| `type_utilisateur` | `type` |
| `source` | (implicitement "Emplois" dans stats) |

Dashboard datalake utile : **Dashboard 24** — Utilisateurs Communs Emplois - Dora.
