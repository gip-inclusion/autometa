# Dashboard : ESAT - Tableau de bord 2024

**URL:** /tableaux-de-bord/zoom-esat-2024/

**64 cartes**

## Nombre d'ESAT ayant répondu au questionnaire

- **ID:** 3013
- **Thème:** esat
- **Description:** Au national
- **Tables:** ESAT

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre moyen de travailleurs accompagnés par ESAT, au national

- **ID:** 3018
- **Thème:** esat
- **Description:** Nombre moyen de travailleurs accompagnés par ESAT, au national
- **Tables:** ESAT

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs accompagnés") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Budget commercial, au national

- **ID:** 3068
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Budget commercial" AS "Budget commercial", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
WHERE ("public"."ESAT - Questionnaire transfo"."Budget commercial" <> 'excédentaires') 
OR ("public"."ESAT - Questionnaire transfo"."Budget commercial" IS NULL) 
GROUP BY "public"."ESAT - Questionnaire transfo"."Budget commercial" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Budget commercial" ASC
```

## Budget activité sociale, au national

- **ID:** 3070
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Budget activité sociale" AS "Budget activité sociale", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Budget activité sociale" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Budget activité sociale" ASC
```

## [471] Moyenne  du nombre de  salariés en droit commun (ETP)

- **ID:** 4941
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de salariés en droit commun") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Moyenne du nombre de travailleurs accompagnés

- **ID:** 4942
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs accompagnés") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Moyenne des places autorisées par ESAT

- **ID:** 4943
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Places autorisées par ARS") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Age moyen des travailleurs

- **ID:** 4944
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Age moyen des travailleurs") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471]  Travailleurs accompagnés par ESAT, dont emploi en milieu ordinaire avant ESAT , Esat pour la 1ere fois, en remplacement, et voulant sortir du milieu protégé

- **ID:** 5013
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs accompagnés") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant occupé un emploi en milieu ordina") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs étant en ESAT pour la 1ere fois") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs admis temporairement en remplacement") AS "avg_4", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs voulant sortir du milieu protégé") AS "avg_5" 
FROM "public"."Esat - Questionnaire 2024"
```

## Travailleurs en temps partiel, inscrits comme DE à France Travail, en cumul temps partiel entreprise adaptée et ESAT, en cumul temps partiel milieu ordinaire et ESAT

- **ID:** 5014
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs en temps partiel") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs inscrits comme DE à France travail") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant cumulé entreprise adaptée et tem") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant cumulé  milieu ordinaire et temps") AS "avg_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Travailleurs en temps partiel (%), inscrits comme DE à France Travail (%), en cumul temps partiel entreprise adaptée et ESAT (%), en cumul temps partiel milieu ordinaire et ESAT (%)

- **ID:** 5015
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs en temps partiel") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs inscrits comme DE à France travail") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant cumulé entreprise adaptée e") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant cumulé  milieu ordinaire et ") AS "avg_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Nombre moyen par ESAT de travailleurs ayant effectué une PMSMP,  une prestation extérieure pour une entreprise, et une MAD (mise à disposition)

- **ID:** 5028
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant effectué une PMSMP") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant réalisé une prestation pour une ") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant réalisé une MAD") AS "avg_3" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage  de travailleurs ayant effectué une PMSMP,  une prestation extérieure pour une entreprise, et une MAD (mise à disposition)

- **ID:** 5034
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant effectué une PMSMP") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant réalisé une prestation pour") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant réalisé une MAD") AS "avg_3" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Nombre moyen par ESAT de travailleurs partis pour une entreprise adaptée, pour le public, pour le privé ou pour une association

- **ID:** 5035
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour entreprise adaptée") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour le public") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour le privé") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour association") AS "avg_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage moyen par ESAT de travailleurs partis pour une entreprise adaptée, pour le public, pour le privé ou pour une association

- **ID:** 5036
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis pour entreprise adaptée") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis pour le public") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis pour le privé") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis pour association") AS "avg_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Nombre moyen par ESAT de travailleurs partis avec CDI,  CDD, contrat intérim, contrat de professionalisation, contrat d'apprentissage

- **ID:** 5039
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec CDI") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec CDD") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec interim") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec contrat pro") AS "avg_4", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec contrat apprentissage") AS "avg_5" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage moyen par ESAT de travailleurs partis avec CDI,  CDD, contrat intérim, contrat de professionalisation, contrat d'apprentissage

- **ID:** 5040
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec CDI") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec CDD") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec interim") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec contrat pro") AS "avg_4", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec contrat apprentissage") AS "avg_5" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Combien d'ESAT  ont eu des refus de PMSMP par des organismes du SPE?

- **ID:** 5041
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Refus de PMSMP par des organismes du SPE?" AS "Refus de PMSMP par des organismes du SPE?", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Refus de PMSMP par des organismes du SPE?" 
ORDER BY "public"."Esat - Questionnaire 2024"."Refus de PMSMP par des organismes du SPE?" ASC
```

