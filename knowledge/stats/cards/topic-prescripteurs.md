# Thème : prescripteurs

*Prescripteur and orientation data*

**8 cartes**

## [136] nouveaux candidats orientés par les prescripteurs habilités sur les 3 derniers - prescripteurs

- **ID:** 1209
- **Dashboard:** 136
- **Tables:** taux_transformation_prescripteurs

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."taux_transformation_prescripteurs"
```

## [136] Répartition des nouveaux candidats orientés par les prescripteurs habilités par mois V2 - prescripteurs

- **ID:** 1213
- **Dashboard:** 136
- **Tables:** taux_transformation_prescripteurs

```sql
SELECT DATE_TRUNC('month', CAST("source"."date_diagnostic" AS timestamp)) AS "date_diagnostic", "source"."État du candidat" AS "État du candidat", count(distinct "source"."id_candidat") AS "Nombre de Nouveaux candidats orientés chaque mois (entrée)" 
FROM (SELECT "public"."taux_transformation_prescripteurs"."id_candidat" AS "id_candidat", "public"."taux_transformation_prescripteurs"."date_diagnostic" AS "date_diagnostic", CASE WHEN "public"."taux_transformation_prescripteurs"."total_embauches" > 0 THEN 'candidats acceptés' ELSE 'candidats non acceptés' END AS "État du candidat" 
FROM "public"."taux_transformation_prescripteurs" 
WHERE ("public"."taux_transformation_prescripteurs"."date_diagnostic" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" < DATE_TRUNC('year', (NOW() + INTERVAL '1 year'))) 
AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" > date '2021-01-01')) AS "source" 
GROUP BY DATE_TRUNC('month', CAST("source"."date_diagnostic" AS timestamp)), "source"."État du candidat" 
ORDER BY DATE_TRUNC('month', CAST("source"."date_diagnostic" AS timestamp)) ASC, "source"."État du candidat" ASC
```

## [136] Taux de candidats acceptés orientés par les prescripteurs habilités sur les 30 derniers jours - prescripteurs

- **ID:** 1214
- **Dashboard:** 136
- **Tables:** taux_transformation_prescripteurs

```sql
SELECT "source"."departement_candidat" AS "departement_candidat", CAST(SUM(CASE WHEN "source"."Candidat accepté" = 'candidats acceptés' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux de candidats acceptés" 
FROM (SELECT CASE WHEN "public"."taux_transformation_prescripteurs"."total_embauches" > 0 THEN 'candidats acceptés' ELSE 'candidats non acceptés' END AS "Candidat accepté", "public"."taux_transformation_prescripteurs"."departement_candidat" AS "departement_candidat" 
FROM "public"."taux_transformation_prescripteurs") AS "source" 
GROUP BY "source"."departement_candidat" 
ORDER BY "source"."departement_candidat" ASC
```

## [136] Répartition des nouveaux candidats orientés par les prescripteurs habilités par mois V1 - diagnostic non valide"

- **ID:** 1441
- **Dashboard:** 136
- **Tables:** taux_transformation_prescripteurs

```sql
SELECT DATE_TRUNC('month', CAST("source"."date_diagnostic" AS timestamp)) AS "date_diagnostic", count(distinct "source"."id_candidat") AS "Nombre de nouveaux candidats orientés", CAST(SUM(CASE WHEN "source"."Candidat accepté" = 'candidat accepté' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux de candidats acceptés" 
FROM (SELECT "public"."taux_transformation_prescripteurs"."id_candidat" AS "id_candidat", CASE WHEN "public"."taux_transformation_prescripteurs"."total_embauches" > 0 THEN 'candidat accepté' ELSE 'candidat non accepté' END AS "Candidat accepté", "public"."taux_transformation_prescripteurs"."date_diagnostic" AS "date_diagnostic" 
FROM "public"."taux_transformation_prescripteurs" 
WHERE ("public"."taux_transformation_prescripteurs"."date_diagnostic" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" < DATE_TRUNC('year', (NOW() + INTERVAL '1 year'))) 
AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" > date '2021-01-01') 
AND ("public"."taux_transformation_prescripteurs"."diagnostic_valide" = 'non')) AS "source" 
GROUP BY DATE_TRUNC('month', CAST("source"."date_diagnostic" AS timestamp)) 
ORDER BY DATE_TRUNC('month', CAST("source"."date_diagnostic" AS timestamp)) ASC
```

## [136] Répartition des nouveaux candidats orientés par les prescripteurs habilités par mois V1 - diagnostic valide

- **ID:** 1442
- **Dashboard:** 136
- **Tables:** taux_transformation_prescripteurs

```sql
SELECT DATE_TRUNC('month', CAST("source"."date_diagnostic" AS timestamp)) AS "date_diagnostic", count(distinct "source"."id_candidat") AS "Nombre de nouveaux candidats orientés", CAST(SUM(CASE WHEN "source"."Candidat accepté" = 'candidat accepté' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux de candidats acceptés" 
FROM (SELECT "public"."taux_transformation_prescripteurs"."id_candidat" AS "id_candidat", CASE WHEN "public"."taux_transformation_prescripteurs"."total_embauches" > 0 THEN 'candidat accepté' ELSE 'candidat non accepté' END AS "Candidat accepté", "public"."taux_transformation_prescripteurs"."date_diagnostic" AS "date_diagnostic" 
FROM "public"."taux_transformation_prescripteurs" 
WHERE ("public"."taux_transformation_prescripteurs"."date_diagnostic" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" < DATE_TRUNC('year', (NOW() + INTERVAL '1 year'))) 
AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" > date '2021-01-01') 
AND ("public"."taux_transformation_prescripteurs"."diagnostic_valide" = 'Oui')) AS "source" 
GROUP BY DATE_TRUNC('month', CAST("source"."date_diagnostic" AS timestamp)) 
ORDER BY DATE_TRUNC('month', CAST("source"."date_diagnostic" AS timestamp)) ASC
```

## [136] % candidats orientés et acceptés

- **ID:** 1471
- **Dashboard:** 136
- **Tables:** taux_transformation_prescripteurs

```sql
SELECT CAST(SUM(CASE WHEN ("public"."taux_transformation_prescripteurs"."total_embauches" <> 0) 
OR ("public"."taux_transformation_prescripteurs"."total_embauches" IS NULL) THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidats acceptés en IAE" 
FROM "public"."taux_transformation_prescripteurs" 
WHERE "public"."taux_transformation_prescripteurs"."date_diagnostic" IS NOT NULL
```

## Nombre de candidats accompagnés par les prescripteurs habilités

- **ID:** 3635
- **Dashboard:** 337
- **Tables:** taux_transformation_prescripteurs

```sql
SELECT "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" AS "type_auteur_diagnostic_detaille", CAST(DATE_TRUNC('year', "public"."taux_transformation_prescripteurs"."date_diagnostic") AS date) AS "date_diagnostic", COUNT(*) AS "count" 
FROM "public"."taux_transformation_prescripteurs" 
WHERE ("public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" IS NOT NULL) 
AND (("public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" <> '') 
OR ("public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" IS NULL)) 
AND (("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'ACI') 
OR ("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'AI') 
OR ("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'EI') 
OR ("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'EITI') 
OR ("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'ETTI')) 
AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" < date '2025-01-01') 
GROUP BY "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille", CAST(DATE_TRUNC('year', "public"."taux_transformation_prescripteurs"."date_diagnostic") AS date) 
ORDER BY CAST(DATE_TRUNC('year', "public"."taux_transformation_prescripteurs"."date_diagnostic") AS date) ASC, "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" ASC
```

## [136] Répartition du nombre de candidats par type de prescripteur

- **ID:** 4834
- **Dashboard:** 136
- **Tables:** taux_transformation_prescripteurs

```sql
SELECT "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" AS "type_auteur_diagnostic_detaille", COUNT(*) AS "count" 
FROM "public"."taux_transformation_prescripteurs" 
GROUP BY "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" 
ORDER BY "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" ASC
```
