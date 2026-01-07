---
date: 2026-01-07
website: emplois
original_query: "Consolidation des analyses sur candidatures autonomes et diagnostic"
query_category: Candidatures autonomes - Synthese
indicator_type:
  - candidatures
  - autonomie
  - diagnostic
  - synthese
---

# Synthese : Candidatures autonomes et diagnostic d'eligibilite

*Consolidation de 5 rapports produits en janvier 2026*

---

## Sources consolidees

| Rapport | Date | Focus |
|---------|------|-------|
| candidats-autonomes | 05/01 | Vue generale : volume, demographie, geographie |
| taux-candidatures-autonomes-avec-diagnostic | 07/01 | Taux de diagnostic 2025, recommandations |
| taux-candidats-autonomes-avec-diagnostic | 07/01 | Quasi-identique au precedent (doublon) |
| evolution-taux-candidats-autonomes-diagnostic-2023-2025 | 07/01 | Evolution 36 mois, tendances |
| synthese-analyses-complementaires-diagnostic | 07/01 | Saisonnalite, correlation volume/taux |

---

## Constats consolides

### 1. Volume en forte croissance

| Annee | Candidatures autonomes | Croissance |
|-------|------------------------|------------|
| 2023 | 56 522 | - |
| 2024 | 80 143 | +42% |
| 2025 | 106 266 | +33% |

**Croissance totale 2023-2025 : +88%** (quasi-doublement)

### 2. Taux de diagnostic : baisse puis stabilisation

| Annee | Taux moyen | Evolution |
|-------|------------|-----------|
| 2023 | 83,8% | Reference |
| 2024 | 74,6% | -9,2 points |
| 2025 | 75,6% | +1,0 point |

**Baisse nette de 8,2 points en 3 ans.**

### 3. Impact critique du diagnostic

| Statut | Taux d'acceptation |
|--------|-------------------|
| Avec diagnostic | 5,9% |
| Sans diagnostic | 0,1% |

**Multiplicateur : x45.** Sans diagnostic, la candidature est quasi-systematiquement refusee.

### 4. France Travail, acteur dominant

France Travail realise **40%** des diagnostics pour les candidats autonomes.
Les prescripteurs dans leur ensemble : **60,6%** (doublement du volume en 3 ans).

### 5. Employeurs en retrait

| Annee | Part des diagnostics employeurs |
|-------|--------------------------------|
| 2023 | 29,1% |
| 2025 | 15,1% |

**Chute de 14 points.** Volume absolu stable (~16 000/an), mais part relative en baisse.

### 6. Q4 structurellement faible

Le 4e trimestre (oct-dec) est systematiquement **3,5 points en dessous** des autres trimestres.
Les 5 pires mois des 3 dernieres annees sont tous en Q4 2024-2025.

---

## Alertes

### Decembre 2025 : 69,7%

Plus bas niveau en 3 ans. Aucune explication identifiee.

### Ecart croissant avec prescripteurs habilites

| Indicateur | Prescripteurs | Candidats autonomes | Ecart |
|------------|---------------|---------------------|-------|
| Taux diagnostic | 98,7% | 75,6% | 23 pts |
| Taux acceptation | 17,5% | 4,5% | 13 pts |

L'ecart s'est creuse de 9 points en 3 ans (2023 : 14 pts d'ecart).

---

## Discordances entre rapports

### 1. Donnees mensuelles incoherentes

Les rapports presentent des chiffres differents pour les memes mois :

| Mois | Rapport 2/3 | Rapport 4 | Ecart |
|------|-------------|-----------|-------|
| **Sept 2025** | 7 509 avec diag (75,0%) | 8 020 avec diag (80,1%) | +511 (+5 pts) |
| **Dec 2025** | 6 327 avec diag (75,7%) | 5 824 avec diag (69,7%) | -503 (-6 pts) |

**A verifier :** Quelle est la source correcte ? Les scripts ont-ils ete executes sur des snapshots differents ?

### 2. Doublon de rapport

`taux-candidatures-autonomes-avec-diagnostic.md` et `taux-candidats-autonomes-avec-diagnostic.md`
sont quasi-identiques. L'un devrait etre supprime.

### 3. Interpretation divergente : stabilite ou inquietude ?

| Rapport | Interpretation |
|---------|----------------|
| taux-candidatures/candidats | "Stabilite remarquable autour de 75%" |
| evolution-2023-2025 | "Baisse de 14 points, alerte rouge" |

Les deux sont vrais : stabilite depuis 2024, mais niveau bien inferieur a 2023.

### 4. Cibles differentes

| Rapport | Objectif propose |
|---------|------------------|
| taux-candidatures/candidats | 85-90% fin 2026 |
| evolution-2023-2025 | 80% fin 2026 |

**80% semble plus realiste** compte tenu de la tendance.

---

## Questions ouvertes

### Donnees

1. **Pourquoi les chiffres mensuels different-ils entre rapports ?**
   Les scripts ont-ils ete executes a des moments differents ? Y a-t-il un probleme de requete ?

2. **Decembre 2025 : 69,7% ou 75,7% ?**
   Un rapport dit alerte rouge, l'autre dit stabilite. Lequel croire ?

### Causes

3. **Qu'est-ce qui a provoque la chute de decembre 2025 ?**
   - Conges des prescripteurs ?
   - Rush de candidatures de fin d'annee ?
   - Probleme technique ?

4. **Pourquoi les employeurs ont-ils divise par 2 leur part de diagnostics ?**
   - Surcharge de travail ?
   - Changement de pratiques ?
   - Manque d'incitation ?

5. **Qu'est-ce qui a cause le rebond de l'ete 2025 (78-80%) ?**
   - Campagne de sensibilisation ?
   - Effet saisonnier ?
   - Artefact statistique ?

### Strategie

6. **Faut-il bloquer les candidatures sans diagnostic ?**
   Les rapports proposent cette action comme "la plus efficace" mais alertent sur le risque de frustration et de perte de volume.

7. **L'objectif 80% est-il atteignable ?**
   Avec un doublement prevu du volume d'ici 2027, le systeme de prescription peut-il suivre ?

8. **Comment reactiver les employeurs comme diagnostiqueurs ?**
   Les rapports suggerent des incitations mais sans plan concret.

---

## Recommandations convergentes

Les 5 rapports s'accordent sur ces actions prioritaires :

### 1. Sensibiliser avant candidature

Afficher clairement l'impact du diagnostic (x45 sur l'acceptation) avant la soumission.

### 2. Cibler Q4 et decembre

Mobilisation specifique octobre-decembre : permanences prescripteurs, alertes candidats.

### 3. Investiguer decembre 2025

Analyse urgente des causes de la chute (69,7% ou 75,7% selon les sources).

### 4. Reactiver les employeurs

Inciter les SIAE a reprendre leur role de diagnostiqueur (part 2023 : 29%, actuelle : 15%).

---

## Actions immediates

1. **Verifier les donnees** : Re-executer les scripts pour clarifier les ecarts Sept/Dec 2025
2. **Supprimer le doublon** : Un des deux rapports "taux-candid*-avec-diagnostic" doit etre supprime
3. **Fixer un objectif unique** : 80% parait realiste, 85-90% optimiste

---

## Metriques de suivi

| KPI | Valeur actuelle | Cible 2026 |
|-----|-----------------|------------|
| Taux de diagnostic | 75,6% | 80% |
| Ecart Q4 vs autres trimestres | -3,5 pts | -2 pts |
| Part employeurs | 15,1% | 20% |
| Candidatures sans diagnostic | 25 879 | < 20 000 |

---

*Rapport de synthese genere le 7 janvier 2026*
