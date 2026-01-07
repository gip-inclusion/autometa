---
date: 2026-01-07
website: emplois
original query: "Dans le rapport 2025-01-gps-reseau-intervenants-evolution.md, on observe, depuis le 15 décembre, un décalage entre les données matomo et celles de metabase. Peux-tu m'aider à identifier la cause possible ?"
query category: Analyse d'écart de métriques GPS
indicator type: [visiteurs_uniques, logs_datadog, segment_matomo, import_n8n]
---

# Analyse du décalage Matomo vs Metabase pour le GPS

**Site :** Les Emplois (emplois.inclusion.beta.gouv.fr)
**Période analysée :** Décembre 2025
**Date du rapport :** 7 janvier 2026

## Résumé exécutif

Un décalage significatif existe entre les comptages d'utilisateurs GPS dans Matomo et Metabase, qui **s'accentue après le 15 décembre 2025** :

- **Avant le 15 décembre** : Matomo compte **1.69x plus** d'utilisateurs uniques que Metabase (1 502 vs 891)
- **Après le 15 décembre** : Matomo compte **2.21x plus** d'utilisateurs uniques que Metabase (2 160 vs 976)
- **Augmentation du décalage** : +31% (de 1.69x à 2.21x)

**Cause principale identifiée** : Différence fondamentale de méthodologie de comptage entre Matomo (tracking de visites) et Metabase (logs d'actions serveur).

---

## 1. Données observées

### 1.1 Synthèse par période

| Période | Matomo visiteurs uniques | Metabase utilisateurs uniques | Ratio M/MB | Écart |
|---------|-------------------------:|------------------------------:|-----------:|------:|
| Avant 15 déc | 1 502 | 891 | **1.69x** | +69% |
| Après 15 déc | 2 160 | 976 | **2.21x** | +121% |

### 1.2 Évolution quotidienne

Quelques exemples représentatifs :

| Date | Matomo UV | Metabase UV | Ratio | MB actions |
|------|----------:|------------:|------:|-----------:|
| 2025-12-01 | 143 | 87 | 1.64x | 262 |
| 2025-12-09 | 139 | 48 | **2.90x** | 245 |
| 2025-12-12 | 283 | 236 | 1.20x | 1 303 |
| **2025-12-15** | **331** | **182** | **1.82x** | **778** |
| 2025-12-16 | 285 | 122 | 2.34x | 424 |
| 2025-12-18 | 202 | 60 | **3.37x** | 171 |
| 2025-12-19 | 165 | 33 | **5.00x** | 118 |
| 2025-12-22 | 231 | 60 | 3.85x | 227 |
| 2025-12-23 | 186 | 36 | **5.17x** | 74 |

**Data source :**
- Matomo : [VisitsSummary.get](https://matomo.inclusion.beta.gouv.fr/?module=API&method=VisitsSummary.get&idSite=117&period=day&date=2025-12-01,2025-12-31&segment=pageUrl%3D%40%2Fgps%2F) avec segment `pageUrl=@/gps/`
- Metabase : `SELECT COUNT(DISTINCT user_id) FROM gps_log_data WHERE timestamp BETWEEN ...`

---

## 2. Investigation des causes

### 2.1 Hypothèse 1 : Import n8n défaillant ❌

**Testé :** Vérification du délai entre `timestamp` (date de l'événement) et `created_at` (date d'import dans la base).

**Résultat :** Import fonctionnel, délais normaux (~8-14h en moyenne), aucun retard >2 jours.

**Conclusion :** L'import n8n depuis Datadog fonctionne correctement.

### 2.2 Hypothèse 2 : Changement de logging Django ❌

**Testé :** Comparaison des `view_name` loggées avant et après le 15 décembre.

**Résultat :**
- Aucune vue manquante après le 15 décembre
- 2 nouvelles vues (marginales) : `gps:ask_access` et `gps:join_group_from_name_and_email`
- Distribution des événements stable

**Conclusion :** Aucun changement significatif dans le logging Django.

### 2.3 Hypothèse 3 : Nouveau tracking Matomo ❌

**Testé :** Comparaison des pages trackées par Matomo avant et après le 15 décembre.

**Résultat :** Les pages GPS trackées sont les mêmes. La proportion de pages non-GPS dans le segment a même légèrement **diminué** (80.7% → 77.7%).

**Conclusion :** Pas de nouveau tracking Matomo introduit le 15 décembre.

### 2.4 Cause réelle : Différence méthodologique ✅

**MATOMO** compte les **visiteurs uniques** (par cookie/fingerprint) ayant eu **au moins une page GPS dans leur session**.

**METABASE** compte les **user_id distincts** ayant généré **au moins un log d'action GPS** dans Datadog.

#### Différences clés :

1. **Matomo = Visites** : Un utilisateur qui charge la page `/gps/groups/list` compte comme visiteur unique, même sans interaction
2. **Metabase = Actions loggées** : Un utilisateur compte uniquement s'il génère un événement serveur (ex: `GPS visit_list_groups`)
3. **Segment pageUrl=@/gps/** : Inclut TOUTES les visites contenant une page GPS, même si l'utilisateur consulte principalement d'autres pages

---

## 3. Analyse détaillée

### 3.1 Distribution des utilisateurs Metabase

| Nombre de logs | Avant 15 déc | Après 15 déc |
|----------------|-------------:|-------------:|
| 1 seul log | 427 (51%) | 440 (48%) |
| 2 logs | 137 (17%) | 125 (14%) |
| 3-5 logs | 123 (15%) | 195 (21%) |
| 6-10 logs | 72 (9%) | 93 (10%) |
| 11+ logs | 71 (9%) | 70 (8%) |
| **Total** | **830** | **923** |

**Observation :** Environ **la moitié** des utilisateurs GPS ne génèrent qu'**un seul log** dans Metabase, suggérant des visites très brèves ou des consultations passives.

### 3.2 Actions par utilisateur

| Période | Total logs | Nb users | Logs/user |
|---------|----------:|---------:|----------:|
| Avant 15 déc | 3 503 | 830 | 4.22 |
| Après 15 déc | 3 851 | 923 | 4.17 |

**Observation :** Le nombre moyen de logs par utilisateur reste **stable** (~4.2), ce qui suggère que le comportement des utilisateurs n'a pas fondamentalement changé.

### 3.3 Ratio Visites/Événements GPS dans Matomo

Comparaison du segment `pageUrl=@/gps/` avec les événements de catégorie "gps" :

| Semaine | Visites GPS | Événements GPS | Ratio V/E |
|---------|------------:|---------------:|----------:|
| 01-07 déc | 625 | 739 | 0.85 |
| 08-14 déc | 944 | 1 131 | 0.83 |
| **15-21 déc** | **1 323** | **1 217** | **1.09** |
| 22-28 déc | 548 | 498 | 1.10 |

**Observation :** Le ratio Visites/Événements **s'inverse** après le 15 décembre (passe de <1 à >1), confirmant que plus de visites sont comptées sans générer d'événements trackés.

### 3.4 Pages GPS trackées par Matomo

#### Top 5 pages AVANT le 15 décembre :

| Visites | Page |
|--------:|------|
| 1 527 | `/gps/groups/list` |
| 1 425 | `/dashboard/` |
| 770 | `/apply/prescriptions/list` |
| 654 | `/search/employers/results` |
| 452 | `/gps/groups/<int:group_id>/memberships` |

#### Top 5 pages APRÈS le 15 décembre :

| Visites | Page |
|--------:|------|
| **2 085** | `/dashboard/` |
| 1 741 | `/gps/groups/list` |
| 1 177 | `/gps/groups/<int:group_id>/memberships` |
| 1 077 | `/apply/prescriptions/list` |
| 894 | `/search/employers/results` |

**Observation majeure :** Le `/dashboard/` passe de la 2e place (1 425 visites) à la **1ère place** (2 085 visites, +46%), dépassant même la page principale du GPS.

---

## 4. Explication du décalage

### 4.1 Mécanisme du segment Matomo

Le segment `pageUrl=@/gps/` dans Matomo signifie : **"toutes les visites qui contiennent AU MOINS une page correspondant à `/gps/`"**.

Cela inclut :
- ✅ Les pages GPS elles-mêmes (`/gps/groups/list`, etc.)
- ✅ **TOUTES les autres pages** consultées durant la même visite (dashboard, candidatures, etc.)

### 4.2 Impact du changement du 25 novembre

Le **25 novembre 2025**, le lien vers la liste des bénéficiaires GPS a été **déplacé du dashboard vers la sidebar** (menu principal).

**Conséquence :**
- L'événement `tdb_liste_beneficiaires` (clic sur le lien) a **multiplié par 5x** (159/semaine → 861/semaine)
- Plus d'utilisateurs accèdent au GPS depuis le dashboard
- Le dashboard est maintenant **inclus dans plus de sessions GPS**

### 4.3 Pourquoi le ratio augmente après le 15 décembre

Plusieurs facteurs combinés :

1. **Visites exploratoires** : Plus d'utilisateurs découvrent le GPS via le nouveau lien sidebar
2. **Consultation passive** : Certains utilisateurs chargent la page GPS sans interagir (pas de log Datadog)
3. **Navigation multi-pages** : Les sessions GPS incluent maintenant plus de pages non-GPS (dashboard, liste candidatures)
4. **Sessions courtes** : ~50% des utilisateurs ne génèrent qu'un seul log (consultation rapide)

**Formule simplifiée :**

```
Ratio Matomo/Metabase =
  (Utilisateurs actifs + Utilisateurs passifs) / Utilisateurs actifs
```

- **Utilisateurs actifs** : Génèrent des logs Datadog (comptés par Metabase ET Matomo)
- **Utilisateurs passifs** : Chargent une page GPS sans interagir (comptés uniquement par Matomo)

Après le 15 décembre, le nombre d'**utilisateurs passifs** augmente plus vite que celui des utilisateurs actifs.

---

## 5. Vérifications complémentaires

### 5.1 Y a-t-il des user_id NULL dans Metabase ?

**Résultat :** Aucun log avec `user_id IS NULL` en décembre 2025.

**Interprétation :** Tous les logs Datadog concernent des utilisateurs authentifiés. Les visiteurs anonymes ne génèrent pas de logs GPS.

### 5.2 Les view_name correspondent-ils aux pages Matomo ?

| Page Matomo | View Datadog | Match |
|-------------|--------------|-------|
| `/gps/groups/list` | `gps:group_list` | ✅ |
| `/gps/groups/<id>/memberships` | `gps:group_memberships` | ✅ |
| `/gps/groups/<id>/contribution` | `gps:group_contribution` | ✅ |
| `/gps/groups/<id>/beneficiary` | `gps:group_beneficiary` | ✅ |
| `/gps/groups/<id>/edition` | `gps:group_edition` | ✅ |

**Conclusion :** Correspondance parfaite. Les vues Django loggent correctement.

### 5.3 Logs Metabase par type d'événement (après 15 déc)

| Événement | Nb logs | Nb users |
|-----------|--------:|---------:|
| `GPS visit_list_groups` | 1 129 | 565 |
| `GPS visit_group_memberships` | 916 | 391 |
| `GPS visit_group_contribution` | 456 | 235 |
| `GPS visit_group_edition` | 382 | 215 |
| `GPS visit_group_beneficiary` | 311 | 206 |
| `GPS display_contact_information` | 224 | 176 |

**Observation :** Les événements principaux (`visit_list_groups`, `visit_group_memberships`) dominent, cohérent avec l'usage attendu.

---

## 6. Conclusions et recommandations

### 6.1 Réponse à la question initiale

**Le décalage entre Matomo et Metabase est NORMAL et ATTENDU** car :

1. **Matomo mesure les visites** (toute session contenant une page GPS)
2. **Metabase mesure les actions loggées** (utilisateurs ayant généré un événement serveur)
3. Les deux métriques mesurent des choses **différentes mais complémentaires**

Le ratio de **1.69x avant** et **2.21x après** le 15 décembre s'explique par :
- Une **augmentation du trafic exploratoire** suite au déplacement du lien sidebar (25 nov)
- Plus d'utilisateurs **chargent des pages GPS sans interagir** (visites courtes)
- Le segment Matomo inclut de plus en plus de **pages non-GPS** dans les sessions GPS

### 6.2 Le décalage n'est PAS dû à :

❌ Un bug d'import n8n
❌ Un changement de logging Django
❌ Un nouveau tracking Matomo
❌ Des données manquantes dans Metabase

### 6.3 Recommandations

#### Pour une comparaison plus juste :

1. **Dans Matomo** : Utiliser le segment `actionType==pageview;pageUrl=@/gps/` pour ne compter que les **pages vues GPS réelles** (et pas toutes les visites contenant une page GPS)

2. **Dans Metabase** : Ajouter un comptage des **sessions GPS** (via `datadog_id`) en plus des `user_id`, pour se rapprocher de la notion de "visite" Matomo

3. **Métrique hybride** : Créer un tableau croisé comparant :
   - Matomo : Visites GPS pures (`pageUrl=@/gps/` ET première page = GPS)
   - Metabase : Sessions distinctes (`COUNT(DISTINCT datadog_id)`)

#### Pour le pilotage :

- **Utiliser Matomo** pour mesurer la **découvrabilité** et l'**attraction** du GPS (combien d'utilisateurs visitent au moins une fois)
- **Utiliser Metabase** pour mesurer l'**engagement réel** (combien d'utilisateurs interagissent avec le GPS)
- **Surveiller le ratio M/MB** comme indicateur de la qualité d'engagement :
  - Ratio élevé (>2x) = beaucoup de visites exploratoires sans engagement
  - Ratio faible (<1.5x) = forte conversion visite → action

---

## 7. Scripts de reproduction

Les scripts suivants ont été créés pour cette analyse :

- `scripts/gps_matomo_vs_metabase_hypothesis.py` : Comparaison visites/événements
- `scripts/gps_matomo_vs_metabase_comparison.py` : Comparaison détaillée quotidienne

### Exemple d'utilisation :

```bash
# Comparaison quotidienne
.venv/bin/python scripts/gps_matomo_vs_metabase_comparison.py

# Analyse du ratio visites/événements
.venv/bin/python scripts/gps_matomo_vs_metabase_hypothesis.py
```

---

## Annexe : Requêtes utilisées

### Metabase : Utilisateurs uniques par jour

```sql
SELECT
    DATE(timestamp) as date,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(*) as nb_actions
FROM gps_log_data
WHERE timestamp >= '2025-12-01'
  AND timestamp < '2026-01-01'
  AND user_id IS NOT NULL
GROUP BY DATE(timestamp)
ORDER BY date
```

### Matomo : Visiteurs uniques GPS

```bash
curl "https://matomo.inclusion.beta.gouv.fr/?module=API&method=VisitsSummary.get&idSite=117&period=day&date=2025-12-01,2025-12-31&segment=pageUrl%3D%40%2Fgps%2F&format=JSON&token_auth=..."
```

### Matomo : Pages GPS trackées

```bash
curl "https://matomo.inclusion.beta.gouv.fr/?module=API&method=Actions.getPageUrls&idSite=117&period=range&date=2025-12-15,2025-12-31&segment=pageUrl%3D%40%2Fgps%2F&flat=1&format=JSON&token_auth=..."
```