## [471] Votre ESAT contribue t'il à l'OPCO Santé ou l'OPCA ANFH?

- **ID:** 5042
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Contribution OPCO ou OPCA" AS "Contribution OPCO ou OPCA", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Contribution OPCO ou OPCA" 
ORDER BY "public"."Esat - Questionnaire 2024"."Contribution OPCO ou OPCA" ASC
```

## [471] Taux de contribution moyen OPCO Santé ou OPCA ANFH

- **ID:** 5043
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Taux de contribution Opco santé ou ANFH") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Types de formation dont ont bénéficié les travailleurs pour reconnaître et développer leurs compétences

- **ID:** 5045
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Types de formations dont ont benéficié les travailleurs - reg" AS "Types de formations dont ont benéficié les travai_90d6594d", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Types de formations dont ont benéficié les travailleurs - reg" 
ORDER BY "public"."Esat - Questionnaire 2024"."Types de formations dont ont benéficié les travailleurs - reg" ASC
```

## [471] Pourcentage moyen de travailleurs par ESAT  ayant bénéficié d'une RAE ou RSFP

- **ID:** 5046
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié de RAE ou RSFP") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Il y a t'il eu des refus de financement par l'OPCO Santé ou l'OPCA ANFH?

- **ID:** 5047
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Refus de financement OPCO Santé ou ANFH" AS "Refus de financement OPCO Santé ou ANFH", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Refus de financement OPCO Santé ou ANFH" 
ORDER BY "public"."Esat - Questionnaire 2024"."Refus de financement OPCO Santé ou ANFH" ASC
```

## [471] Suite de parcours après RAE / RSFP

- **ID:** 5048
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Suite de parcours après reconnaissance - regroupé" AS "Suite de parcours après reconnaissance - regroupé", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant bénéficié de RAE ou RSFP" > 0 
GROUP BY "public"."Esat - Questionnaire 2024"."Suite de parcours après reconnaissance - regroupé" 
ORDER BY "public"."Esat - Questionnaire 2024"."Suite de parcours après reconnaissance - regroupé" ASC
```

## [471]  Pourcentage moyen de travailleurs sans utilisation CPF

- **ID:** 5050
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs sans utilisation CPF") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage moyen de travailleurs ayant bénéficié d'une formation par les salariés de l'ESAT

- **ID:** 5051
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié formation par sa") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Montant médian du CA total

- **ID:** 5052
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT PERCENTILE_CONT(0.5) within group (order by "public"."Esat - Questionnaire 2024"."Montant du CA total") AS "median" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Budget commercial

- **ID:** 5053
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Budget commercial" AS "Budget commercial", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Budget commercial" 
ORDER BY "public"."Esat - Questionnaire 2024"."Budget commercial" ASC
```

## [471] Pourcentage moyen du CA avec secteur public

- **ID:** 5054
- **Thème:** candidatures

## [471] Budget activité sociale

- **ID:** 5055
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Budget activité sociale" AS "Budget activité sociale", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Budget activité sociale" 
ORDER BY "public"."Esat - Questionnaire 2024"."Budget activité sociale" ASC
```

## [471]  Montant médian de l'investissement mise aux normes sécurité  et accessibilité

- **ID:** 5343
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT PERCENTILE_CONT(0.5) within group (order by "public"."Esat - Questionnaire 2024"."Montant investissement mise aux normes sécurité accessibilit") AS "median" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant investissement mise aux normes sécurité accessibilit" > 0
```

## [471] Montant médian en investissement de production (parmi les ESAT ayant investi)

- **ID:** 5346
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT PERCENTILE_CONT(0.5) within group (order by "public"."Esat - Questionnaire 2024"."Montant investissement production") AS "median" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant investissement production" > 0
```

