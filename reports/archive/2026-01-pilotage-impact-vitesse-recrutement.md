---
date: 2026-01-07
website: [pilotage, emplois]
original query: "Les professionnels qui utilisent le pilotage de l'inclusion recrutent-ils plus rapidement que les professionnels qui ne l'utilisent pas ?"
query category: "Impact et efficacité des outils"
indicator type: [usage-pilotage, délais-recrutement, méthodologie]
---

# Impact de l'utilisation de Pilotage sur la vitesse de recrutement

**Demande initiale :** Les professionnels qui utilisent Pilotage de l'inclusion recrutent-ils plus rapidement que les professionnels qui ne l'utilisent pas ?

**Verdict :** Cette analyse n'est **pas réalisable avec les données actuellement disponibles**.

---

## 1. Pourquoi cette analyse est impossible aujourd'hui

### 1.1 Absence de liaison entre les systèmes

Les deux sources de données nécessaires ne sont pas reliées :

| Système | Données disponibles | Limitations |
|---------|---------------------|-------------|
| **Matomo** (Pilotage, site ID 146) | Visites sur le site Pilotage : volumes, pages consultées, durée de session | • Utilisateurs anonymisés<br>• Pas de custom dimensions (contrairement à Emplois qui track UserKind, UserDepartment, etc.)<br>• Impossible d'identifier individuellement les professionnels |
| **Metabase** | Données de candidatures et recrutements : taux d'acceptation, délais, profils des candidats | • Ne contient aucune information sur l'utilisation de Pilotage<br>• Pas de variable "utilise_pilotage" |

**Il n'existe aucun identifiant commun** (SIRET, ID utilisateur, ID structure) permettant de croiser ces données.

### 1.2 Pilotage : un outil de consultation sans authentification

Pilotage est actuellement configuré comme un **site de consultation publique** :

```yaml
Tracking actuel:
  - Custom dimensions: Aucune (vs Emplois qui track UserKind, UserDepartment)
  - Événements trackés: ~10/an (uniquement bouton Infolettre)
  - Authentification: Non trackée
  - Méthode: Matomo Tag Manager (pas de code inline)
```

**Conséquence :** Même si nous savons combien de visites reçoit Pilotage (ex: 191 visiteurs uniques/jour en juin 2025), nous ne savons pas :
- **Qui** consulte (quel prescripteur, quel SIAE, quel DDETS)
- **Quelle organisation** ils représentent
- **Avec quelle régularité** ils reviennent

### 1.3 Absence de métriques temporelles dans Metabase

Après analyse de l'inventaire Metabase (334 cards, 16 dashboards), les données disponibles se concentrent sur :

