# Thème : prescripteurs

*Prescripteur and orientation data*

**23 cartes**

## Part de prescriptions du SPE en 2024

- **ID:** 7033
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de prescriptions du SPE" FROM "public"."candidatures_echelle_locale" WHERE ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2024-01-01' AND date '2024-12-31'
```

## Suivi des orientations par orienteur

- **ID:** 7041
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", "public"."candidatures_echelle_locale"."type_prescripteur" AS "type_prescripteur", count(distinct "public"."candidatures_echelle_locale"."id") AS "count" FROM "public"."candidatures_echelle_locale" WHERE ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) AND (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) AND (("public"."candidatures_echelle_locale"."type_prescripteur" = 'Autre') OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Département') OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Nouveaux prescripteurs') OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE')) AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) AND ("public"."candidatures_echelle_locale"."injection_ai" = 0) AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') OR ("public"."candidatures_echelle_loc
-- ... (truncated)
```

## Part de prescriptions du SPE

- **ID:** 7043
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de prescriptions du SPE" FROM "public"."candidatures_echelle_locale" WHERE ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2023-01-01' AND date '2023-12-31'
```

## Cartographie des prescripteurs

- **ID:** 7045
- **Tables:** public, organisations

```sql
SELECT "public"."organisations"."département" AS "département", COUNT(*) AS "count" FROM "public"."organisations" WHERE ("public"."organisations"."total_membres" <> 0) OR ("public"."organisations"."total_membres" IS NULL) GROUP BY "public"."organisations"."département" ORDER BY "count" DESC, "public"."organisations"."département" ASC
```

## Répartition orienteurs inscrits par type

- **ID:** 7054
- **Tables:** public, organisations

```sql
SELECT "public"."organisations"."type_prescripteur" AS "type_prescripteur", COUNT(*) AS "count" FROM "public"."organisations" WHERE ("public"."organisations"."total_membres" <> 0) OR ("public"."organisations"."total_membres" IS NULL) GROUP BY "public"."organisations"."type_prescripteur" ORDER BY "count" DESC, "public"."organisations"."type_prescripteur" ASC
```

## Nombre de candidats accompagnés par les prescripteurs habilités

- **ID:** 7059
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" AS "type_auteur_diagnostic_detaille", CAST(DATE_TRUNC('year', "public"."taux_transformation_prescripteurs"."date_diagnostic") AS date) AS "date_diagnostic", COUNT(*) AS "count" FROM "public"."taux_transformation_prescripteurs" WHERE ("public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" IS NOT NULL) AND (("public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" <> '') OR ("public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" IS NULL)) AND (("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'ACI') OR ("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'AI') OR ("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'EI') OR ("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'EITI') OR ("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'ETTI')) AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" < date '2025-01-01') GROUP BY "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille", CAST(DATE_TRUNC('year', "public"."taux_transformation_prescripteurs"."date_diagnostic") AS date) ORDER BY CAST(DATE_TRUNC('year', "public"."taux_transformation_prescripteurs"."date_diagnostic") AS date) ASC, "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" ASC
```

## Répartition des orientations vers l'IAE

