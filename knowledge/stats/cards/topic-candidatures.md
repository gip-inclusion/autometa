# Thème : candidatures

*Candidature metrics, states, flows*

**49 cartes**

## [267] Candidatures acceptées (toutes)

- **ID:** 7008
- **Dashboard:** 267
- **Tables:** public, suivi_auto_prescription

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

## Taux d'acceptation et refus des prescriptions

- **ID:** 7027
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures refusées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."candidatures_echelle_locale"."type_prescripteur" = 'Autre') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Département') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Nouveaux prescripteurs') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE')) 
GROUP BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## Taux d'acceptation et refus des prescriptions par type de SIAE en 2024

- **ID:** 7029
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures refusées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2024-01-01' 
AND date '2024-12-31' 
AND (("public"."candidatures_echelle_locale"."type_prescripteur" = 'Autre') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Département') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Nouveaux prescripteurs') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE')) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND ("public"."candidatures_echelle_locale"."région_structure" = 'Nouvelle-Aquitaine') 
GROUP BY "public"."candidatures_echelle_locale"."type_structure" 
ORDER BY "public"."candidatures_echelle_locale"."type_structure" ASC
```

## Nombre de candidatures acceptées en 2023

- **ID:** 7030
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-1 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Taux de candidatures acceptées par les SIAE en 2024

- **ID:** 7034
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2024-01-01' 
AND date '2024-12-31' 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Taux d'acceptation et refus des prescriptions par type de SIAE en 2023

- **ID:** 7036
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures refusées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-1 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."candidatures_echelle_locale"."type_prescripteur" = 'Autre') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Département') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Nouveaux prescripteurs') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE')) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
GROUP BY "public"."candidatures_echelle_locale"."type_structure" 
ORDER BY "public"."candidatures_echelle_locale"."type_structure" ASC
```

## Evolution annuelle du taux de candidatures acceptées et refusées à partir de 2021

- **ID:** 7038
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures refusées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
GROUP BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## Evolution des prescriptions des PH

- **ID:** 7042
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", "public"."candidatures_echelle_locale"."type_complet" AS "type_complet", count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."date_candidature" < date '2025-01-01') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND (("public"."candidatures_echelle_locale"."type_prescripteur" = 'Autre') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Département') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Nouveaux prescripteurs') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE')) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
GROUP BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date), "public"."candidatures_echelle_locale"."type_complet" 
ORDER BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC, "public"."candidatures_echelle_locale"."type_complet" ASC
```

## Nombre de candidatures en attente d'être clôturée sur 2024

- **ID:** 7044
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."état" = 'Candidature à l''étude') 
OR ("public"."candidatures_echelle_locale"."état" = 'Candidature en attente') 
OR ("public"."candidatures_echelle_locale"."état" = 'Nouvelle candidature')) 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2024-01-01' 
AND date '2024-12-31' 
AND ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Evolution annuelle des candidatures orientées par type de SIAE

- **ID:** 7046
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND (("public"."candidatures_echelle_locale"."type_prescripteur" = 'Autre') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Département') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Nouveaux prescripteurs') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE')) 
GROUP BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date), "public"."candidatures_echelle_locale"."type_structure" 
ORDER BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC, "public"."candidatures_echelle_locale"."type_structure" ASC
```

## Nombre de candidatures en cours de traitement en 2023

- **ID:** 7049
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."état" = 'Candidature à l''étude') 
OR ("public"."candidatures_echelle_locale"."état" = 'Candidature en attente') 
OR ("public"."candidatures_echelle_locale"."état" = 'Nouvelle candidature')) 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-1 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Taux de candidatures acceptées par les SIAE en 2023

- **ID:** 7050
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-1 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Nombre de candidatures acceptées en 2024

- **ID:** 7051
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2024-01-01' 
AND date '2024-12-31' 
AND ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Taux de candidatures refusées par les SIAE en 2024

- **ID:** 7052
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures refusées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2024-01-01' 
AND date '2024-12-31' 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Taux de candidatures refusées par les SIAE en 2023

- **ID:** 7056
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures refusées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-1 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Motifs de refus sur 2024

