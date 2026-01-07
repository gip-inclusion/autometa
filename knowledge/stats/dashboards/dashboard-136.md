# Dashboard : Candidatures - L'accompagnement des prescripteurs habilités

### ⚠️  Aide à la lecture des données
#### Analyse des données basées sur la date et l'auteur du diagnostic d'éligibilité
##### Voici un aperçu de certains termes clés utilisés dans ce tableau de bord :
- Un **Prescripteur Habilité** est un professionnel qui soumet la candidature d'un candidat à un employeur. Il est également habilits à valider l'éligibilité d'un candidat à l'insertion par l'activité économique.
- **Candidature** fait référence à l'acte de postuler à un emploi en envoyant un profil ou un CV à un employeur. Le **candidat** est la personne qui postule à l'emploi. Un candidat peut avoir plusieurs candidatures.
- **Ici**, les données ont été analysées pour les candidats qui ont eu un diagnostic d'éligibilité réalisé par les Prescripteurs Habilités.
- Un **candidat accepté** est un candidat qui a été déclaré embauché par une SIAE.

### ✅ Comment ce tableau de bord vous accompagne dans vos missions ?
En tant que prescripteur habilité, vous pouvez utiliser ce tableau pour sui

**8 cartes**

## [136] nouveaux candidats orientés par les prescripteurs habilités sur les 3 derniers - prescripteurs

- **ID:** 7082
- **Thème:** prescripteurs
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."taux_transformation_prescripteurs"
```

## [136] Taux de candidats acceptés orientés par les prescripteurs habilités sur les 30 derniers jours - prescripteurs

- **ID:** 7083
- **Thème:** prescripteurs
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT "source"."departement_candidat" AS "departement_candidat", CAST(SUM(CASE WHEN "source"."Candidat accepté" = 'candidats acceptés' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux de candidats acceptés" 
FROM (SELECT "public"."taux_transformation_prescripteurs"."departement_candidat" AS "departement_candidat", "public"."taux_transformation_prescripteurs"."total_embauches" AS "total_embauches", CASE WHEN "public"."taux_transformation_prescripteurs"."total_embauches" > 0 THEN 'candidats acceptés' ELSE 'candidats non acceptés' END AS "Candidat accepté" 
FROM "public"."taux_transformation_prescripteurs") AS "source" 
GROUP BY "source"."departement_candidat" 
ORDER BY "source"."departement_candidat" ASC
```

## [136] candidats orientés par les prescripteurs habilités acceptés en IAE sur les 3 derniers mois - prescripteurs

- **ID:** 7084
- **Thème:** prescripteurs
- **Tables:** candidatures, public, taux_transformation_prescripteurs

```sql
SELECT count(distinct "public"."taux_transformation_prescripteurs"."id_candidat") AS "count" 
FROM "public"."taux_transformation_prescripteurs" LEFT 
JOIN "public"."candidatures" AS "Candidatures" ON "public"."taux_transformation_prescripteurs"."id_candidat" = "Candidatures"."id_candidat" 
WHERE ("public"."taux_transformation_prescripteurs"."date_diagnostic" IS NOT NULL) 
AND ("Candidatures"."date_embauche" IS NOT NULL)
```

## [136] Répartition des nouveaux candidats orientés par les prescripteurs habilités par mois V2 - prescripteurs

