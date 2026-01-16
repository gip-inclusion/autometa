# Dashboard : Esat - Tableau de bord du plan de transformation des ESAT

**URL:** /tableaux-de-bord/zoom-esat/

**32 cartes**

## Nombre de travailleurs cumulant ESAT et Entreprise adaptée ou Milieu ordinaire par Région

- **ID:** 2466
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Region" AS "Region", SUM("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs cumul ESAT EA") AS "sum", SUM("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs cumul ESAT milieu ordinaire") AS "sum_2" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Region" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Region" ASC
```

## Somme des Travailleurs parti de l'ESAT avec contrat CDI, CDD et intérim par Région

- **ID:** 2468
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Region" AS "Region", SUM("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs partis avec CDI") AS "sum", SUM("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs partis avec CDD") AS "sum_2", SUM("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs partis avec interim") AS "sum_3" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Region" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Region" ASC
```

## Chiffre d'Affaires (CA) total moyen, pourcentage moyen du CA réalisé avec secteur public, par Région

- **ID:** 2529
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Region" AS "Region", AVG("public"."ESAT - Questionnaire transfo"."Montant du CA total") AS "avg", AVG("public"."ESAT - Questionnaire transfo"."Pourcentage du CA avec secteur public") AS "avg_2" 
FROM "public"."ESAT - Questionnaire transfo" 
WHERE ("public"."ESAT - Questionnaire transfo"."Region" <> 'Martinique') 
OR ("public"."ESAT - Questionnaire transfo"."Region" IS NULL) 
GROUP BY "public"."ESAT - Questionnaire transfo"."Region" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Region" ASC
```

## Pourcentage adhésion Opco et nombre moyen de travailleurs par ESAT ayant suivi une formation Opco, par Region

- **ID:** 2554
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Region" AS "Region", SUM(CASE WHEN "public"."ESAT - Questionnaire transfo"."OPCO" = 1 THEN 1 ELSE 0.0 END) / COUNT(*) AS "Pourcentage adhésion Opco", AVG("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs ayant suivi une formation OPCO") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Region" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Region" ASC
```

## Mise en place d'une sensibilisation à l'auto-détermination pour les travailleurs

- **ID:** 2557
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Region" AS "Region", SUM(CASE WHEN "public"."ESAT - Questionnaire transfo"."Formation par un ou des professionnels de l’ESAT" = 'Formation par un ou des professionnels de l’ESAT' THEN 1 ELSE 0.0 END) AS "Formation interne", SUM(CASE WHEN "public"."ESAT - Questionnaire transfo"."Formation par un intervenant/organisme extérieur" = 'Formation par un intervenant/organisme extérieur' THEN 1 ELSE 0.0 END) AS "Formation intervenant extérieur", SUM(CASE WHEN "public"."ESAT - Questionnaire transfo"."Pas de formation mise en place" = 'Pas de formation mise en place' THEN 1 ELSE 0.0 END) AS "Pas de formation mise en place" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Region" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Region" ASC
```

## Nombre moyen de salarié(e)s en droit commun

- **ID:** 3015
- **Thème:** esat
- **Description:** Nombre moyen de salarié(e)s en droit commun par ESAT
- **Tables:** ESAT

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Nombre de salariés en droit commun") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre d'ESAT ayant répondu au questionnaire

- **ID:** 3016
- **Thème:** esat
- **Description:** sur la région filtrée
- **Tables:** ESAT

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre moyen de salarié(e)s en droit commun

- **ID:** 3017
- **Thème:** esat
- **Description:** Nombre moyen de salarié(e)s en droit commun par ESAT, sur la région filtrée
- **Tables:** ESAT

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Nombre de salariés en droit commun") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Moyenne de travailleur(se)s accompagné(e)s par ESAT, au national

- **ID:** 3019
- **Thème:** esat
- **Description:** Moyenne de travailleur(se)s accompagné(e)s par ESAT, au national
- **Tables:** ESAT

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs accompagnés") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Moyenne de travailleur(se)s accompagné(e)s par ESAT

- **ID:** 3020
- **Thème:** esat
- **Description:** Moyenne de travailleur(se)s accompagné(e)s par ESAT, sur la région filtrée
- **Tables:** ESAT

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs accompagnés") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Moyenne des places agréées par ESAT, au national

- **ID:** 3021
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Nombre de places agréées") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Moyenne des places agréées par ESAT, au national - Dupliquer

- **ID:** 3022
- **Thème:** esat
- **Description:** Moyenne des places agréées par ESAT, sur la région filtrée
- **Tables:** ESAT

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Nombre de places agréées") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre de PMSMP réalisées, au national

- **ID:** 3023
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombres de PMSMP réalisées") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre de PMSMP réalisées, filtré sur la région choisie

- **ID:** 3024
- **Thème:** esat
- **Description:** Nombre de PMSMP réalisées, filtré sur la région choisie
- **Tables:** ESAT

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombres de PMSMP réalisées") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre de travailleurs inscrits à Pôle Emploi, au national

- **ID:** 3027
- **Thème:** esat
- **Description:** Nombre de travailleurs inscrits à Pôle Emploi, au national
- **Tables:** ESAT

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs inscrits à Pôle Emploi") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre de travailleurs inscrits à Pôle Emploi, filtré sur la région choisie

- **ID:** 3028
- **Thème:** esat
- **Description:** Nombre de travailleurs inscrits à Pôle Emploi, filtré sur la région choisie
- **Tables:** ESAT

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs inscrits à Pôle Emploi") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre de MAD (mises à disposition), au national

- **ID:** 3032
- **Thème:** esat
- **Description:** Nombre de MAD (mises à disposition), au national
- **Tables:** ESAT

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombre de MAD") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre de MAD (mises à disposition), filtré sur la région choisie

- **ID:** 3033
- **Thème:** esat
- **Description:** Nombre de MAD (mises à disposition), filtré sur la région choisie
- **Tables:** ESAT

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombre de MAD") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre de travailleurs en activité Hors les Murs, au national

- **ID:** 3034
- **Thème:** esat
- **Description:** Nombre de travailleurs en activité Hors les Murs, au national
- **Tables:** ESAT

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombres de travailleurs activité hors les murs") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre de travailleurs en activité Hors les Murs, filtré sur la région choisie

- **ID:** 3036
- **Thème:** esat
- **Description:** Nombre de travailleurs en activité Hors les Murs, filtré sur la région choisie
- **Tables:** ESAT

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombres de travailleurs activité hors les murs") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Mise en place d'une formation d'auto-sensibilisation pour les salarié(e)s de l'ESAT, au niveau national

- **ID:** 3058
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Mise en place formation auto sensibilisation pour les professio" AS "Mise en place formation auto sensibilisation pour l_2995b879", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Mise en place formation auto sensibilisation pour les professio" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Mise en place formation auto sensibilisation pour les professio" ASC
```