- **ID:** 7063
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."Origine simple" AS "Origine simple", CAST(DATE_TRUNC('year', "source"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" FROM (SELECT "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."reprise_de_stock_ai" AS "reprise_de_stock_ai", "public"."candidatures_echelle_locale"."origine_détaillée" AS "origine_détaillée", CASE WHEN "public"."candidatures_echelle_locale"."origine_détaillée" = 'Prescripteur habilité PE' THEN 'Pôle emploi' WHEN "public"."candidatures_echelle_locale"."origine_détaillée" = 'Prescripteur habilité ML' THEN 'Mission Locale' WHEN "public"."candidatures_echelle_locale"."origine_détaillée" = 'Prescripteur habilité CAP_EMPLOI' THEN 'Cap Emploi' WHEN "public"."candidatures_echelle_locale"."origine_détaillée" = 'Prescripteur habilité PLIE' THEN 'PLIE - Plan local pour l''insertion et l''emploi' WHEN "public"."candidatures_echelle_locale"."origine_détaillée" = 'Prescripteur habilité DEPT' THEN 'Service social du conseil départemental' WHEN "public"."candidatures_echelle_locale"."origine_détaillée" LIKE 'Employeur%' THEN 'Employeur' WHEN "public"."candidatures_echelle_locale"."origine_détaillée" = 'Candidat' THEN 'Candidat' WHEN "public"."candidatures_echelle_locale"."origine_détaillée" LIKE 'Orienteur%' THEN 'Autres orienteurs' ELSE 'Autres prescripteurs' END AS "Origine simple" FROM "public"."candidatures_echelle_locale" WHERE ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) AND ("public"."candidatures_echelle_locale"."injection_ai" = 0) AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') AND (("public"."candidatures_echelle_lo
-- ... (truncated)
```

## Répartition des conseilleurs inscrits par type de prescripteurs

- **ID:** 7066
- **Tables:** public, organisations

```sql
SELECT "public"."organisations"."type_prescripteur" AS "type_prescripteur", SUM("public"."organisations"."total_membres") AS "Nombre total de conseillers inscrits" FROM "public"."organisations" WHERE "public"."organisations"."date_inscription" IS NOT NULL GROUP BY "public"."organisations"."type_prescripteur" ORDER BY "Nombre total de conseillers inscrits" DESC, "public"."organisations"."type_prescripteur" ASC
```

## Répartition des orientations par type de SIAE

- **ID:** 7071
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" FROM "public"."candidatures_echelle_locale" WHERE ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) AND ("public"."candidatures_echelle_locale"."injection_ai" = 0) AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) GROUP BY "public"."candidatures_echelle_locale"."type_structure", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ORDER BY "public"."candidatures_echelle_locale"."type_structure" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## Carte des orienteurs

- **ID:** 7078
- **Tables:** public, organisations

```sql
SELECT "public"."organisations"."département" AS "département", COUNT(*) AS "count" FROM "public"."organisations" WHERE (("public"."organisations"."total_membres" <> 0) OR ("public"."organisations"."total_membres" IS NULL)) AND ("public"."organisations"."habilitée" = 0) GROUP BY "public"."organisations"."département" ORDER BY "public"."organisations"."département" ASC
```

## [136] nouveaux candidats orientés par les prescripteurs habilités sur les 3 derniers - prescripteurs

- **ID:** 7082
- **Dashboard:** 136
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT COUNT(*) AS "count" FROM "public"."taux_transformation_prescripteurs"
```

## [136] Taux de candidats acceptés orientés par les prescripteurs habilités sur les 30 derniers jours - prescripteurs

- **ID:** 7083
- **Dashboard:** 136
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT "source"."departement_candidat" AS "departement_candidat", CAST(SUM(CASE WHEN "source"."Candidat accepté" = 'candidats acceptés' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux de candidats acceptés" FROM (SELECT "public"."taux_transformation_prescripteurs"."departement_candidat" AS "departement_candidat", "public"."taux_transformation_prescripteurs"."total_embauches" AS "total_embauches", CASE WHEN "public"."taux_transformation_prescripteurs"."total_embauches" > 0 THEN 'candidats acceptés' ELSE 'candidats non acceptés' END AS "Candidat accepté" FROM "public"."taux_transformation_prescripteurs") AS "source" GROUP BY "source"."departement_candidat" ORDER BY "source"."departement_candidat" ASC
```

## [136] candidats orientés par les prescripteurs habilités acceptés en IAE sur les 3 derniers mois - prescripteurs

- **ID:** 7084
- **Dashboard:** 136
- **Tables:** candidatures, public, taux_transformation_prescripteurs

```sql
SELECT count(distinct "public"."taux_transformation_prescripteurs"."id_candidat") AS "count" FROM "public"."taux_transformation_prescripteurs" LEFT JOIN "public"."candidatures" AS "Candidatures" ON "public"."taux_transformation_prescripteurs"."id_candidat" = "Candidatures"."id_candidat" WHERE ("public"."taux_transformation_prescripteurs"."date_diagnostic" IS NOT NULL) AND ("Candidatures"."date_embauche" IS NOT NULL)
```

## [136] Répartition des nouveaux candidats orientés par les prescripteurs habilités par mois V2 - prescripteurs

- **ID:** 7085
- **Dashboard:** 136
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) AS "date_diagnostic", "source"."État du candidat" AS "État du candidat", count(distinct "source"."id_candidat") AS "Nombre de Nouveaux candidats orientés chaque mois (entrée)" FROM (SELECT "public"."taux_transformation_prescripteurs"."id_candidat" AS "id_candidat", "public"."taux_transformation_prescripteurs"."date_diagnostic" AS "date_diagnostic", "public"."taux_transformation_prescripteurs"."total_embauches" AS "total_embauches", CASE WHEN "public"."taux_transformation_prescripteurs"."total_embauches" > 0 THEN 'candidats acceptés' ELSE 'candidats non acceptés' END AS "État du candidat" FROM "public"."taux_transformation_prescripteurs" WHERE ("public"."taux_transformation_prescripteurs"."date_diagnostic" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" < DATE_TRUNC('year', (NOW() + INTERVAL '1 year'))) AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" > date '2021-01-01')) AS "source" GROUP BY CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date), "source"."État du candidat" ORDER BY CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) ASC, "source"."État du candidat" ASC
```

## [136] % candidats orientés et acceptés

- **ID:** 7086
- **Dashboard:** 136
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT CAST(SUM(CASE WHEN ("public"."taux_transformation_prescripteurs"."total_embauches" <> 0) OR ("public"."taux_transformation_prescripteurs"."total_embauches" IS NULL) THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidats acceptés en IAE" FROM "public"."taux_transformation_prescripteurs" WHERE "public"."taux_transformation_prescripteurs"."date_diagnostic" IS NOT NULL
```

## [136] Répartition des nouveaux candidats orientés par les prescripteurs habilités par mois V1 - diagnostic valide

- **ID:** 7087
- **Dashboard:** 136
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) AS "date_diagnostic", count(distinct "source"."id_candidat") AS "Nombre de nouveaux candidats orientés", CAST(SUM(CASE WHEN "source"."Candidat accepté" = 'candidat accepté' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux de candidats acceptés" FROM (SELECT "public"."taux_transformation_prescripteurs"."id_candidat" AS "id_candidat", "public"."taux_transformation_prescripteurs"."date_diagnostic" AS "date_diagnostic", "public"."taux_transformation_prescripteurs"."total_embauches" AS "total_embauches", "public"."taux_transformation_prescripteurs"."diagnostic_valide" AS "diagnostic_valide", CASE WHEN "public"."taux_transformation_prescripteurs"."total_embauches" > 0 THEN 'candidat accepté' ELSE 'candidat non accepté' END AS "Candidat accepté" FROM "public"."taux_transformation_prescripteurs" WHERE ("public"."taux_transformation_prescripteurs"."date_diagnostic" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" < DATE_TRUNC('year', (NOW() + INTERVAL '1 year'))) AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" > date '2021-01-01') AND ("public"."taux_transformation_prescripteurs"."diagnostic_valide" = 'Oui')) AS "source" GROUP BY CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) ORDER BY CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) ASC
```

## [136] Répartition des nouveaux candidats orientés par les prescripteurs habilités par mois V1 - diagnostic non valide"

- **ID:** 7088
- **Dashboard:** 136
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) AS "date_diagnostic", count(distinct "source"."id_candidat") AS "Nombre de nouveaux candidats orientés", CAST(SUM(CASE WHEN "source"."Candidat accepté" = 'candidat accepté' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux de candidats acceptés" FROM (SELECT "public"."taux_transformation_prescripteurs"."id_candidat" AS "id_candidat", "public"."taux_transformation_prescripteurs"."date_diagnostic" AS "date_diagnostic", "public"."taux_transformation_prescripteurs"."total_embauches" AS "total_embauches", "public"."taux_transformation_prescripteurs"."diagnostic_valide" AS "diagnostic_valide", CASE WHEN "public"."taux_transformation_prescripteurs"."total_embauches" > 0 THEN 'candidat accepté' ELSE 'candidat non accepté' END AS "Candidat accepté" FROM "public"."taux_transformation_prescripteurs" WHERE ("public"."taux_transformation_prescripteurs"."date_diagnostic" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" < DATE_TRUNC('year', (NOW() + INTERVAL '1 year'))) AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" > date '2021-01-01') AND ("public"."taux_transformation_prescripteurs"."diagnostic_valide" = 'non')) AS "source" GROUP BY CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) ORDER BY CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) ASC
```

## [136] Répartition du nombre de candidats par type de prescripteur

- **ID:** 7089
- **Dashboard:** 136
- **Tables:** public, taux_transformation_prescripteurs

```sql
SELECT "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" AS "type_auteur_diagnostic_detaille", COUNT(*) AS "count" FROM "public"."taux_transformation_prescripteurs" GROUP BY "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" ORDER BY "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" ASC
```

## [52] % conseillers hors SPE

- **ID:** 7108
- **Dashboard:** 52
- **Tables:** public, organisations

```sql
SELECT CAST(SUM(CASE WHEN (("public"."organisations"."type" <> 'FT') OR ("public"."organisations"."type" IS NULL)) AND (("public"."organisations"."type" <> 'ML') OR ("public"."organisations"."type" IS NULL)) AND (("public"."organisations"."type" <> 'CAP_EMPLOI') OR ("public"."organisations"."type" IS NULL)) THEN "public"."organisations"."total_membres" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."organisations"."total_membres") AS DOUBLE PRECISION), 0.0) AS "% conseillers hors SPE" FROM "public"."organisations" WHERE "public"."organisations"."date_inscription" IS NOT NULL
```

## [52] % conseillers SPE

- **ID:** 7109
- **Dashboard:** 52
- **Tables:** public, organisations

```sql
SELECT CAST(SUM(CASE WHEN "public"."organisations"."type" = 'FT' THEN "public"."organisations"."total_membres" ELSE 0.0 END) + SUM(CASE WHEN "public"."organisations"."type" = 'ML' THEN "public"."organisations"."total_membres" ELSE 0.0 END) + SUM(CASE WHEN "public"."organisations"."type" = 'CAP_EMPLOI' THEN "public"."organisations"."total_membres" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."organisations"."total_membres") AS DOUBLE PRECISION), 0.0) AS "% conseillers SPE" FROM "public"."organisations" WHERE "public"."organisations"."date_inscription" IS NOT NULL
```

## [52] nombre total de conseillers inscrits

- **ID:** 7110
- **Dashboard:** 52
- **Tables:** public, organisations

```sql
SELECT SUM("public"."organisations"."total_membres") AS "Nombre total de conseillers inscrits" FROM "public"."organisations" WHERE "public"."organisations"."date_inscription" IS NOT NULL
```

## Evolution du nombre de prescripteurs inscrits

- **ID:** 7111
- **Tables:** public, organisations

```sql
SELECT "source"."date_inscription" AS "date_inscription", SUM(COUNT(*)) OVER (ORDER BY "source"."date_inscription" ASC ROWS UNBOUNDED PRECEDING) AS "count" FROM (SELECT CAST(DATE_TRUNC('week', "public"."organisations"."date_inscription") AS date) AS "date_inscription" FROM "public"."organisations" WHERE "public"."organisations"."date_inscription" IS NOT NULL) AS "source" GROUP BY "source"."date_inscription" ORDER BY "source"."date_inscription" ASC
```

## [52] Tableau des prescripteurs par type détaillé

- **ID:** 7112
- **Dashboard:** 52
- **Tables:** public, organisations

```sql
SELECT "public"."organisations"."type_complet" AS "type_complet", "public"."organisations"."nom" AS "nom", "public"."organisations"."ville" AS "ville", "public"."organisations"."code_postal" AS "code_postal", "public"."organisations"."adresse_ligne_1" AS "adresse_ligne_1", "public"."organisations"."région" AS "région", "public"."organisations"."nom_département" AS "nom_département", "public"."organisations"."date_inscription" AS "date_inscription", "public"."organisations"."type" AS "type", COUNT(*) AS "count", SUM("public"."organisations"."total_membres") AS "sum" FROM "public"."organisations" WHERE "public"."organisations"."date_inscription" IS NOT NULL GROUP BY "public"."organisations"."type_complet", "public"."organisations"."nom", "public"."organisations"."ville", "public"."organisations"."code_postal", "public"."organisations"."adresse_ligne_1", "public"."organisations"."région", "public"."organisations"."nom_département", "public"."organisations"."date_inscription", "public"."organisations"."type" ORDER BY "sum" DESC, "public"."organisations"."type_complet" ASC, "public"."organisations"."nom" ASC, "public"."organisations"."ville" ASC, "public"."organisations"."code_postal" ASC, "public"."organisations"."adresse_ligne_1" ASC, "public"."organisations"."région" ASC, "public"."organisations"."nom_département" ASC, "public"."organisations"."date_inscription" ASC, "public"."organisations"."type" ASC
```