- **ID:** 7070
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."motif_de_refus" AS "motif_de_refus", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND ("public"."candidatures_echelle_locale"."état" = 'Candidature refusée') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2024-01-01' 
AND date '2024-12-31' 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
GROUP BY "public"."candidatures_echelle_locale"."motif_de_refus" 
ORDER BY "count" DESC, "public"."candidatures_echelle_locale"."motif_de_refus" ASC
```

## Candidatures toujours en cours de traitement

- **ID:** 7072
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", "public"."candidatures_echelle_locale"."origine" AS "origine", count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."état" = 'Candidature à l''étude') 
OR ("public"."candidatures_echelle_locale"."état" = 'Candidature en attente') 
OR ("public"."candidatures_echelle_locale"."état" = 'Nouvelle candidature')) 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
GROUP BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date), "public"."candidatures_echelle_locale"."origine" 
ORDER BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC, "public"."candidatures_echelle_locale"."origine" ASC
```

## Candidats inscrits sur les emplois

- **ID:** 7074
- **Tables:** candidats, public

```sql
SELECT "public"."candidats"."département" AS "département", COUNT(*) AS "count" 
FROM "public"."candidats" 
GROUP BY "public"."candidats"."département" 
ORDER BY "public"."candidats"."département" ASC
```

## [116] Etat des candidatures par domaine professionnel sur les 12 derniers mois - échelle locale

- **ID:** 7090
- **Dashboard:** 116
- **Tables:** fiches_de_poste_par_candidature, public, candidatures_echelle_locale, fiches_de_poste, code_rome_domaine_professionnel

```sql
SELECT "source"."Métier" AS "Métier", count(distinct "source"."id") AS "Nombre de candidatures", CAST(SUM(CASE WHEN "source"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures acceptées", CAST(SUM(CASE WHEN "source"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures refusées" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."état" AS "état", "public"."candidatures_echelle_locale"."reprise_de_stock_ai" AS "reprise_de_stock_ai", "Code Rome Domaine Professionnel"."domaine_professionnel" AS "Métier", "Fiches De Poste Par Candidature"."id_fiche_de_poste" AS "Fiches De Poste Par Candidature__id_fiche_de_poste", "Fiches De Poste Par Candidature"."id_candidature" AS "Fiches De Poste Par Candidature__id_candidature", "Fiches De Poste Par Candidature"."date_mise_à_jour_metabase" AS "Fiches De Poste Par Candidature__date_mise_à_jour_metabase", "Fiches De Poste"."id" AS "Fiches De Poste__id", "Fiches De Poste"."code_rome" AS "Fiches De Poste__code_rome", "Fiches De Poste"."nom_rome" AS "Fiches De Poste__nom_rome", "Fiches De Poste"."recrutement_ouvert" AS "Fiches De Poste__recrutement_ouvert", "Fiches De Poste"."type_contrat" AS "Fiches De Poste__type_contrat", "Fiches De Poste"."id_employeur" AS "Fiches De Poste__id_employeur", "Fiches De Poste"."type_employeur" AS "Fiches De Poste__type_employeur", "Fiches De Poste"."siret_employeur" AS "Fiches De Poste__siret_employeur", "Fiches De Poste"."nom_employeur" AS "Fiches De Poste__nom_employeur", "Fiches De Poste"."mises_a_jour_champs" AS "Fiches De Poste__mises_a_jour_champs", "Fiches De Poste"."département_employeur" AS "Fiches De Poste__département_employeur", "Fiches De Poste"."nom_département_employeur" AS "Fiches De Poste__nom_département_employeur", "Fiches De Poste"."région_employeur" AS "Fiches De Poste__région_employeur", "Fiches De Poste"."total_candidatures" AS "Fiches De Poste__total_candidatures", "Fiches De Poste"."date_création" AS "Fiches De Poste__date_création", "Fiches De Poste"."date_dernière_modification" AS "Fiches De Poste__date_dernière_modification", "Fiches De Poste"."date_mise_à_jour_metabase" AS "Fiches De Poste__date_mise_à_jour_metabase", "Code Rome Domaine Professionnel"."grand_domaine" AS "Code Rome Domaine Professionnel__grand_domaine", "Code Rome Domaine Professionnel"."domaine_professionnel" AS "Code Rome Domaine Professionnel__domaine_professionnel", "Code Rome Domaine Professionnel"."code_rome" AS "Code Rome Domaine Professionnel__code_rome", "Code Rome Domaine Professionnel"."description_code_rome" AS "Code Rome Domaine Professionnel__description_code_rome", "Code Rome Domaine Professionnel"."date_mise_à_jour_metabase" AS "Code Rome Domaine Professionnel__date_mise_à_jour_metabase" 
FROM "public"."candidatures_echelle_locale" LEFT 
-- ... (truncated)
```

