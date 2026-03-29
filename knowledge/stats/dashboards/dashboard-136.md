# Dashboard : Candidatures - L'accompagnement des prescripteurs habilités

**URL:** /tableaux-de-bord/prescripteurs-habilites/

**8 cartes**

## [136] nouveaux candidats orientés par les prescripteurs habilités sur les 3 derniers - prescripteurs

- **ID:** 1209
- **Thème:** prescripteurs
- **Tables:** taux_transformation_prescripteurs

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."taux_transformation_prescripteurs"
```

## [136] candidats orientés par les prescripteurs habilités acceptés en IAE sur les 3 derniers mois - prescripteurs

- **ID:** 1210
- **Thème:** candidatures
- **Tables:** candidatures, taux_transformation_prescripteurs

```sql
SELECT count(distinct "public"."taux_transformation_prescripteurs"."id_candidat") AS "count" 
FROM "public"."taux_transformation_prescripteurs" LEFT 
JOIN (SELECT "public"."candidatures"."id" AS "id", "public"."candidatures"."candidature_archivee" AS "candidature_archivee", "public"."candidatures"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures"."date_candidature" AS "date_candidature", "public"."candidatures"."date_début_contrat" AS "date_début_contrat", "public"."candidatures"."date_traitement" AS "date_traitement", "public"."candidatures"."état" AS "état", "public"."candidatures"."origine" AS "origine", "public"."candidatures"."origine_détaillée" AS "origine_détaillée", "public"."candidatures"."origine_id_structure" AS "origine_id_structure", "public"."candidatures"."parcours_de_création" AS "parcours_de_création", "public"."candidatures"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures"."motif_de_refus" AS "motif_de_refus", "public"."candidatures"."id_candidat" AS "id_candidat", "public"."candidatures"."id_structure" AS "id_structure", "public"."candidatures"."type_structure" AS "type_structure", "public"."candidatures"."nom_structure" AS "nom_structure", "public"."candidatures"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures"."département_structure" AS "département_structure", "public"."candidatures"."nom_département_structure" AS "nom_département_structure", "public"."candidatures"."région_structure" AS "région_structure", "public"."candidatures"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures"."id_utilisateur_origine_candidature" AS "id_utilisateur_origine_candidature", "public"."candidatures"."date_embauche" AS "date_embauche", "public"."candidatures"."injection_ai" AS "injection_ai", "public"."candidatures"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures"."type_contrat" AS "type_contrat", "public"."candidatures"."présence_de_cv" AS "présence_de_cv", "public"."candidatures"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" 
FROM "public"."candidatures") AS "Candidatures" ON "public"."taux_transformation_prescripteurs"."id_candidat" = "Candidatures"."id_candidat" 
WHERE ("public"."taux_transformation_prescripteurs"."date_diagnostic" IS NOT NULL) 
AND ("Candidatures"."date_embauche" IS NOT NULL)
```

## [136] Répartition des nouveaux candidats orientés par les prescripteurs habilités par mois V2 - prescripteurs

- **ID:** 1213
- **Thème:** prescripteurs
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
- **Thème:** prescripteurs
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
- **Thème:** prescripteurs
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
- **Thème:** prescripteurs
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
- **Thème:** prescripteurs
- **Tables:** taux_transformation_prescripteurs

```sql
SELECT CAST(SUM(CASE WHEN ("public"."taux_transformation_prescripteurs"."total_embauches" <> 0) 
OR ("public"."taux_transformation_prescripteurs"."total_embauches" IS NULL) THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidats acceptés en IAE" 
FROM "public"."taux_transformation_prescripteurs" 
WHERE "public"."taux_transformation_prescripteurs"."date_diagnostic" IS NOT NULL
```

## [136] Répartition du nombre de candidats par type de prescripteur

- **ID:** 4834
- **Thème:** prescripteurs
- **Tables:** taux_transformation_prescripteurs

```sql
SELECT "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" AS "type_auteur_diagnostic_detaille", COUNT(*) AS "count" 
FROM "public"."taux_transformation_prescripteurs" 
GROUP BY "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" 
ORDER BY "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" ASC
```
