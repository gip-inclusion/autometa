# Dashboard : ESAT - Tableau de bord 2024

☞  Votre tableau de bord est composé de 6 onglets thématiques

## 26 mars 2025


Date de la dernière mise à jour

![](https://github.com/gip-inclusion/pilotage/blob/staging/pilotage/static/images/metabase/explication_onglets.png?raw=true)

💾 Source des données : questionnaire 2024 sur les actions mises en œuvre en 2023 - suivi du plan de transformation des ESAT

1 - **Chiffres clés :** Quel est le nombre de salariés (ETP) par ESAT ? Quel est le nombre, l'âge et l'ancienneté des travailleurs ? Quel est le pourcentage d'ESAT publics ?

2 -  **Dynamiques de parcours :** Quelles activités hors les murs les travailleurs pratiquent-il ? Combien de travailleurs partagent leur temps de travail avec un autre emploi partiel ? Combien sont partis de l'ESAT, vers quel milieu et avec quel type de contrat ?

3 - **Droits et pouvoir d'agir des personnes accompagnées  :**  Les travailleurs ont-il bénéficié d'une formation, d'une sensibilisation à l'auto détermination ? L'ESAT a t-il mis en place un ca

**URL:** /tableaux-de-bord/zoom-esat-2025/

**54 cartes**

## [471] Pourcentage moyen de travailleurs ayant travaillé au moins 1 dimanche en 2023

- **ID:** 7131
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant travaillé un dimanche") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Nombre moyen par ESAT de travailleurs partis pour une entreprise adaptée, pour le public, pour le privé ou pour une association

- **ID:** 7132
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour entreprise adaptée") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour le public") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour le privé") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour association") AS "avg_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Nombre de répondants

- **ID:** 7134
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471]  Travailleurs accompagnés par ESAT, dont emploi en milieu ordinaire avant ESAT , Esat pour la 1ere fois, en remplacement, et voulant sortir du milieu protégé - Modifié

- **ID:** 7135
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs accompagnés") AS "sum", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant occupé un emploi en milieu ordina") AS "sum_2", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs étant en ESAT pour la 1ere fois") AS "sum_3", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs admis temporairement en remplacement") AS "sum_4", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs voulant sortir du milieu protégé") AS "sum_5" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Somme des places autorisées par ESAT

- **ID:** 7136
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Places autorisées par ARS") AS "sum" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Montant médian du CA total

- **ID:** 7137
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT PERCENTILE_CONT(0.5) within group (order by "public"."Esat - Questionnaire 2024"."Montant du CA total") AS "median" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Somme du nombre de  salariés en droit commun (ETP)

- **ID:** 7139
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de salariés en droit commun") AS "sum" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Montant médian en investissement de production (parmi les ESAT ayant investi)

- **ID:** 7140
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT PERCENTILE_CONT(0.5) within group (order by "public"."Esat - Questionnaire 2024"."Montant investissement production") AS "median" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant investissement production" > 0
```

## [471] Moyenne du nombre de travailleurs accompagnés

- **ID:** 7141
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs accompagnés") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Montant moyen par travailleur de la prime de partage de la valeur (PPV) pour les travailleurs l'ayant touché

- **ID:** 7142
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Montant moyen PPV") AS "avg" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant moyen PPV" > 0
```

## [471] Pourcentage de travailleurs ayant bénéficié du dispositif UAAT

- **ID:** 7143
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié dispositif UAAT") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Votre ESAT contribue t'il à l'OPCO Santé ou l'OPCA ANFH?

- **ID:** 7144
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Contribution OPCO ou OPCA" AS "Contribution OPCO ou OPCA", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Contribution OPCO ou OPCA" 
ORDER BY "public"."Esat - Questionnaire 2024"."Contribution OPCO ou OPCA" ASC
```

## [471] Age moyen des travailleurs

- **ID:** 7145
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Age moyen des travailleurs") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage moyen de travailleurs par ESAT  ayant bénéficié d'une RAE ou RSFP

- **ID:** 7146
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié de RAE ou RSFP") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471]  Montant médian de l'investissement mise aux normes sécurité  et accessibilité

- **ID:** 7147
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT PERCENTILE_CONT(0.5) within group (order by "public"."Esat - Questionnaire 2024"."Montant investissement mise aux normes sécurité accessibilit") AS "median" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant investissement mise aux normes sécurité accessibilit" > 0
```

## [471] Pourcentage moyen par ESAT de travailleurs partis avec CDI,  CDD, contrat intérim, contrat de professionalisation, contrat d'apprentissage

- **ID:** 7148
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec CDI") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec CDD") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec interim") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec contrat pro") AS "avg_4", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec contrat apprentissage") AS "avg_5" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Budget activité sociale

