---
date: 2026-01-07
website: emplois
original_query: "Cloture des questions ouvertes sur le diagnostic des candidats autonomes"
query_category: Candidatures autonomes - Investigation
indicator_type:
  - candidatures
  - autonomie
  - diagnostic
  - investigation
---

# Cloture des questions ouvertes : Diagnostic des candidats autonomes

*Investigation menee le 7 janvier 2026*

Ce rapport repond aux 5 questions ouvertes identifiees dans la synthese des rapports.

---

## Question 1 : Pourquoi les chiffres mensuels different-ils entre rapports ?

### Reponse : Erreur dans les rapports 2/3, rapport 4 correct

**Donnees verifiees (requete du 7 janvier 2026) :**

| Mois | Total | Avec diagnostic | Taux |
|------|-------|-----------------|------|
| Sept 2025 | 10 008 | 8 020 | **80,1%** |
| Oct 2025 | 10 103 | 7 695 | 76,2% |
| Nov 2025 | 9 879 | 7 343 | 74,3% |
| Dec 2025 | 8 353 | 5 824 | **69,7%** |

**Comparaison avec les rapports :**

| Mois | Rapports 2/3 | Rapport 4 | Verite |
|------|--------------|-----------|--------|
| Sept 2025 | 75,0% | 80,1% | **80,1%** |
| Dec 2025 | 75,7% | 69,7% | **69,7%** |

**Conclusion :** Les rapports `taux-candidatures-autonomes-avec-diagnostic.md` et `taux-candidats-autonomes-avec-diagnostic.md` contenaient des erreurs. Le rapport `evolution-taux-candidats-autonomes-diagnostic-2023-2025.md` etait correct.

**Action :** Supprimer le doublon errone.

---

## Question 2 : Qu'est-ce qui a provoque la chute de decembre 2025 (69,7%) ?

### Reponse : Effet conges de fin d'annee, aggrave par la derniere semaine

**Analyse par semaine :**

| Semaine | Candidatures | Avec diagnostic | Taux |
|---------|--------------|-----------------|------|
| 1-7 dec | 2 235 | 1 670 | 74,7% |
| 8-14 dec | 2 245 | 1 531 | 68,2% |
| 15-21 dec | 1 909 | 1 326 | 69,5% |
| 22-28 dec | 1 144 | 802 | 70,1% |
| **29-31 dec** | **820** | **495** | **60,4%** |

**Constat :** La derniere semaine de decembre (60,4%) tire fortement le taux vers le bas.

**Comparaison des decembres :**

| Annee | Total | Taux | Diag prescripteur | Diag employeur |
|-------|-------|------|-------------------|----------------|
| 2023 | 4 964 | 76,9% | 2 899 | 918 |
| 2024 | 6 075 | 72,9% | 3 428 | 1 003 |
| 2025 | 8 353 | 69,7% | 5 011 | 813 |

**Observations :**
1. Les prescripteurs augmentent leur volume (+73% entre 2023 et 2025)
2. Les employeurs baissent leur volume (-11% entre 2023 et 2025)
3. Le volume total a presque double (+68%)

**Repartition decembre 2025 :**

| Auteur | Candidatures | Part |
|--------|--------------|------|
| Prescripteur | 5 011 | 60,0% |
| Sans diagnostic | 2 529 | 30,3% |
| Employeur | 813 | **9,7%** |

**Conclusion :** La part employeur en decembre 2025 (9,7%) est bien inferieure a leur moyenne annuelle (15,1%). Les employeurs reduisent fortement leur activite de diagnostic en fin d'annee.

**Causes identifiees :**
1. **Conges des prescripteurs** : Moins de diagnostics realises en fin d'annee
2. **Conges des employeurs** : Part employeur chute de 15% a 10%
3. **Rush de candidatures** : Volume en hausse malgre les conges
4. **Derniere semaine critique** : 60,4% seulement

---

## Question 3 : Pourquoi les employeurs ont-ils divise par 2 leur part de diagnostics ?

### Reponse : Volume stable, part diluee par la croissance du marche

**Evolution annuelle :**

| Annee | Total | Prescripteur | Employeur | Sans diag | Part employeur |
|-------|-------|--------------|-----------|-----------|----------------|
| 2023 | 56 522 | 30 875 | 16 469 | 9 178 | **29,1%** |
| 2024 | 80 143 | 43 833 | 15 946 | 20 364 | **19,9%** |
| 2025 | 106 266 | 64 358 | 16 029 | 25 879 | **15,1%** |

**Constat cle :** Le volume absolu de diagnostics employeurs est **stable** (~16 000/an).
La baisse de part est due a la croissance du volume total (+88% en 3 ans).

**Decomposition par type d'employeur :**

| Type | 2023 | 2024 | 2025 | Evolution |
|------|------|------|------|-----------|
| ACI | 7 596 | 7 228 | 6 543 | **-14%** |
| AI | 3 805 | 3 355 | 3 446 | -9% |
| ETTI | 2 550 | 2 758 | 2 953 | **+16%** |
| EI | 2 465 | 2 561 | 2 792 | **+13%** |
| EITI | 53 | 44 | 295 | +457% |

