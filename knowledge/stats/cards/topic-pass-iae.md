# Thème : pass-iae

*PASS IAE delivery and tracking*

**9 cartes**

## [217] Expiration PASS reprise de stock AI

- **ID:** 1656
- **Dashboard:** 336
- **Tables:** pass_agréments

```sql
SELECT CAST(DATE_TRUNC('week', "public"."pass_agréments"."date_fin") AS date) AS "date_fin", COUNT(*) AS "count" 
FROM "public"."pass_agréments" 
WHERE CAST(("public"."pass_agréments"."date_fin" + INTERVAL '0 month') AS date) BETWEEN DATE_TRUNC('month', NOW()) 
AND DATE_TRUNC('month', (NOW() + INTERVAL '24 month')) 
GROUP BY CAST(DATE_TRUNC('week', "public"."pass_agréments"."date_fin") AS date) 
ORDER BY CAST(DATE_TRUNC('week', "public"."pass_agréments"."date_fin") AS date) ASC
```

## [217] Nombre de pass expirant entre le 27/11/23 et 3/12/23

- **ID:** 1677
- **Dashboard:** 217
- **Tables:** pass_agréments

```sql
SELECT "public"."pass_agréments"."département_structure_ou_org_pe" AS "département_structure_ou_org_pe", COUNT(*) AS "count" 
FROM "public"."pass_agréments" 
WHERE "public"."pass_agréments"."date_fin" BETWEEN date '2023-11-27' 
AND date '2023-12-03' 
AND ("public"."pass_agréments"."type_structure" = 'AI') 
AND (CASE WHEN "public"."pass_agréments"."injection_ai" = 0 THEN 'Non' ELSE 'Oui' END = 'Oui') 
GROUP BY "public"."pass_agréments"."département_structure_ou_org_pe" 
ORDER BY "public"."pass_agréments"."département_structure_ou_org_pe" ASC
```

## [217] Moyenne hebdo du Nombre de pass expirant en 2025

- **ID:** 1679
- **Dashboard:** 217
- **Tables:** pass_agréments

```sql
SELECT "public"."pass_agréments"."département_structure_ou_org_pe" AS "département_structure_ou_org_pe", CAST(COUNT(*) AS DOUBLE PRECISION) / 52.0 AS "Moyenne hebdomadaire PASS expirés" 
FROM "public"."pass_agréments" 
WHERE "public"."pass_agréments"."date_fin" BETWEEN date '2025-01-01' 
AND date '2025-12-31' 
AND ("public"."pass_agréments"."type_structure" = 'AI') 
AND (CASE WHEN "public"."pass_agréments"."injection_ai" = 0 THEN 'Non' ELSE 'Oui' END = 'Oui') 
GROUP BY "public"."pass_agréments"."département_structure_ou_org_pe" 
ORDER BY "public"."pass_agréments"."département_structure_ou_org_pe" ASC
```

## Nombre de pass agréments délivrés par année

- **ID:** 6236
- **Dashboard:** 337
- **Tables:** pass_agréments

```sql
SELECT CAST(DATE_TRUNC('year', "public"."pass_agréments"."date_début") AS date) AS "date_début", count(distinct "public"."pass_agréments"."id") AS "count" 
FROM "public"."pass_agréments" 
WHERE ("public"."pass_agréments"."date_début" > date '2020-12-31') 
AND ("public"."pass_agréments"."date_début" < date '2025-01-01') 
GROUP BY CAST(DATE_TRUNC('year', "public"."pass_agréments"."date_début") AS date) 
ORDER BY CAST(DATE_TRUNC('year', "public"."pass_agréments"."date_début") AS date) ASC
```

## Pass actifs à ce jour

- **ID:** 6329
- **Dashboard:** 217
- **Tables:** pass_agrements_valides

```sql
SELECT count(distinct "public"."pass_agrements_valides"."id") AS "count" 
FROM "public"."pass_agrements_valides" 
WHERE "public"."pass_agrements_valides"."validite_pass" = 'pass valide'
```

## Pass qui arrivent à expiration ce mois

- **ID:** 6330
- **Dashboard:** 217
- **Tables:** pass_agrements_valides

```sql
SELECT count(distinct "public"."pass_agrements_valides"."id") AS "count" 
FROM "public"."pass_agrements_valides" 
WHERE ("public"."pass_agrements_valides"."date_fin" >= DATE_TRUNC('month', NOW())) 
AND ("public"."pass_agrements_valides"."date_fin" < DATE_TRUNC('month', (NOW() + INTERVAL '1 month')))
```

## Pass délivrés par année (be)

- **ID:** 6353
- **Dashboard:** 217
- **Tables:** pass_agrements_valides

```sql
SELECT CAST(DATE_TRUNC('year', "public"."pass_agrements_valides"."date_début") AS date) AS "date_début", count(distinct "public"."pass_agrements_valides"."id") AS "count" 
FROM "public"."pass_agrements_valides" 
WHERE ("public"."pass_agrements_valides"."type" = 'PASS IAE (99999)') 
AND ("public"."pass_agrements_valides"."date_début" > date '2023-01-01') 
AND ("public"."pass_agrements_valides"."date_début" >= DATE_TRUNC('year', (NOW() + INTERVAL '-12 year'))) 
AND ("public"."pass_agrements_valides"."date_début" < DATE_TRUNC('year', (NOW() + INTERVAL '1 year'))) 
GROUP BY CAST(DATE_TRUNC('year', "public"."pass_agrements_valides"."date_début") AS date) 
ORDER BY CAST(DATE_TRUNC('year', "public"."pass_agrements_valides"."date_début") AS date) ASC
```

## Pass suspendus à ce jour

- **ID:** 6354
- **Dashboard:** 217
- **Tables:** pass_agrements_valides

```sql
SELECT count(distinct "public"."pass_agrements_valides"."id") AS "count" 
FROM "public"."pass_agrements_valides" 
WHERE ("public"."pass_agrements_valides"."suspension_en_cours" = 'Oui') 
AND ("public"."pass_agrements_valides"."validite_pass" = 'pass valide')
```

## Pass délivrés par mois (be)

- **ID:** 6356
- **Dashboard:** 217
- **Tables:** pass_agrements_valides

```sql
SELECT CAST(DATE_TRUNC('month', "public"."pass_agrements_valides"."date_début") AS date) AS "date_début", count(distinct "public"."pass_agrements_valides"."id") AS "count" 
FROM "public"."pass_agrements_valides" 
WHERE ("public"."pass_agrements_valides"."type" = 'PASS IAE (99999)') 
AND ("public"."pass_agrements_valides"."date_début" >= DATE_TRUNC('month', (NOW() + INTERVAL '-12 month'))) 
AND ("public"."pass_agrements_valides"."date_début" < DATE_TRUNC('month', NOW())) 
GROUP BY CAST(DATE_TRUNC('month', "public"."pass_agrements_valides"."date_début") AS date) 
ORDER BY CAST(DATE_TRUNC('month', "public"."pass_agrements_valides"."date_début") AS date) ASC
```