✅ **Disponible :**
- Taux d'acceptation des candidatures (par prescripteur, par SIAE, par type)
- Volume de candidatures (origine, état, type d'orienteur)
- Profils des candidats embauchés
- Postes en tension (difficultés de recrutement)

❌ **Manquant :**
- Délai entre candidature et décision d'embauche
- Délai entre réception et première action sur une candidature
- Temps moyen de traitement d'un dossier
- **Aucune variable sur l'utilisation d'outils de pilotage**

**Note importante :** Le dashboard 116 "Candidatures - Traitement et résultats des candidatures émises" contient un avertissement explicite :

> ☝️ Attention : les données dans ce tableau de bord proviennent du service des emplois de l'inclusion. Dans le parcours des prescripteurs et des SIAE, **il ne leur est pas demandé de renseigner de manière exhaustive les critères des publics accompagnés**. [...] **Les données que nous présentons ci-dessous servent à avoir une tendance, mais pas une vision exacte de la réalité**.

---

## 2. Ce qu'il faudrait pour répondre à cette question

### 2.1 Tracking authentifié sur Pilotage

**Ajout de custom dimensions dans Matomo :**

```javascript
// À implémenter sur Pilotage
_paq.push(['setCustomDimension', customDimensionId=1, 'SIRET_structure']);
_paq.push(['setCustomDimension', customDimensionId=2, 'role']);  // prescripteur, employeur, DDETS
_paq.push(['setCustomDimension', customDimensionId=3, 'departement']);
_paq.push(['setCustomDimension', customDimensionId=4, 'type_structure']);  // FT, ML, SIAE, etc.
```

**Événements à tracker :**
- Consultation des tableaux de bord privés (déjà configuré mais pas actif)
- Téléchargement de données
- Exploration des indicateurs par thématique
- Durée de consultation par dashboard

### 2.2 Enrichissement des données Metabase

**Nouvelles colonnes dans les tables de candidatures :**

```sql
-- Table candidatures_echelle_locale
ALTER TABLE candidatures_echelle_locale ADD COLUMN structure_utilise_pilotage BOOLEAN;
ALTER TABLE candidatures_echelle_locale ADD COLUMN derniere_connexion_pilotage DATE;
ALTER TABLE candidatures_echelle_locale ADD COLUMN frequence_consultation_pilotage TEXT;  -- jamais, rare, régulier, intensif

-- Nouvelles métriques temporelles
ALTER TABLE candidatures_echelle_locale ADD COLUMN delai_reception_premiere_action_jours INT;
ALTER TABLE candidatures_echelle_locale ADD COLUMN delai_candidature_decision_jours INT;
ALTER TABLE candidatures_echelle_locale ADD COLUMN delai_acceptation_embauche_jours INT;
```

**Source des données :**
1. **Connexion Pilotage → Matomo** : Export mensuel des structures actives sur Pilotage (via API Matomo)
2. **Injection dans Metabase** : Jointure SIRET entre export Matomo et tables candidatures
3. **Métriques temporelles** : Calcul à partir des timestamps existants dans la base Emplois

### 2.3 Méthodologie d'analyse

Une fois les données disponibles, l'analyse devrait suivre cette structure :

```python
# Pseudo-code de l'analyse cible
structures = get_all_structures()

# Segmentation
utilisateurs_pilotage = structures.filter(dernier_acces_pilotage < 30_jours)
non_utilisateurs_pilotage = structures.filter(dernier_acces_pilotage IS NULL OR > 90_jours)

# Métriques à comparer
metrics = [
    'delai_moyen_traitement_candidature',
    'taux_acceptation',
    'delai_moyen_embauche_apres_acceptation',
    'nombre_candidatures_traitees_par_mois',
]

# Contrôle des variables confondantes
control_variables = [
    'type_structure',  # SIAE vs prescripteur
    'departement',     # Tension du marché local
    'taille_structure', # Capacité de traitement
    'anciennete_plateforme',  # Expérience
]

# Test statistique
result = run_regression(
    dependent_var='delai_moyen_traitement',
    independent_vars=['utilise_pilotage'] + control_variables,
    data=structures
)
```

**Hypothèses à tester :**
- H1 : Les utilisateurs réguliers de Pilotage ont un délai de traitement **inférieur** de X jours
- H2 : L'effet est plus marqué chez les **nouveaux prescripteurs** (courbe d'apprentissage)
- H3 : L'effet varie selon le **type d'indicateur consulté** (candidatures vs offres vs publics)

---

## 3. Analyses alternatives possibles aujourd'hui

En attendant la mise en place du tracking, voici ce que je peux produire :

### 3.1 Corrélation géographique (proxy imparfait)

**Hypothèse :** Si Pilotage est utile, les départements où il est le plus consulté devraient avoir de meilleurs indicateurs.

**Données disponibles :**
- **Matomo (Pilotage)** : Répartition géographique des visiteurs (UserCountry.getRegion)
- **Metabase** : Indicateurs de performance par département (taux acceptation, volumes)

**Méthode :**
```python
# 1. Extraire les visites Pilotage par département (Matomo)
visits_by_dept = get_pilotage_visits_by_department(period='year', date='2025')

# 2. Extraire les performances recrutement par département (Metabase)
performance_by_dept = get_recruitment_metrics_by_department(year=2025)

# 3. Calculer la corrélation
correlation = pearsonr(
    visits_by_dept['visits_per_capita'],  # Normalisé par population
    performance_by_dept['taux_acceptation']
)
```