## Mise en place d'une formation d'auto-sensibilisation pour les salarié(e)s de l'ESAT, filtré sur la région choisie

- **ID:** 3059
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Mise en place formation auto sensibilisation pour les professio" AS "Mise en place formation auto sensibilisation pour l_2995b879", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Mise en place formation auto sensibilisation pour les professio" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Mise en place formation auto sensibilisation pour les professio" ASC
```

## Mise en place d'une instance mixte salariés / travailleurs sur QVT, hygiène et sécurité et éval risques pro, au national

- **ID:** 3060
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Instance mixte QVT" AS "Instance mixte QVT", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Instance mixte QVT" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Instance mixte QVT" ASC
```

## Mise en place d'une instance mixte salariés / travailleurs sur QVT, hygiène et sécurité et éval risques pro, filtré sur la région choisie

- **ID:** 3061
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Instance mixte QVT" AS "Instance mixte QVT", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Instance mixte QVT" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Instance mixte QVT" ASC
```

## Mise en place d'une prime PEPA pour les travailleur(se)s, au national

- **ID:** 3062
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."PEPA" AS "PEPA", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."PEPA" 
ORDER BY "public"."ESAT - Questionnaire transfo"."PEPA" ASC
```

## Mise en place d'une prime PEPA pour les travailleur(se)s, filtré sur la région choisie

- **ID:** 3063
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."PEPA" AS "PEPA", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."PEPA" 
ORDER BY "public"."ESAT - Questionnaire transfo"."PEPA" ASC
```

## Convention de partenariat avec un ou plusieurs acteurs du SPE (pole emploi, cap emploi, ML) , au national

- **ID:** 3064
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Convention de partenariat" AS "Convention de partenariat", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Convention de partenariat" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Convention de partenariat" ASC
```

## Convention de partenariat avec un ou plusieurs acteurs du SPE (pole emploi, cap emploi, ML) , filtré sur la région choisie

- **ID:** 3065
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Convention de partenariat" AS "Convention de partenariat", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Convention de partenariat" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Convention de partenariat" ASC
```

## Partenariat Avec Entreprise Adaptée, au national

- **ID:** 3066
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Partenariats avec entreprise adaptée" AS "Partenariats avec entreprise adaptée", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Partenariats avec entreprise adaptée" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Partenariats avec entreprise adaptée" ASC
```

## Partenariat Avec Entreprise Adaptée, filtré sur la région choisie

- **ID:** 3067
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Partenariats avec entreprise adaptée" AS "Partenariats avec entreprise adaptée", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Partenariats avec entreprise adaptée" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Partenariats avec entreprise adaptée" ASC
```

## Budget commercial, filtré sur la région choisie

- **ID:** 3069
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

## Budget activité sociale, filtré sur la région choisie

- **ID:** 3071
- **Thème:** esat
- **Tables:** ESAT

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Budget activité sociale" AS "Budget activité sociale", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Budget activité sociale" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Budget activité sociale" ASC
```