- **ID:** 7151
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Budget activité sociale" AS "Budget activité sociale", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Budget activité sociale" 
ORDER BY "public"."Esat - Questionnaire 2024"."Budget activité sociale" ASC
```

## [471] Pourcentage moyen par ESAT de travailleurs partis pour une entreprise adaptée, pour le public, pour le privé ou pour une association

- **ID:** 7152
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis pour entreprise adaptée") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis pour le public") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis pour le privé") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis pour association") AS "avg_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Mise en place documents pour travailleurs en FALC (en % d'ESAT)

- **ID:** 7153
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Mise en place documents pour travailleurs en FALC" AS "Mise en place documents pour travailleurs en FALC", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Mise en place documents pour travailleurs en FALC" 
ORDER BY "public"."Esat - Questionnaire 2024"."Mise en place documents pour travailleurs en FALC" ASC
```

## [471] Pourcentage moyen du CA avec secteur public

- **ID:** 7154
- **Thème:** esat

```sql
[No SQL in native_form]
```

## [471] Nombre moyen de conseillers insertion et inclusion (en ETP)

- **ID:** 7155
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de conseillers insertion et inclusion") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Taux de contribution moyen OPCO Santé ou OPCA ANFH

- **ID:** 7156
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Taux de contribution Opco santé ou ANFH") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Type de complémentaire santé mise en place (en % d'ESAT)

- **ID:** 7157
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Complémentaire santé" AS "Complémentaire santé", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Complémentaire santé" 
ORDER BY "public"."Esat - Questionnaire 2024"."Complémentaire santé" ASC
```

## [471] Pourcentage d'ESAT ayant investi pour la production en 2023

- **ID:** 7158
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT CAST(SUM(CASE WHEN "public"."Esat - Questionnaire 2024"."Montant investissement production" > 0 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Pourcentage d'ESAT ayant investi pour la production en 2023" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Moyenne  du nombre de  salariés en droit commun (ETP)

- **ID:** 7159
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de salariés en droit commun") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Nombre moyen par ESAT de travailleurs partis pour une entreprise adaptée, pour le public, pour le privé ou pour une association

- **ID:** 7160
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour entreprise adaptée") AS "sum", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour le public") AS "sum_2", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour le privé") AS "sum_3", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour association") AS "sum_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage d'ESAT ayant reçu un soutien FATESAT, parmi les ESAT ayant investi pour leur production

- **ID:** 7161
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT CAST(SUM(CASE WHEN "public"."Esat - Questionnaire 2024"."Montant soutien FATESAT" > 0 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Pourcentage d'ESAT ayant reçu un soutien FATESAT" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant investissement production" > 0
```

## [471] Somme du nombre de travailleurs accompagnés

- **ID:** 7162
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs accompagnés") AS "sum" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage moyen de travailleurs ayant bénéficié d'une formation par les salariés de l'ESAT

- **ID:** 7163
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié formation par sa") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Mise en place d'une instance QVT

- **ID:** 7164
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Instance mixte QVT" AS "Instance mixte QVT", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Instance mixte QVT" 
ORDER BY "public"."Esat - Questionnaire 2024"."Instance mixte QVT" ASC
```

## [471] Nombre moyen par ESAT de travailleurs ayant effectué une PMSMP,  une prestation extérieure pour une entreprise, et une MAD (mise à disposition)

- **ID:** 7165
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant effectué une PMSMP") AS "sum", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant réalisé une prestation pour une ") AS "sum_2", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant réalisé une MAD") AS "sum_3" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Combien d'ESAT  ont eu des refus de PMSMP par des organismes du SPE?

- **ID:** 7166
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Refus de PMSMP par des organismes du SPE?" AS "Refus de PMSMP par des organismes du SPE?", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Refus de PMSMP par des organismes du SPE?" 
ORDER BY "public"."Esat - Questionnaire 2024"."Refus de PMSMP par des organismes du SPE?" ASC
```

## [471] Pourcentage moyen de la rémunération des travailleurs prise en charge par l'ESAT

- **ID:** 7168
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de rémunération du travailleur pris en charge par") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Suite de parcours après RAE / RSFP

- **ID:** 7169
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Suite de parcours après reconnaissance - regroupé" AS "Suite de parcours après reconnaissance - regroupé", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant bénéficié de RAE ou RSFP" > 0 
GROUP BY "public"."Esat - Questionnaire 2024"."Suite de parcours après reconnaissance - regroupé" 
ORDER BY "public"."Esat - Questionnaire 2024"."Suite de parcours après reconnaissance - regroupé" ASC
```

## [471] Budget commercial

- **ID:** 7170
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Budget commercial" AS "Budget commercial", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Budget commercial" 
ORDER BY "public"."Esat - Questionnaire 2024"."Budget commercial" ASC
```

## [471] Mise en place auto sensibilisation (en % d'ESAT)

- **ID:** 7172
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Mise en place formation auto sensilibisation" AS "Mise en place formation auto sensilibisation", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Mise en place formation auto sensilibisation" 
ORDER BY "public"."Esat - Questionnaire 2024"."Mise en place formation auto sensilibisation" ASC
```

## [471] Mise en place d'un carnet de parcours et compétences (en % d'ESAT)

- **ID:** 7173
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Mise en place carnet de parcours et compétence" AS "Mise en place carnet de parcours et compétence", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Mise en place carnet de parcours et compétence" 
ORDER BY "public"."Esat - Questionnaire 2024"."Mise en place carnet de parcours et compétence" ASC
```

