# Dashboard : Candidatures - Zoom sur les prescripteurs

**URL:** /tableaux-de-bord/zoom-prescripteurs/

**5 cartes**

## Evolution du nombre de prescripteurs inscrits

- **ID:** 1527
- **Thème:** employeurs
- **Tables:** organisations

```sql
SELECT "source"."date_inscription" AS "date_inscription", SUM(COUNT(*)) OVER (ORDER BY "source"."date_inscription" ASC ROWS UNBOUNDED PRECEDING) AS "count" 
FROM (SELECT CAST(DATE_TRUNC('week', "public"."organisations"."date_inscription") AS date) AS "date_inscription" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL) AS "source" 
GROUP BY "source"."date_inscription" 
ORDER BY "source"."date_inscription" ASC
```

## [52] Tableau des prescripteurs par type détaillé

- **ID:** 2590
- **Thème:** employeurs
- **Tables:** organisations

```sql
SELECT "public"."organisations"."type_complet" AS "type_complet", "public"."organisations"."nom" AS "nom", "public"."organisations"."ville" AS "ville", "public"."organisations"."code_postal" AS "code_postal", "public"."organisations"."adresse_ligne_1" AS "adresse_ligne_1", "public"."organisations"."région" AS "région", "public"."organisations"."nom_département" AS "nom_département", "public"."organisations"."date_inscription" AS "date_inscription", "public"."organisations"."type" AS "type", COUNT(*) AS "count", SUM("public"."organisations"."total_membres") AS "sum" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL 
GROUP BY "public"."organisations"."type_complet", "public"."organisations"."nom", "public"."organisations"."ville", "public"."organisations"."code_postal", "public"."organisations"."adresse_ligne_1", "public"."organisations"."région", "public"."organisations"."nom_département", "public"."organisations"."date_inscription", "public"."organisations"."type" 
ORDER BY "sum" DESC, "public"."organisations"."type_complet" ASC, "public"."organisations"."nom" ASC, "public"."organisations"."ville" ASC, "public"."organisations"."code_postal" ASC, "public"."organisations"."adresse_ligne_1" ASC, "public"."organisations"."région" ASC, "public"."organisations"."nom_département" ASC, "public"."organisations"."date_inscription" ASC, "public"."organisations"."type" ASC
```

## [52] % conseillers SPE

- **ID:** 2601
- **Thème:** employeurs
- **Tables:** organisations

```sql
SELECT CAST(SUM(CASE WHEN "public"."organisations"."type" = 'FT' THEN "public"."organisations"."total_membres" ELSE 0.0 END) + SUM(CASE WHEN "public"."organisations"."type" = 'ML' THEN "public"."organisations"."total_membres" ELSE 0.0 END) + SUM(CASE WHEN "public"."organisations"."type" = 'CAP_EMPLOI' THEN "public"."organisations"."total_membres" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."organisations"."total_membres") AS DOUBLE PRECISION), 0.0) AS "% conseillers SPE" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL
```

## [52] % conseillers hors SPE

- **ID:** 2602
- **Thème:** employeurs
- **Tables:** organisations

```sql
SELECT CAST(SUM(CASE WHEN (("public"."organisations"."type" <> 'FT') 
OR ("public"."organisations"."type" IS NULL)) 
AND (("public"."organisations"."type" <> 'ML') 
OR ("public"."organisations"."type" IS NULL)) 
AND (("public"."organisations"."type" <> 'CAP_EMPLOI') 
OR ("public"."organisations"."type" IS NULL)) THEN "public"."organisations"."total_membres" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."organisations"."total_membres") AS DOUBLE PRECISION), 0.0) AS "% conseillers hors SPE" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL
```

## [52] nombre total de conseillers inscrits

- **ID:** 2603
- **Thème:** employeurs
- **Tables:** organisations

```sql
SELECT SUM("public"."organisations"."total_membres") AS "Nombre total de conseillers inscrits" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL
```