## [116] Evolution des candidatures sur les 12 derniers mois, par état - échelle locale

- **ID:** 7091
- **Dashboard:** 116
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."état" AS "état", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non' 
GROUP BY "public"."candidatures_echelle_locale"."état", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."état" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## Evolution candidatures annuelles SIAE

- **ID:** 7092
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."état" AS "état", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."date_candidature" > date '2021-01-01' 
GROUP BY "public"."candidatures_echelle_locale"."état", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."état" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## [116]Etat des candidatures par métier sur les 3 derniers mois

- **ID:** 7093
- **Dashboard:** 116
- **Tables:** fiches_de_poste_par_candidature, public, fiches_de_poste, candidatures_echelle_locale, structures

```sql
SELECT "source"."Métier" AS "Métier", COUNT(*) AS "count", CAST(SUM(CASE WHEN "source"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures acceptées", CAST(SUM(CASE WHEN "source"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures refusées" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."état" AS "état", "public"."candidatures_echelle_locale"."reprise_de_stock_ai" AS "reprise_de_stock_ai", CONCAT("Fiches De Poste"."code_rome", ' - ', "Fiches De Poste"."nom_rome") AS "Métier", "Fiches De Poste Par Candidature"."id_fiche_de_poste" AS "Fiches De Poste Par Candidature__id_fiche_de_poste", "Fiches De Poste Par Candidature"."id_candidature" AS "Fiches De Poste Par Candidature__id_candidature", "Fiches De Poste Par Candidature"."date_mise_à_jour_metabase" AS "Fiches De Poste Par Candidature__date_mise_à_jour_metabase", "Fiches De Poste"."id" AS "Fiches De Poste__id", "Fiches De Poste"."code_rome" AS "Fiches De Poste__code_rome", "Fiches De Poste"."nom_rome" AS "Fiches De Poste__nom_rome", "Fiches De Poste"."recrutement_ouvert" AS "Fiches De Poste__recrutement_ouvert", "Fiches De Poste"."type_contrat" AS "Fiches De Poste__type_contrat", "Fiches De Poste"."id_employeur" AS "Fiches De Poste__id_employeur", "Fiches De Poste"."type_employeur" AS "Fiches De Poste__type_employeur", "Fiches De Poste"."siret_employeur" AS "Fiches De Poste__siret_employeur", "Fiches De Poste"."nom_employeur" AS "Fiches De Poste__nom_employeur", "Fiches De Poste"."mises_a_jour_champs" AS "Fiches De Poste__mises_a_jour_champs", "Fiches De Poste"."département_employeur" AS "Fiches De Poste__département_employeur", "Fiches De Poste"."nom_département_employeur" AS "Fiches De Poste__nom_département_employeur", "Fiches De Poste"."région_employeur" AS "Fiches De Poste__région_employeur", "Fiches De Poste"."total_candidatures" AS "Fiches De Poste__total_candidatures", "Fiches De Poste"."date_création" AS "Fiches De Poste__date_création", "Fiches De Poste"."date_dernière_modification" AS "Fiches De Poste__date_dernière_modification", "Fiches De Poste"."date_mise_à_jour_metabase" AS "Fiches De Poste__date_mise_à_jour_metabase", "Structures"."id" AS "Structures__id", "Structures"."id_asp" AS "Structures__id_asp", "Structures"."nom" AS "Structures__nom", "Structures"."nom_complet" AS "Structures__nom_complet", "Structures"."description" AS "Structures__description", "Structures"."type" AS "Structures__type", "Structures"."siret" AS "Structures__siret", "Structures"."code_naf" AS "Structures__code_naf", "Structures"."email_public" AS "Structures__email_public", "Structures"."email_authentification" AS "Structures__email_authentification", "Structures"."convergence_france" AS "Stru
-- ... (truncated)
```

