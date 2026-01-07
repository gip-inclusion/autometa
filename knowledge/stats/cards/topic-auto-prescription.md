# Thème : auto-prescription

*Auto-prescription metrics*

**17 cartes**

## [267] Nombre de personnes recrutées en autoprescription critères niv 2

- **ID:** 7004
- **Dashboard:** 267
- **Tables:** public, candidats_auto_prescription

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."candidats_auto_prescription" 
WHERE ((("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") <> 0) 
OR (("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") IS NULL)) 
AND ("public"."candidats_auto_prescription"."total_critères_niveau_1" = 0) 
AND ("public"."candidats_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."candidats_auto_prescription"."type_de_candidature" = 'Autoprescription')
```

## [267] Candidatures acceptées en auto prescription

- **ID:** 7006
- **Dashboard:** 267
- **Tables:** public, suivi_auto_prescription

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

## [267] Détails critère de niveau 1

- **ID:** 7007
- **Dashboard:** 267
- **Tables:** public, candidats_auto_prescription

```sql
SELECT SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_allocataire_aah" = 1 THEN 1 ELSE 0.0 END) AS "Nombre AAH", CAST(SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_allocataire_aah" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% AAH", SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_allocataire_ass" = 1 THEN 1 ELSE 0.0 END) AS "Nombre ASS", CAST(SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_allocataire_ass" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% ASS", SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_bénéficiaire_du_rsa" = 1 THEN 1 ELSE 0.0 END) AS "Nombre bRSA", CAST(SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_bénéficiaire_du_rsa" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% bRSA", SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_detld_plus_de_24_mois" = 1 THEN 1 ELSE 0.0 END) AS "Nombre DETLD", CAST(SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_detld_plus_de_24_mois" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% DETLD", COUNT(*) AS "Total de candidats" 
FROM "public"."candidats_auto_prescription" 
WHERE ((("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") <> 0) 
OR (("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") IS NULL)) 
AND (("public"."candidats_auto_prescription"."total_critères_niveau_1" <> 0) 
OR ("public"."candidats_auto_prescription"."total_critères_niveau_1" IS NULL)) 
AND ("public"."candidats_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."candidats_auto_prescription"."type_de_candidature" = 'Autoprescription')
```

## [267] Candidats - Nombre de critères de niveau 2

- **ID:** 7010
- **Dashboard:** 267
- **Tables:** public, candidats_auto_prescription

```sql
SELECT "public"."candidats_auto_prescription"."total_critères_niveau_2" AS "total_critères_niveau_2", COUNT(*) AS "count" 
FROM "public"."candidats_auto_prescription" 
WHERE ((("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") <> 0) 
OR (("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") IS NULL)) 
AND ("public"."candidats_auto_prescription"."total_critères_niveau_1" = 0) 
AND ("public"."candidats_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."candidats_auto_prescription"."type_de_candidature" = 'Autoprescription') 
GROUP BY "public"."candidats_auto_prescription"."total_critères_niveau_2" 
ORDER BY "public"."candidats_auto_prescription"."total_critères_niveau_2" ASC
```

## [267] % Embauches en auto prescription

- **ID:** 7012
- **Dashboard:** 267
- **Tables:** public, suivi_auto_prescription

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

## [267] % de structures pratiquant l'auto prescription

- **ID:** 7013
- **Dashboard:** 267
- **Tables:** public, siae_pratiquant_autoprescription

```sql
SELECT CAST(SUM("public"."siae_pratiquant_autoprescription"."Nombre de structures utilisant l'autoprescription") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."siae_pratiquant_autoprescription"."Nombre total de structures") AS DOUBLE PRECISION), 0.0) AS "% de Siae pratiquant l'auto prescription" 
FROM "public"."siae_pratiquant_autoprescription" 
WHERE ("public"."siae_pratiquant_autoprescription"."type_structure" = 'ACI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'AI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'EI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'ETTI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'EITI')
```

## [267] Nombre de personnes recrutées en autoprescription critères niv 1

- **ID:** 7016
- **Dashboard:** 267
- **Tables:** public, candidats_auto_prescription

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."candidats_auto_prescription" 
WHERE ((("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") <> 0) 
OR (("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") IS NULL)) 
AND (("public"."candidats_auto_prescription"."total_critères_niveau_1" <> 0) 
OR ("public"."candidats_auto_prescription"."total_critères_niveau_1" IS NULL)) 
AND ("public"."candidats_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."candidats_auto_prescription"."type_de_candidature" = 'Autoprescription')
```

## [267] Nombre candidats concernés auto-prescription

- **ID:** 7017
- **Dashboard:** 267
- **Tables:** public, candidats_auto_prescription

```sql
SELECT COUNT(*) AS "Candidats concernés par l'auto-prescription" 
FROM "public"."candidats_auto_prescription" 
WHERE ((("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") <> 0) 
OR (("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") IS NULL)) 
AND ("public"."candidats_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."candidats_auto_prescription"."type_de_candidature" = 'Autoprescription')
```

## [267] Candidats - Nombre de critères de niveau 1 (w/ 0)

- **ID:** 7018
- **Dashboard:** 267
- **Tables:** public, candidats_auto_prescription

```sql
SELECT "public"."candidats_auto_prescription"."total_critères_niveau_1" AS "total_critères_niveau_1", COUNT(*) AS "count" 
FROM "public"."candidats_auto_prescription" 
WHERE ((("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") <> 0) 
OR (("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") IS NULL)) 
AND ("public"."candidats_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."candidats_auto_prescription"."type_de_candidature" = 'Autoprescription') 
GROUP BY "public"."candidats_auto_prescription"."total_critères_niveau_1" 
ORDER BY "public"."candidats_auto_prescription"."total_critères_niveau_1" ASC
```

## [267] Nombre de SIAE pratiquant l'auto prescription

- **ID:** 7020
- **Dashboard:** 267
- **Tables:** public, siae_pratiquant_autoprescription

```sql
SELECT SUM("public"."siae_pratiquant_autoprescription"."Nombre de structures utilisant l'autoprescription") AS "sum" 
FROM "public"."siae_pratiquant_autoprescription"
```

## [267] Taux d'auto presciption par type de structure

- **ID:** 7021
- **Dashboard:** 267
- **Tables:** public, suivi_auto_prescription

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

## [267] Evolution du taux d'auto presciption dans le temps

- **ID:** 7022
- **Dashboard:** 267
- **Tables:** public, suivi_auto_prescription

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

## [267] Détails critère de niveau 2

- **ID:** 7023
- **Dashboard:** 267

```sql
[No SQL in native_form]
```

## Evolution du taux d'auto-prescription

- **ID:** 7032
- **Tables:** public, suivi_auto_prescription

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

## Taux d'auto-prescription en 2024

- **ID:** 7053
- **Tables:** public, suivi_auto_prescription

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

- **ID:** 7062
- **Tables:** public, suivi_auto_prescription

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

## Taux d'auto-prescription en 2023

- **ID:** 7067
- **Tables:** public, suivi_auto_prescription

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