- **ID:** 7085
- **Thème:** prescripteurs
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) AS "date_diagnostic", "source"."État du candidat" AS "État du candidat", count(distinct "source"."id_candidat") AS "Nombre de Nouveaux candidats orientés chaque mois (entrée)" 
FROM (SELECT "public"."taux_transformation_prescripteurs"."id_candidat" AS "id_candidat", "public"."taux_transformation_prescripteurs"."date_diagnostic" AS "date_diagnostic", "public"."taux_transformation_prescripteurs"."total_embauches" AS "total_embauches", CASE WHEN "public"."taux_transformation_prescripteurs"."total_embauches" > 0 THEN 'candidats acceptés' ELSE 'candidats non acceptés' END AS "État du candidat" 
FROM "public"."taux_transformation_prescripteurs" 
WHERE ("public"."taux_transformation_prescripteurs"."date_diagnostic" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" < DATE_TRUNC('year', (NOW() + INTERVAL '1 year'))) 
AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" > date '2021-01-01')) AS "source" 
GROUP BY CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date), "source"."État du candidat" 
ORDER BY CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) ASC, "source"."État du candidat" ASC
```

## [136] % candidats orientés et acceptés

- **ID:** 7086
- **Thème:** prescripteurs
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT CAST(SUM(CASE WHEN ("public"."taux_transformation_prescripteurs"."total_embauches" <> 0) 
OR ("public"."taux_transformation_prescripteurs"."total_embauches" IS NULL) THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidats acceptés en IAE" 
FROM "public"."taux_transformation_prescripteurs" 
WHERE "public"."taux_transformation_prescripteurs"."date_diagnostic" IS NOT NULL
```

## [136] Répartition des nouveaux candidats orientés par les prescripteurs habilités par mois V1 - diagnostic valide

- **ID:** 7087
- **Thème:** prescripteurs
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) AS "date_diagnostic", count(distinct "source"."id_candidat") AS "Nombre de nouveaux candidats orientés", CAST(SUM(CASE WHEN "source"."Candidat accepté" = 'candidat accepté' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux de candidats acceptés" 
FROM (SELECT "public"."taux_transformation_prescripteurs"."id_candidat" AS "id_candidat", "public"."taux_transformation_prescripteurs"."date_diagnostic" AS "date_diagnostic", "public"."taux_transformation_prescripteurs"."total_embauches" AS "total_embauches", "public"."taux_transformation_prescripteurs"."diagnostic_valide" AS "diagnostic_valide", CASE WHEN "public"."taux_transformation_prescripteurs"."total_embauches" > 0 THEN 'candidat accepté' ELSE 'candidat non accepté' END AS "Candidat accepté" 
FROM "public"."taux_transformation_prescripteurs" 
WHERE ("public"."taux_transformation_prescripteurs"."date_diagnostic" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" < DATE_TRUNC('year', (NOW() + INTERVAL '1 year'))) 
AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" > date '2021-01-01') 
AND ("public"."taux_transformation_prescripteurs"."diagnostic_valide" = 'Oui')) AS "source" 
GROUP BY CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) 
ORDER BY CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) ASC
```

## [136] Répartition des nouveaux candidats orientés par les prescripteurs habilités par mois V1 - diagnostic non valide"

- **ID:** 7088
- **Thème:** prescripteurs
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) AS "date_diagnostic", count(distinct "source"."id_candidat") AS "Nombre de nouveaux candidats orientés", CAST(SUM(CASE WHEN "source"."Candidat accepté" = 'candidat accepté' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux de candidats acceptés" 
FROM (SELECT "public"."taux_transformation_prescripteurs"."id_candidat" AS "id_candidat", "public"."taux_transformation_prescripteurs"."date_diagnostic" AS "date_diagnostic", "public"."taux_transformation_prescripteurs"."total_embauches" AS "total_embauches", "public"."taux_transformation_prescripteurs"."diagnostic_valide" AS "diagnostic_valide", CASE WHEN "public"."taux_transformation_prescripteurs"."total_embauches" > 0 THEN 'candidat accepté' ELSE 'candidat non accepté' END AS "Candidat accepté" 
FROM "public"."taux_transformation_prescripteurs" 
WHERE ("public"."taux_transformation_prescripteurs"."date_diagnostic" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" < DATE_TRUNC('year', (NOW() + INTERVAL '1 year'))) 
AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" > date '2021-01-01') 
AND ("public"."taux_transformation_prescripteurs"."diagnostic_valide" = 'non')) AS "source" 
GROUP BY CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) 
ORDER BY CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) ASC
```

## [136] Répartition du nombre de candidats par type de prescripteur

- **ID:** 7089
- **Thème:** prescripteurs
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" AS "type_auteur_diagnostic_detaille", COUNT(*) AS "count" 
FROM "public"."taux_transformation_prescripteurs" 
GROUP BY "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" 
ORDER BY "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" ASC
```