**Limites :**
- Corrélation ≠ causalité (peut-être que les départements performants consultent plus Pilotage parce qu'ils sont déjà efficaces)
- Impossible d'isoler l'effet Pilotage des autres facteurs (tension du marché, dotation en prescripteurs, etc.)

### 3.2 Profil des utilisateurs de Pilotage

**Objectif :** Comprendre qui utilise Pilotage et comment.

**Analyses possibles :**
- Volume de trafic mensuel et saisonnalité
- Pages les plus consultées (tableaux de bord publics vs privés)
- Parcours de navigation typiques
- Taux d'engagement (durée, profondeur de visite)

**Utilité :** Identifier les usages et optimiser l'outil.

### 3.3 Benchmark des performances de recrutement

**Objectif :** Établir des références pour mesurer l'impact futur de Pilotage.

**Analyses possibles via Metabase :**
- Taux d'acceptation moyen par type de prescripteur
- Taux d'acceptation par type de SIAE
- Évolution annuelle des candidatures et embauches
- Postes en tension (délais de recrutement longs)

**Utilité :** Baseline pour une étude avant/après une fois le tracking en place.

---

## 4. Recommandations

### Court terme (1-2 mois)

1. **Implémenter l'authentification sur Pilotage** avec tracking Matomo :
   ```javascript
   // Dans le code Pilotage (Django)
   _paq.push(['setCustomDimension', 1, '{{ user.organization.siret }}']);
   _paq.push(['setCustomDimension', 2, '{{ user.role }}']);
   ```

2. **Activer les événements déjà configurés** dans Matomo Tag Manager :
   - "Clic Tableaux de bord privés" (déjà défini, jamais déclenché)
   - Ajouter : "Consultation dashboard [nom]"
   - Ajouter : "Export données"

3. **Documenter les timestamps** dans la base Emplois :
   - Vérifier si les champs `created_at`, `updated_at` permettent de calculer les délais
   - Si oui, créer des vues calculées dans Metabase

### Moyen terme (3-6 mois)

4. **Créer un tableau de bord "Impact Pilotage"** dans Metabase :
   ```sql
   -- Vue matérialisée
   CREATE MATERIALIZED VIEW impact_pilotage AS
   SELECT
     s.siret,
     s.type_structure,
     s.departement,
     COUNT(DISTINCT mp.date_visite) AS jours_connexion_pilotage,
     AVG(c.delai_traitement) AS delai_moyen_traitement,
     COUNT(c.id) / COUNT(DISTINCT c.mois) AS candidatures_par_mois
   FROM structures s
   LEFT JOIN matomo_pilotage mp ON s.siret = mp.siret
   LEFT JOIN candidatures c ON s.siret = c.structure_siret
   GROUP BY s.siret, s.type_structure, s.departement;
   ```

5. **Mener une enquête qualitative** :
   - Questionnaire auprès d'un échantillon de prescripteurs/SIAE
   - Question clé : "Utilisez-vous Pilotage ? Si oui, cela a-t-il changé vos pratiques ?"

### Long terme (6-12 mois)

6. **Étude d'impact rigoureuse** :
   - Design quasi-expérimental : comparer utilisateurs avant/après première utilisation de Pilotage
   - Contrôler les variables confondantes (taille, ancienneté, département)
   - Mesurer plusieurs outcomes : délais, taux acceptation, satisfaction candidats

7. **Dashboard temps réel** :
   - Indicateur "Utilisation Pilotage" visible dans Emplois (côté prescripteur/SIAE)
   - Nudge : "Les structures qui consultent Pilotage traitent X% plus vite les candidatures"

---

## 5. Conclusion

**État actuel :** La question posée est légitime et stratégique, mais **les données pour y répondre n'existent pas encore**.

**Raison principale :** Les silos entre systèmes (Matomo anonyme + Metabase sans variable usage-outil).

**Action immédiate recommandée :** Implémenter le tracking SIRET sur Pilotage (effort technique faible, impact analytique élevé).

**Délai pour première analyse :** 3-6 mois après implémentation du tracking (besoin d'historique).

**En attendant :** Je peux produire les analyses alternatives listées en section 3, qui fourniront du contexte utile mais ne répondront pas directement à la question causale.

---

**Souhaitez-vous que je réalise l'une des analyses alternatives (3.1, 3.2 ou 3.3) ?**
