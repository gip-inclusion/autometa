# Thème : auto-prescription

*Auto-prescription metrics*

**9 cartes**

## [267] Candidatures acceptées en auto prescription

- **ID:** 1997
- **Dashboard:** 32
- **Tables:** suivi_auto_prescription

```sql
SELECT COUNT(*) AS "Candidatures acceptées en auto-prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription') 
AND ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI'))
```

## [267] % Embauches en auto prescription

- **ID:** 1998
- **Dashboard:** 32
- **Tables:** suivi_auto_prescription

```sql
SELECT CAST(SUM(CASE WHEN "public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% embauches en auto-prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI'))
```

## [267] Evolution du taux d'auto presciption dans le temps

- **ID:** 1999
- **Dashboard:** 32
- **Tables:** suivi_auto_prescription

```sql
SELECT CAST(DATE_TRUNC('month', "public"."suivi_auto_prescription"."date_diagnostic") AS date) AS "date_diagnostic", COUNT(*) AS "Nombre total de candidatures acceptées", CAST(SUM(CASE WHEN "public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux d'auto prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI')) 
GROUP BY CAST(DATE_TRUNC('month', "public"."suivi_auto_prescription"."date_diagnostic") AS date) 
ORDER BY CAST(DATE_TRUNC('month', "public"."suivi_auto_prescription"."date_diagnostic") AS date) ASC
```

## [267] Taux d'auto presciption par type de structure

- **ID:** 2009
- **Dashboard:** 32
- **Tables:** suivi_auto_prescription

```sql
SELECT "public"."suivi_auto_prescription"."type_structure" AS "type_structure", COUNT(*) AS "Nombre total de candidatures acceptées", CAST(SUM(CASE WHEN "public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux d'auto prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI')) 
GROUP BY "public"."suivi_auto_prescription"."type_structure" 
ORDER BY "public"."suivi_auto_prescription"."type_structure" ASC
```

## [267] Candidatures acceptées (toutes)

- **ID:** 2280
- **Dashboard:** 32
- **Tables:** suivi_auto_prescription

```sql
SELECT COUNT(*) AS "Candidatures acceptées en auto-prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI'))
```

## Evolution du taux d'auto-prescription

- **ID:** 3668
- **Dashboard:** 337
- **Tables:** suivi_auto_prescription

```sql
SELECT CAST(DATE_TRUNC('year', "public"."suivi_auto_prescription"."date_candidature") AS date) AS "date_candidature", CAST(SUM(CASE WHEN "public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux d'auto prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."suivi_auto_prescription"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."suivi_auto_prescription"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND ("public"."suivi_auto_prescription"."categorie_structure" = 'IAE') 
GROUP BY CAST(DATE_TRUNC('year', "public"."suivi_auto_prescription"."date_candidature") AS date) 
ORDER BY CAST(DATE_TRUNC('year', "public"."suivi_auto_prescription"."date_candidature") AS date) ASC
```

## Taux d'auto-prescription en 2023

- **ID:** 3689
- **Dashboard:** 337
- **Tables:** suivi_auto_prescription

```sql
SELECT CAST(SUM(CASE WHEN "public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux d'auto prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI')) 
AND ("public"."suivi_auto_prescription"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-1 year'))) 
AND ("public"."suivi_auto_prescription"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI'))
```

## Taux d'auto-prescription en 2024

- **ID:** 3864
- **Dashboard:** 337
- **Tables:** suivi_auto_prescription

```sql
SELECT CAST(SUM(CASE WHEN "public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux d'auto prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI')) 
AND "public"."suivi_auto_prescription"."date_candidature" BETWEEN date '2024-01-01' 
AND date '2024-12-31' 
AND (("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI'))
```

## Evolution du taux d'auto-prescription par type de SIAE

- **ID:** 3874
- **Dashboard:** 337
- **Tables:** suivi_auto_prescription

```sql
SELECT "public"."suivi_auto_prescription"."type_structure" AS "type_structure", CAST(DATE_TRUNC('year', "public"."suivi_auto_prescription"."date_candidature") AS date) AS "date_candidature", CAST(SUM(CASE WHEN "public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux d'auto prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI')) 
AND ("public"."suivi_auto_prescription"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."suivi_auto_prescription"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI')) 
GROUP BY "public"."suivi_auto_prescription"."type_structure", CAST(DATE_TRUNC('year', "public"."suivi_auto_prescription"."date_candidature") AS date) 
ORDER BY "public"."suivi_auto_prescription"."type_structure" ASC, CAST(DATE_TRUNC('year', "public"."suivi_auto_prescription"."date_candidature") AS date) ASC
```