## [471] Conventions de partenariat (en % d'ESAT)

- **ID:** 7174
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Conventions partenariat - regroupé" AS "Conventions partenariat - regroupé", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Conventions partenariat - regroupé" 
ORDER BY "public"."Esat - Questionnaire 2024"."Conventions partenariat - regroupé" ASC
```

## [471] Pourcentage moyen du financement de la complémentaire santé par les ESAT

- **ID:** 7175
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage financement complémentaire santé ESAT") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage de travailleurs ayant bénéficié formation à l'auto sensibilisation, parmi les ESAT l'ayant mis en place, en 2023

- **ID:** 7176
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié formation auto s") AS "avg" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié formation auto s" > 0
```

## [471] Pourcentage d'ESAT public

- **ID:** 7178
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."ESAT public" AS "ESAT public", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."ESAT public" 
ORDER BY "public"."Esat - Questionnaire 2024"."ESAT public" ASC
```

## [471] Nombre moyen par ESAT de travailleurs partis avec CDI,  CDD, contrat intérim, contrat de professionalisation, contrat d'apprentissage

- **ID:** 7179
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec CDI") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec CDD") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec interim") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec contrat pro") AS "avg_4", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec contrat apprentissage") AS "avg_5" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage  de travailleurs ayant effectué une PMSMP,  une prestation extérieure pour une entreprise, et une MAD (mise à disposition)

- **ID:** 7180
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant effectué une PMSMP") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant réalisé une prestation pour") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant réalisé une MAD") AS "avg_3" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Nombre moyen par ESAT de travailleurs ayant effectué une PMSMP,  une prestation extérieure pour une entreprise, et une MAD (mise à disposition)

- **ID:** 7181
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant effectué une PMSMP") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant réalisé une prestation pour une ") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant réalisé une MAD") AS "avg_3" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Types de formation dont ont bénéficié les travailleurs pour reconnaître et développer leurs compétences

- **ID:** 7182
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Types de formations dont ont benéficié les travailleurs - reg" AS "Types de formations dont ont benéficié les travai_90d6594d", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Types de formations dont ont benéficié les travailleurs - reg" 
ORDER BY "public"."Esat - Questionnaire 2024"."Types de formations dont ont benéficié les travailleurs - reg" ASC
```

## [471] Travailleurs en temps partiel (%), inscrits comme DE à France Travail (%), en cumul temps partiel entreprise adaptée et ESAT (%), en cumul temps partiel milieu ordinaire et ESAT (%)

- **ID:** 7183
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs en temps partiel") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs inscrits comme DE à France travail") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant cumulé entreprise adaptée e") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant cumulé  milieu ordinaire et ") AS "avg_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage d'ESAT ayant investi pour la mise aux normes sécurité et accessibilité en 2023

- **ID:** 7184
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT CAST(SUM(CASE WHEN "public"."Esat - Questionnaire 2024"."Montant investissement mise aux normes sécurité accessibilit" > 0 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Pourcentage d'ESAT ayant investi pour la mise aux n_4ce75df4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Travailleurs partis avec CDI,  CDD, contrat intérim, contrat de professionalisation, contrat d'apprentissage - Modifié

- **ID:** 7185
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec CDI") AS "sum", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec CDD") AS "sum_2", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec interim") AS "sum_3", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec contrat pro") AS "sum_4", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec contrat apprentissage") AS "sum_5" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Moyenne des places autorisées par ESAT

- **ID:** 7186
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Places autorisées par ARS") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Montant moyen de la prime d'intéressement par travailleur, pour les travailleurs l'ayant touché

- **ID:** 7187
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Montant moyen prime interessement des travailleurs") AS "avg" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant moyen prime interessement des travailleurs" > 0
```

## [471] Prime d'activité versée aux travailleurs (en % d'ESAT)

- **ID:** 7189
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Prime activité pour travailleurs" AS "Prime activité pour travailleurs", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Prime activité pour travailleurs" 
ORDER BY "public"."Esat - Questionnaire 2024"."Prime activité pour travailleurs" ASC
```

## [471] Election d'un délégué en 2023

- **ID:** 7191
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Délégué élu" AS "Délégué élu", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Délégué élu" 
ORDER BY "public"."Esat - Questionnaire 2024"."Délégué élu" ASC
```

## [471]  Pourcentage moyen de travailleurs sans utilisation CPF

- **ID:** 7192
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs sans utilisation CPF") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Il y a t'il eu des refus de financement par l'OPCO Santé ou l'OPCA ANFH?

- **ID:** 7193
- **Thème:** esat
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Refus de financement OPCO Santé ou ANFH" AS "Refus de financement OPCO Santé ou ANFH", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Refus de financement OPCO Santé ou ANFH" 
ORDER BY "public"."Esat - Questionnaire 2024"."Refus de financement OPCO Santé ou ANFH" ASC
```