## [471] Pourcentage d'ESAT ayant investi pour la mise aux normes sécurité et accessibilité en 2023

- **ID:** 5347
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT CAST(SUM(CASE WHEN "public"."Esat - Questionnaire 2024"."Montant investissement mise aux normes sécurité accessibilit" > 0 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Pourcentage d'ESAT ayant investi pour la mise aux n_4ce75df4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage d'ESAT ayant investi pour la production en 2023

- **ID:** 5348
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT CAST(SUM(CASE WHEN "public"."Esat - Questionnaire 2024"."Montant investissement production" > 0 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Pourcentage d'ESAT ayant investi pour la production en 2023" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage d'ESAT ayant reçu un soutien FATESAT, parmi les ESAT ayant investi pour leur production

- **ID:** 5353
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT CAST(SUM(CASE WHEN "public"."Esat - Questionnaire 2024"."Montant soutien FATESAT" > 0 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Pourcentage d'ESAT ayant reçu un soutien FATESAT" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant investissement production" > 0
```

## [471] Nombre de répondants

- **ID:** 5357
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Conventions de partenariat (en % d'ESAT)

- **ID:** 5373
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Conventions partenariat - regroupé" AS "Conventions partenariat - regroupé", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Conventions partenariat - regroupé" 
ORDER BY "public"."Esat - Questionnaire 2024"."Conventions partenariat - regroupé" ASC
```

## [471] Mise en place auto sensibilisation (en % d'ESAT)

- **ID:** 5382
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Mise en place formation auto sensilibisation" AS "Mise en place formation auto sensilibisation", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Mise en place formation auto sensilibisation" 
ORDER BY "public"."Esat - Questionnaire 2024"."Mise en place formation auto sensilibisation" ASC
```

## [471] Pourcentage de travailleurs ayant bénéficié du dispositif UAAT

- **ID:** 5384
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié dispositif UAAT") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage de travailleurs ayant bénéficié formation à l'auto sensibilisation, parmi les ESAT l'ayant mis en place, en 2023

- **ID:** 5385
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié formation auto s") AS "avg" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié formation auto s" > 0
```

## [471] Mise en place d'un carnet de parcours et compétences (en % d'ESAT)

- **ID:** 5386
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Mise en place carnet de parcours et compétence" AS "Mise en place carnet de parcours et compétence", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Mise en place carnet de parcours et compétence" 
ORDER BY "public"."Esat - Questionnaire 2024"."Mise en place carnet de parcours et compétence" ASC
```

## [471] Mise en place documents pour travailleurs en FALC (en % d'ESAT)

- **ID:** 5387
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Mise en place documents pour travailleurs en FALC" AS "Mise en place documents pour travailleurs en FALC", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Mise en place documents pour travailleurs en FALC" 
ORDER BY "public"."Esat - Questionnaire 2024"."Mise en place documents pour travailleurs en FALC" ASC
```

## [471] Election d'un délégué en 2023

- **ID:** 5388
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Délégué élu" AS "Délégué élu", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Délégué élu" 
ORDER BY "public"."Esat - Questionnaire 2024"."Délégué élu" ASC
```

## [471] Mise en place d'une instance QVT

- **ID:** 5389
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Instance mixte QVT" AS "Instance mixte QVT", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Instance mixte QVT" 
ORDER BY "public"."Esat - Questionnaire 2024"."Instance mixte QVT" ASC
```

## [471] Montant moyen de la prime d'intéressement par travailleur, pour les travailleurs l'ayant touché

- **ID:** 5390
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Montant moyen prime interessement des travailleurs") AS "avg" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant moyen prime interessement des travailleurs" > 0
```

## [471] Montant moyen par travailleur de la prime de partage de la valeur (PPV) pour les travailleurs l'ayant touché

- **ID:** 5391
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Montant moyen PPV") AS "avg" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant moyen PPV" > 0
```

## [471] Pourcentage moyen de la rémunération des travailleurs prise en charge par l'ESAT

- **ID:** 5392
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de rémunération du travailleur pris en charge par") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Prime d'activité versée aux travailleurs (en % d'ESAT)

- **ID:** 5394
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Prime activité pour travailleurs" AS "Prime activité pour travailleurs", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Prime activité pour travailleurs" 
ORDER BY "public"."Esat - Questionnaire 2024"."Prime activité pour travailleurs" ASC
```

## [471] Type de complémentaire santé mise en place (en % d'ESAT)

- **ID:** 5395
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Complémentaire santé" AS "Complémentaire santé", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Complémentaire santé" 
ORDER BY "public"."Esat - Questionnaire 2024"."Complémentaire santé" ASC
```

## [471] Pourcentage moyen du financement de la complémentaire santé par les ESAT

- **ID:** 5396
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage financement complémentaire santé ESAT") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage moyen de travailleurs ayant travaillé au moins 1 dimanche en 2023

- **ID:** 5399
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant travaillé un dimanche") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Nombre moyen de conseillers insertion et inclusion (en ETP)

- **ID:** 5406
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de conseillers insertion et inclusion") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## Pourcentage moyen du CA avec secteur public

- **ID:** 5407
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Pourcentage du CA avec secteur public") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Financement OPCO

- **ID:** 5409
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "source"."Financement Opco" AS "Financement Opco", COUNT(*) AS "count" 
FROM (SELECT CASE WHEN "public"."ESAT - Questionnaire transfo"."OPCO" = 1 THEN 'oui' WHEN "public"."ESAT - Questionnaire transfo"."OPCO" = 0 THEN 'non' END AS "Financement Opco" 
FROM "public"."ESAT - Questionnaire transfo") AS "source" 
GROUP BY "source"."Financement Opco" 
ORDER BY "source"."Financement Opco" ASC
```

## Nombre de conseillers insertion et inclusion (en ETP)

- **ID:** 5410
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."nombre de conseillers") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## [471] Pourcentage d'ESAT public

- **ID:** 5455
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."ESAT public" AS "ESAT public", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."ESAT public" 
ORDER BY "public"."Esat - Questionnaire 2024"."ESAT public" ASC
```

## [471] Somme du nombre de  salariés en droit commun (ETP)

- **ID:** 6065
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de salariés en droit commun") AS "sum" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Somme du nombre de travailleurs accompagnés

- **ID:** 6066
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs accompagnés") AS "sum" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Somme des places autorisées par ESAT

- **ID:** 6067
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Places autorisées par ARS") AS "sum" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471]  Travailleurs accompagnés par ESAT, dont emploi en milieu ordinaire avant ESAT , Esat pour la 1ere fois, en remplacement, et voulant sortir du milieu protégé - Modifié

- **ID:** 6068
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs accompagnés") AS "sum", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant occupé un emploi en milieu ordina") AS "sum_2", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs étant en ESAT pour la 1ere fois") AS "sum_3", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs admis temporairement en remplacement") AS "sum_4", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs voulant sortir du milieu protégé") AS "sum_5" 
FROM "public"."Esat - Questionnaire 2024"
```

## Travailleurs en temps partiel, inscrits comme DE à France Travail, en cumul temps partiel entreprise adaptée et ESAT, en cumul temps partiel milieu ordinaire et ESAT

- **ID:** 6069
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs en temps partiel") AS "sum", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs inscrits comme DE à France travail") AS "sum_2", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant cumulé entreprise adaptée et tem") AS "sum_3", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant cumulé  milieu ordinaire et temps") AS "sum_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Nombre moyen par ESAT de travailleurs ayant effectué une PMSMP,  une prestation extérieure pour une entreprise, et une MAD (mise à disposition)

- **ID:** 6070
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant effectué une PMSMP") AS "sum", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant réalisé une prestation pour une ") AS "sum_2", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant réalisé une MAD") AS "sum_3" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Nombre moyen par ESAT de travailleurs partis pour une entreprise adaptée, pour le public, pour le privé ou pour une association

- **ID:** 6071
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour entreprise adaptée") AS "sum", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour le public") AS "sum_2", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour le privé") AS "sum_3", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour association") AS "sum_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Travailleurs partis avec CDI,  CDD, contrat intérim, contrat de professionalisation, contrat d'apprentissage - Modifié

- **ID:** 6072
- **Thème:** esat
- **Tables:** Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec CDI") AS "sum", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec CDD") AS "sum_2", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec interim") AS "sum_3", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec contrat pro") AS "sum_4", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec contrat apprentissage") AS "sum_5" 
FROM "public"."Esat - Questionnaire 2024"
```