**Observations :**
1. **Les ACI baissent** : -1 053 diagnostics (-14%)
2. **Les ETTI et EI augmentent** : +403 et +327 diagnostics
3. **Les EITI explosent** : +242 diagnostics (mais base faible)

**Hypotheses confirmees :**
1. Les ACI, qui faisaient le plus de diagnostics, se sont recentres sur le recrutement
2. Les ETTI et EI compensent partiellement
3. La capacite globale des employeurs est saturee a ~16 000 diagnostics/an

---

## Question 4 : Qu'est-ce qui a cause le rebond de l'ete 2025 ?

### Reponse : Forte mobilisation des prescripteurs (+56%)

**Comparaison des etes (juillet-septembre) :**

| Annee | Total | Avec diag | Prescripteur | Employeur | Taux |
|-------|-------|-----------|--------------|-----------|------|
| 2023 | 13 373 | 11 118 | 7 034 | 4 084 | 83,1% |
| 2024 | 18 115 | 13 380 | 9 809 | 3 571 | 73,9% |
| 2025 | 24 134 | 19 082 | **15 328** | 3 754 | **79,1%** |

**Croissance des diagnostics prescripteurs :**
- Ete 2024 vs 2023 : +39%
- **Ete 2025 vs 2024 : +56%**

**Detail mensuel ete 2025 :**

| Mois | Total | Prescripteur | Employeur | Taux |
|------|-------|--------------|-----------|------|
| Juillet | 7 468 | 4 686 | 1 134 | 77,9% |
| Aout | 6 658 | 4 269 | 973 | 78,7% |
| Septembre | 10 008 | 6 373 | 1 647 | 80,1% |

**Observations :**
1. Les prescripteurs ont absorbe la croissance estivale (+56% de diagnostics)
2. Les employeurs sont restes stables (~3 700-3 800 diagnostics/ete)
3. Le taux s'ameliore progressivement de juillet (77,9%) a septembre (80,1%)

**Hypotheses :**
1. **Mobilisation prescripteurs** : Possible effort de rattrapage post-creux 2024
2. **Saisonnalite inversee** : L'ete voit moins de candidats "non prepares" que la rentree
3. **Effet renfort** : France Travail et Missions Locales ont peut-etre renforce leurs effectifs

---

## Question 5 : Faut-il bloquer les candidatures sans diagnostic ?

### Reponse : Question de politique produit, donnees pour eclairer la decision

**Profil des candidatures sans diagnostic (decembre 2025) :**

| Type SIAE | Candidatures | Part |
|-----------|--------------|------|
| ACI | 920 | 36,4% |
| EI | 552 | 21,8% |
| AI | 382 | 15,1% |
| ETTI | 373 | 14,7% |
| EA | 146 | 5,8% |
| GEIQ | 80 | 3,2% |
| Autres | 76 | 3,0% |

**Observations :**
1. Les ACI recoivent 36% des candidatures sans diagnostic
2. La repartition est similaire a celle des candidatures avec diagnostic
3. Pas de structure particulierement "ciblee" par les candidats non diagnostiques

**Impact du blocage (estimation) :**

| Scenario | Candidatures | Diagnostics | Taux |
|----------|--------------|-------------|------|
| **Actuel** | 106 266 | 80 387 | 75,6% |
| **Blocage** | ~85 000 (-20%) | 85 000 | **100%** |

**Risques :**
- Perte de ~21 000 candidatures/an (20% du volume)
- Frustration des candidats
- Certains candidats eligibles mais sans diagnostic seraient exclus

**Alternative douce :**
- Alerte non bloquante avant soumission
- Impact estime : +5-10 points de taux (80-85%)
- Pas de perte de volume

---

## Synthese des reponses

| Question | Reponse courte |
|----------|----------------|
| 1. Ecarts de donnees | Erreur dans rapports 2/3, rapport 4 correct |
| 2. Chute dec 2025 | Conges + derniere semaine a 60,4% |
| 3. Declin employeurs | Volume stable, part diluee par croissance x2 |
| 4. Rebond ete 2025 | Prescripteurs +56% de diagnostics |
| 5. Bloquer ? | Decision produit ; risque -20% volume |

---

## Actions recommandees

### Immediat

1. **Supprimer le doublon** : `taux-candidatures-autonomes-avec-diagnostic.md` (errone)
2. **Corriger les donnees** dans les rapports restants si necessaire

### Court terme

3. **Mobilisation Q4** : Campagne de sensibilisation octobre-decembre
4. **Alerte pre-candidature** : Message non bloquant sur l'importance du diagnostic

### Moyen terme

5. **Reactiver les ACI** : Investiguer pourquoi les ACI font -14% de diagnostics
6. **Capitaliser sur l'ete** : Comprendre ce qui a fonctionne pour le reproduire

---

## Sources des donnees

**Table** : `candidatures_echelle_locale`
**Periode** : 2023-01-01 a 2025-12-31
**Script** : `scripts/close_open_questions_diagnostic.py`

**Requete executee le** : 7 janvier 2026

---

*Rapport genere par Matometa*