## [116] Taux candidatures déclinées

- **ID:** 7094
- **Dashboard:** 116
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures déclinées" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non'
```

## [116] Taux candidatures acceptées

- **ID:** 7095
- **Dashboard:** 116
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non'
```

## [116] Evolution des candidatures acceptées sur les 12 derniers mois, par type d'employeur - échelle locale

- **ID:** 7096
- **Dashboard:** 116
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) AS "date_embauche", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
GROUP BY "public"."candidatures_echelle_locale"."type_structure", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) 
ORDER BY "count" DESC, "public"."candidatures_echelle_locale"."type_structure" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) ASC
```

## [116] Evolution des candidatures, par type d'orienteur - échelle locale

- **ID:** 7097
- **Dashboard:** 116
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine" AS "origine", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) AS "date_embauche", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
GROUP BY "public"."candidatures_echelle_locale"."origine", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."origine" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) ASC
```

## [185] Repartition des motifs de refus

- **ID:** 7098
- **Dashboard:** 185
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."motif_de_refus" AS "motif_de_refus", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature refusée') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."motif_de_refus" IS NOT NULL) 
AND (("public"."candidatures_echelle_locale"."motif_de_refus" <> '') 
OR ("public"."candidatures_echelle_locale"."motif_de_refus" IS NULL)) 
GROUP BY "public"."candidatures_echelle_locale"."motif_de_refus" 
ORDER BY "count" DESC, "public"."candidatures_echelle_locale"."motif_de_refus" ASC
```

## [116] Taux de refus des structures

- **ID:** 7099
- **Dashboard:** 116
- **Tables:** public, tx_refus_siae

```sql
SELECT "public"."tx_refus_siae"."type_structure" AS "type_structure", CAST(SUM("public"."tx_refus_siae"."nombre_candidatures_refusees") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."tx_refus_siae"."nombre_candidatures") AS DOUBLE PRECISION), 0.0) AS "Taux de refus", SUM("public"."tx_refus_siae"."nombre_candidatures") AS "Nombre de candidatures", SUM("public"."tx_refus_siae"."nombre_fiches_poste_ouvertes") AS "Nombre de postes ouverts", SUM("public"."tx_refus_siae"."nombre_siae") AS "Nombre de SIAE", SUM("public"."tx_refus_siae"."nombre_candidatures") - SUM("public"."tx_refus_siae"."nombre_candidatures_employeurs") AS "Nombre de candidatures hors auto-prescription", CAST(SUM("public"."tx_refus_siae"."nb_candidatures_refusees_non_emises_par_employeur_siae") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."tx_refus_siae"."nombre_candidatures") - SUM("public"."tx_refus_siae"."nombre_candidatures_employeurs") AS DOUBLE PRECISION), 0.0) AS "Taux de refus hors auto-prescription" 
FROM "public"."tx_refus_siae" 
GROUP BY "public"."tx_refus_siae"."type_structure" 
ORDER BY "public"."tx_refus_siae"."type_structure" ASC
```

## [116]Motifs de refus des candidatures par type de prescripteurs - échelle locale

- **ID:** 7100
- **Dashboard:** 116
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine_détaillée" AS "origine_détaillée", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures acceptées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures refusées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Embauche incompatible avec les objectifs du dialogue de gestion' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Embauche incompatible avec les objectifs du dialogu_bc7feb62", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Candidat non joignable' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Candidat non joignable", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Pas de recrutement en cours' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Pas de recrutement en cours", SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS "Nombre de candidatures refusées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Candidat indisponible (en formation)' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Candidat indisponible (en formation)", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Candidat indisponible (en emploi)' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Candidat indisponible (en emploi)", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Autre motif saisi sur les emplois de l''inclusion' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Autre motif saisi sur les emplois de l'inclusion", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Candidature en doublon' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidatur
-- ... (truncated)
```

## [116] Nombre total de candidatures

- **ID:** 7101
- **Dashboard:** 116
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non'
```

## [116] Evolution des candidatures sur les 12 derniers mois, par origine - échelle locale

- **ID:** 7102
- **Dashboard:** 116
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine" AS "origine", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."injection_ai" = 0) 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
GROUP BY "public"."candidatures_echelle_locale"."origine", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."origine" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## [116] Pourcentage de candidatures acceptées par type de prescripteur v2

- **ID:** 7103
- **Dashboard:** 116
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine_détaillée" AS "origine_détaillée", COUNT(*) AS "count", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures acceptées" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non' 
GROUP BY "public"."candidatures_echelle_locale"."origine_détaillée" 
ORDER BY "count" DESC, "public"."candidatures_echelle_locale"."origine_détaillée" ASC
```

## [116] Motifs de refus actualisés (mensuel)

- **ID:** 7104
- **Dashboard:** 116
- **Tables:** structures, public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."motif_de_refus" AS "motif_de_refus", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" LEFT 
JOIN "public"."structures" AS "Structures" ON "public"."candidatures_echelle_locale"."id_structure" = "Structures"."id" 
WHERE (("public"."candidatures_echelle_locale"."origine" = 'Orienteur') 
OR ("public"."candidatures_echelle_locale"."origine" = 'Prescripteur habilité')) 
AND ("public"."candidatures_echelle_locale"."état" = 'Candidature refusée') 
AND ("public"."candidatures_echelle_locale"."motif_de_refus" IS NOT NULL) 
AND (("public"."candidatures_echelle_locale"."motif_de_refus" <> '') 
OR ("public"."candidatures_echelle_locale"."motif_de_refus" IS NULL)) 
AND ("public"."candidatures_echelle_locale"."injection_ai" = 0) 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
GROUP BY "public"."candidatures_echelle_locale"."motif_de_refus", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "count" DESC, "public"."candidatures_echelle_locale"."motif_de_refus" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## [116]Profil des candidats embauchés

- **ID:** 7105
- **Dashboard:** 116
- **Tables:** candidats, public

```sql
SELECT CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) AS "date_diagnostic", "source"."pivot-grouping" AS "pivot-grouping", CAST(SUM(CASE WHEN "source"."critère_n1_bénéficiaire_du_rsa" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression", CAST(SUM(CASE WHEN "source"."critère_n1_detld_plus_de_24_mois" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression_2", CAST(SUM(CASE WHEN "source"."critère_n2_deld_12_à_24_mois" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression_3", CAST(SUM(CASE WHEN "source"."critère_n2_jeune_moins_de_26_ans" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression_4", CAST(SUM(CASE WHEN "source"."critère_n2_résident_qpv" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression_5" 
FROM (SELECT "public"."candidats"."total_embauches" AS "total_embauches", "public"."candidats"."date_diagnostic" AS "date_diagnostic", "public"."candidats"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidats"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidats"."critère_n1_detld_plus_de_24_mois" AS "critère_n1_detld_plus_de_24_mois", "public"."candidats"."critère_n2_jeune_moins_de_26_ans" AS "critère_n2_jeune_moins_de_26_ans", "public"."candidats"."critère_n2_deld_12_à_24_mois" AS "critère_n2_deld_12_à_24_mois", "public"."candidats"."critère_n2_résident_qpv" AS "critère_n2_résident_qpv", ABS(0) AS "pivot-grouping" 
FROM "public"."candidats" 
WHERE (("public"."candidats"."total_embauches" <> 0) 
OR ("public"."candidats"."total_embauches" IS NULL)) 
AND (("public"."candidats"."type_structure_dernière_embauche" = 'ACI') 
OR ("public"."candidats"."type_structure_dernière_embauche" = 'AI') 
OR ("public"."candidats"."type_structure_dernière_embauche" = 'EI') 
OR ("public"."candidats"."type_structure_dernière_embauche" = 'EITI') 
OR ("public"."candidats"."type_structure_dernière_embauche" = 'ETTI'))) AS "source" 
GROUP BY CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date), "source"."pivot-grouping" 
ORDER BY CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) ASC, "source"."pivot-grouping" ASC
```

## [116] Evolution annuelle des candidatures, par origine

- **ID:** 7106
- **Dashboard:** 116
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine" AS "origine", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."date_candidature" > date '2021-01-01') 
AND ("public"."candidatures_echelle_locale"."injection_ai" = 0) 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
GROUP BY "public"."candidatures_echelle_locale"."origine", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."origine" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## [116] Nombre total de candidatures en cours

- **ID:** 7107
- **Dashboard:** 116
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."état" = 'Candidature à l''étude') 
OR ("public"."candidatures_echelle_locale"."état" = 'Candidature en attente') 
OR ("public"."candidatures_echelle_locale"."état" = 'Nouvelle candidature')) 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non')
```

## Evolution du nombre de candidatures acceptées les 6 derniers mois

- **ID:** 7291
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) AS "date_embauche", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND ("public"."candidatures_echelle_locale"."date_embauche" >= DATE_TRUNC('month', (NOW() + INTERVAL '-6 month'))) 
AND ("public"."candidatures_echelle_locale"."date_embauche" < DATE_TRUNC('month', NOW())) 
GROUP BY CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) 
ORDER BY CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) ASC
```

## [408] Évolution de l'état des candidatures

- **ID:** 7298
- **Dashboard:** 408
- **Tables:** public, candidatures_candidats_recherche_active, candidats_recherche_active

```sql
SELECT "source"."état" AS "état", DATE_TRUNC('month', CAST("source"."date_candidature" AS timestamp)) AS "date_candidature", COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "
-- ... (truncated)
```

## [408] Candidatures en cours vs clôturée

- **ID:** 7299
- **Dashboard:** 408
- **Tables:** public, candidatures_candidats_recherche_active, candidats_recherche_active

```sql
SELECT "source"."refus_vs_encours" AS "refus_vs_encours", COUNT(*) AS "count" 
FROM (SELECT "source"."état" AS "état", CASE WHEN "source"."état" = 'Candidature refusée' THEN 'Clôturée' WHEN "source"."état" = 'Embauché ailleurs' THEN 'Clôturée' WHEN "source"."état" = 'Embauche annulée' THEN 'Clôturée' ELSE 'En cours' END AS "refus_vs_encours" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candida
-- ... (truncated)
```

## [408] Motifs de refus

- **ID:** 7303
- **Dashboard:** 408
- **Tables:** public, candidatures_candidats_recherche_active, candidats_recherche_active

```sql
SELECT "source"."MR" AS "MR", COUNT(*) AS "count" 
FROM (SELECT "source"."état" AS "état", "source"."motif_de_refus" AS "motif_de_refus", "source"."categorie_structure" AS "categorie_structure", CASE WHEN "source"."motif_de_refus" = 'Autre' THEN 'Motif autre saisi sur les Emplois de l''Inclusion' ELSE "source"."motif_de_refus" END AS "MR" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_
-- ... (truncated)
```

## [216] répartition des candidatures par origine candidat - tous

- **ID:** 7309
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."origine" AS "origine", COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "active", "public"."candidatures_echelle_locale"
-- ... (truncated)
```

## [216] orientation SIAE - tous

- **ID:** 7311
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."type_structure" AS "type_structure", COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "active", "public"."candidatures_e
-- ... (truncated)
```

## [216] nb de candidatures acceptées

- **ID:** 7312
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "active", "public"."candidatures_echelle_locale"."brsa" AS "brsa", "public"."cand
-- ... (truncated)
```

## [216] taux acceptation des candidatures (global)

- **ID:** 7313
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "source"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date
-- ... (truncated)
```

## [216] Taux acceptation femmes

- **ID:** 7321
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN ("source"."genre_candidat" = 'Femme') 
AND ("source"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation femme" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echell
-- ... (truncated)
```

## [216] Nombre de candidats acceptés

- **ID:** 7329
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT count(distinct "source"."id_candidat") AS "Nb candidats acceptés" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "active", "public"."candidatures_ec
-- ... (truncated)
```

## [216] Nombre de candidats

- **ID:** 7331
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT count(distinct "source"."id_candidat") AS "Nb candidats acceptés" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "active", "public"."candidatures_ec
-- ... (truncated)
```

## [216] nb candidatures

- **ID:** 7333
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "active", "public"."candidatures_echelle_locale"."brsa" AS "brsa", "public"."cand
-- ... (truncated)
```

## [216] Taux acceptation hommes

- **ID:** 7337
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN ("source"."genre_candidat" = 'Homme') 
AND ("source"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation homme" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echell
-- ... (truncated)
```
