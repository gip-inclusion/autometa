# Thème : employeurs

*SIAE and employer information*

**42 cartes**

## [116] Taux de refus des structures

- **ID:** 997
- **Dashboard:** 116
- **Tables:** tx_refus_siae

```sql
SELECT "public"."tx_refus_siae"."type_structure" AS "type_structure", CAST(SUM("public"."tx_refus_siae"."nombre_candidatures_refusees") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."tx_refus_siae"."nombre_candidatures") AS DOUBLE PRECISION), 0.0) AS "Taux de refus", SUM("public"."tx_refus_siae"."nombre_candidatures") AS "Nombre de candidatures", SUM("public"."tx_refus_siae"."nombre_fiches_poste_ouvertes") AS "Nombre de postes ouverts", SUM("public"."tx_refus_siae"."nombre_siae") AS "Nombre de SIAE", SUM("public"."tx_refus_siae"."nombre_candidatures") - SUM("public"."tx_refus_siae"."nombre_candidatures_employeurs") AS "Nombre de candidatures hors auto-prescription", CAST(SUM("public"."tx_refus_siae"."nb_candidatures_refusees_non_emises_par_employeur_siae") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."tx_refus_siae"."nombre_candidatures") - SUM("public"."tx_refus_siae"."nombre_candidatures_employeurs") AS DOUBLE PRECISION), 0.0) AS "Taux de refus hors auto-prescription" 
FROM "public"."tx_refus_siae" 
GROUP BY "public"."tx_refus_siae"."type_structure" 
ORDER BY "public"."tx_refus_siae"."type_structure" ASC
```

## Evolution du nombre de prescripteurs inscrits

- **ID:** 1527
- **Dashboard:** 52
- **Tables:** organisations

```sql
SELECT "source"."date_inscription" AS "date_inscription", SUM(COUNT(*)) OVER (ORDER BY "source"."date_inscription" ASC ROWS UNBOUNDED PRECEDING) AS "count" 
FROM (SELECT CAST(DATE_TRUNC('week', "public"."organisations"."date_inscription") AS date) AS "date_inscription" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL) AS "source" 
GROUP BY "source"."date_inscription" 
ORDER BY "source"."date_inscription" ASC
```

## Carte des orienteurs

- **ID:** 1749
- **Dashboard:** 218
- **Tables:** organisations

```sql
SELECT "public"."organisations"."département" AS "département", COUNT(*) AS "count" 
FROM "public"."organisations" 
WHERE (("public"."organisations"."total_membres" <> 0) 
OR ("public"."organisations"."total_membres" IS NULL)) 
AND ("public"."organisations"."habilitée" = 0) 
GROUP BY "public"."organisations"."département" 
ORDER BY "public"."organisations"."département" ASC
```

## [267] Nombre de SIAE pratiquant l'auto prescription

- **ID:** 2006
- **Dashboard:** 32
- **Tables:** siae_pratiquant_autoprescription

```sql
SELECT SUM("public"."siae_pratiquant_autoprescription"."Nombre de structures utilisant l'autoprescription") AS "sum" 
FROM "public"."siae_pratiquant_autoprescription"
```

## [267] Nombre total de SIAE

- **ID:** 2007
- **Dashboard:** 32
- **Tables:** siae_pratiquant_autoprescription

```sql
SELECT SUM("public"."siae_pratiquant_autoprescription"."Nombre total de structures") AS "sum" 
FROM "public"."siae_pratiquant_autoprescription" 
WHERE ("public"."siae_pratiquant_autoprescription"."type_structure" = 'ACI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'AI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'EI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'EITI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'ETTI')
```

## [267] % de structures pratiquant l'auto prescription

- **ID:** 2008
- **Dashboard:** 32
- **Tables:** siae_pratiquant_autoprescription

```sql
SELECT CAST(SUM("public"."siae_pratiquant_autoprescription"."Nombre de structures utilisant l'autoprescription") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."siae_pratiquant_autoprescription"."Nombre total de structures") AS DOUBLE PRECISION), 0.0) AS "% de Siae pratiquant l'auto prescription" 
FROM "public"."siae_pratiquant_autoprescription" 
WHERE ("public"."siae_pratiquant_autoprescription"."type_structure" = 'ACI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'AI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'EI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'ETTI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'EITI')
```

## [265] part SIAE ctrlées pos vs neg

- **ID:** 2017
- **Dashboard:** 32
- **Tables:** cap_campagnes, cap_structures, structures

```sql
SELECT "source"."état" AS "état", COUNT(*) AS "count" 
FROM (SELECT CASE WHEN "public"."cap_structures"."état" = 'ACCEPTED' THEN 'Résultats positifs' WHEN "public"."cap_structures"."état" = 'REFUSED' THEN 'Résultats négatifs' WHEN "public"."cap_structures"."état" = 'NOTIFICATION_PENDING' THEN 'Résultats négatifs' END AS "état" 
FROM "public"."cap_structures" LEFT 
JOIN (SELECT "public"."structures"."id" AS "id", "public"."structures"."id_asp" AS "id_asp", "public"."structures"."nom" AS "nom", "public"."structures"."nom_complet" AS "nom_complet", "public"."structures"."description" AS "description", "public"."structures"."type" AS "type", "public"."structures"."siret" AS "siret", "public"."structures"."code_naf" AS "code_naf", "public"."structures"."email_public" AS "email_public", "public"."structures"."email_authentification" AS "email_authentification", "public"."structures"."convergence_france" AS "convergence_france", "public"."structures"."adresse_ligne_1" AS "adresse_ligne_1", "public"."structures"."adresse_ligne_2" AS "adresse_ligne_2", "public"."structures"."code_postal" AS "code_postal", "public"."structures"."code_commune" AS "code_commune", "public"."structures"."longitude" AS "longitude", "public"."structures"."latitude" AS "latitude", "public"."structures"."département" AS "département", "public"."structures"."nom_département" AS "nom_département", "public"."structures"."région" AS "région", "public"."structures"."adresse_ligne_1_c1" AS "adresse_ligne_1_c1", "public"."structures"."adresse_ligne_2_c1" AS "adresse_ligne_2_c1", "public"."structures"."code_postal_c1" AS "code_postal_c1", "public"."structures"."code_commune_c1" AS "code_commune_c1", "public"."structures"."ville_c1" AS "ville_c1", "public"."structures"."longitude_c1" AS "longitude_c1", "public"."structures"."latitude_c1" AS "latitude_c1", "public"."structures"."département_c1" AS "département_c1", "public"."structures"."nom_département_c1" AS "nom_département_c1", "public"."structures"."région_c1" AS "région_c1", "public"."structures"."date_inscription" AS "date_inscription", "public"."structures"."total_membres" AS "total_membres", "public"."structures"."total_candidatures" AS "total_candidatures", "public"."structures"."total_candidatures_30j" AS "total_candidatures_30j", "public"."structures"."total_embauches" AS "total_embauches", "public"."structures"."total_embauches_30j" AS "total_embauches_30j", "public"."structures"."taux_conversion_30j" AS "taux_conversion_30j", "public"."structures"."total_auto_prescriptions" AS "total_auto_prescriptions", "public"."structures"."total_candidatures_autonomes" AS "total_candidatures_autonomes", "public"."structures"."total_candidatures_via_prescripteur" AS "total_candidatures_via_prescripteur", "public"."structures"."total_candidatures_non_traitées" AS "total_candidatures_non_traitées", "public"."structures"."total_candidatures_en_étude" AS "total_candidatures_en_étude", "public"."structures"."date_dernière_connexion" AS "date_der
-- ... (truncated)
```

## [265] Nb de structures dont le contrôle est terminé

- **ID:** 2291
- **Dashboard:** 32
- **Tables:** suivi_cap_structures

```sql
SELECT count(distinct "public"."suivi_cap_structures"."id_structure") AS "Nb structures contrôlées" 
FROM "public"."suivi_cap_structures" 
WHERE ("public"."suivi_cap_structures"."état" = 'ACCEPTED') 
OR ("public"."suivi_cap_structures"."état" = 'REFUSED')
```

## [265] SIAE à contrôler

- **ID:** 2438
- **Dashboard:** 32
- **Tables:** cap_campagnes, cap_structures

```sql
SELECT count(distinct "public"."cap_structures"."id_structure") AS "structures à contrôler" 
FROM "public"."cap_structures" LEFT 
JOIN (SELECT "public"."cap_campagnes"."id" AS "id", "public"."cap_campagnes"."nom" AS "nom", "public"."cap_campagnes"."id_institution" AS "id_institution", "public"."cap_campagnes"."date_début" AS "date_début", "public"."cap_campagnes"."date_fin" AS "date_fin", "public"."cap_campagnes"."pourcentage_sélection" AS "pourcentage_sélection", "public"."cap_campagnes"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" 
FROM "public"."cap_campagnes") AS "Cap Campagnes" ON "public"."cap_structures"."id_cap_campagne" = "Cap Campagnes"."id"
```

## [54] Répartition des employeurs et métiers - detaillé

- **ID:** 2589
- **Dashboard:** 54
- **Tables:** structures

```sql
SELECT "public"."structures"."type" AS "type", "public"."structures"."total_membres" AS "total_membres", "public"."structures"."date_inscription" AS "date_inscription", "public"."structures"."adresse_ligne_1" AS "adresse_ligne_1", "public"."structures"."ville" AS "ville", "public"."structures"."code_postal" AS "code_postal", "public"."structures"."nom_département" AS "nom_département", "public"."structures"."région" AS "région", "public"."structures"."nom" AS "nom", COUNT(*) AS "count", SUM("public"."structures"."total_fiches_de_poste_actives") AS "sum" 
FROM "public"."structures" 
WHERE ("public"."structures"."date_inscription" IS NOT NULL) 
AND (("public"."structures"."source" = 'Export ASP') 
OR ("public"."structures"."source" = 'Export EA+EATT') 
OR ("public"."structures"."source" = 'Export GEIQ')) 
GROUP BY "public"."structures"."type", "public"."structures"."total_membres", "public"."structures"."date_inscription", "public"."structures"."adresse_ligne_1", "public"."structures"."ville", "public"."structures"."code_postal", "public"."structures"."nom_département", "public"."structures"."région", "public"."structures"."nom" 
ORDER BY "public"."structures"."type" ASC, "public"."structures"."total_membres" ASC, "public"."structures"."date_inscription" ASC, "public"."structures"."adresse_ligne_1" ASC, "public"."structures"."ville" ASC, "public"."structures"."code_postal" ASC, "public"."structures"."nom_département" ASC, "public"."structures"."région" ASC, "public"."structures"."nom" ASC
```

## [52] Tableau des prescripteurs par type détaillé

- **ID:** 2590
- **Dashboard:** 52
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
- **Dashboard:** 52
- **Tables:** organisations

```sql
SELECT CAST(SUM(CASE WHEN "public"."organisations"."type" = 'FT' THEN "public"."organisations"."total_membres" ELSE 0.0 END) + SUM(CASE WHEN "public"."organisations"."type" = 'ML' THEN "public"."organisations"."total_membres" ELSE 0.0 END) + SUM(CASE WHEN "public"."organisations"."type" = 'CAP_EMPLOI' THEN "public"."organisations"."total_membres" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."organisations"."total_membres") AS DOUBLE PRECISION), 0.0) AS "% conseillers SPE" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL
```

## [52] % conseillers hors SPE

- **ID:** 2602
- **Dashboard:** 52
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
- **Dashboard:** 52
- **Tables:** organisations

```sql
SELECT SUM("public"."organisations"."total_membres") AS "Nombre total de conseillers inscrits" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL
```

## [287] Répartition par type de structure de l'effectif annuel conventionné

- **ID:** 2688
- **Dashboard:** 287
- **Tables:** suivi_etp_conventionnes_v2

```sql
SELECT "public"."suivi_etp_conventionnes_v2"."type_structure" AS "type_structure", SUM("public"."suivi_etp_conventionnes_v2"."effectif_annuel_conventionné") AS "sum" 
FROM "public"."suivi_etp_conventionnes_v2" 
GROUP BY "public"."suivi_etp_conventionnes_v2"."type_structure" 
ORDER BY "public"."suivi_etp_conventionnes_v2"."type_structure" ASC
```

## [287]  Effectif annuel consommé - cumulatif

- **ID:** 2690
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT "source"."af_date_fin_effet_v2" AS "af_date_fin_effet_v2", SUM(SUM("source"."nombre_etp_consommes_reels_annuels")) OVER (ORDER BY "source"."af_date_fin_effet_v2" ASC ROWS UNBOUNDED PRECEDING) AS "sum", SUM(SUM("source"."effectif_annuel_conventionné_mensualisé")) OVER (ORDER BY "source"."af_date_fin_effet_v2" ASC ROWS UNBOUNDED PRECEDING) AS "sum_2" 
FROM (SELECT DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") AS "af_date_fin_effet_v2", "public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_annuels" AS "nombre_etp_consommes_reels_annuels", "public"."suivi_realisation_convention_mensuelle"."effectif_annuel_conventionné_mensualisé" AS "effectif_annuel_conventionné_mensualisé" 
FROM "public"."suivi_realisation_convention_mensuelle") AS "source" 
GROUP BY "source"."af_date_fin_effet_v2" 
ORDER BY "source"."af_date_fin_effet_v2" ASC
```

## [287] Répartition par structure de l'effectif annuel consommé

- **ID:** 2691
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT "public"."suivi_realisation_convention_mensuelle"."type_structure" AS "type_structure", SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_annuels") AS "sum" 
FROM "public"."suivi_realisation_convention_mensuelle" 
GROUP BY "public"."suivi_realisation_convention_mensuelle"."type_structure" 
ORDER BY "public"."suivi_realisation_convention_mensuelle"."type_structure" ASC
```

## [287] Table détaillée du conventionnement et de la consommation de l'effectif annuel

- **ID:** 2692
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT "public"."suivi_realisation_convention_mensuelle"."annee_af" AS "annee_af", "public"."suivi_realisation_convention_mensuelle"."type_structure" AS "type_structure", "public"."suivi_realisation_convention_mensuelle"."nom_departement_af" AS "nom_departement_af", "public"."suivi_realisation_convention_mensuelle"."nom_region_af" AS "nom_region_af", CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION) / 12.0 AS "Effectif annuel conventionné (en ETP)", CAST(SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS DOUBLE PRECISION) / 12.0 AS "Effectif annuel réalisé (en ETP)", CAST(SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION), 0.0) AS "% de réalisation" 
FROM "public"."suivi_realisation_convention_mensuelle" 
GROUP BY "public"."suivi_realisation_convention_mensuelle"."annee_af", "public"."suivi_realisation_convention_mensuelle"."type_structure", "public"."suivi_realisation_convention_mensuelle"."nom_departement_af", "public"."suivi_realisation_convention_mensuelle"."nom_region_af" 
ORDER BY "public"."suivi_realisation_convention_mensuelle"."annee_af" DESC, "public"."suivi_realisation_convention_mensuelle"."type_structure" ASC, "public"."suivi_realisation_convention_mensuelle"."nom_departement_af" ASC, "public"."suivi_realisation_convention_mensuelle"."nom_region_af" ASC
```

## [287] Tableau de la répartition de l'effectif mensuel (états mensuels validés)

- **ID:** 2902
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT "public"."suivi_realisation_convention_mensuelle"."annee_af" AS "annee_af", "public"."suivi_realisation_convention_mensuelle"."type_structure" AS "type_structure", "public"."suivi_realisation_convention_mensuelle"."nom_departement_af" AS "nom_departement_af", "public"."suivi_realisation_convention_mensuelle"."nom_region_af" AS "nom_region_af", DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") AS "af_date_fin_effet_v2", SUM(CASE WHEN "public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" = 'VALIDE' THEN "public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels" ELSE 0.0 END) AS "Effectif mensuel réalisé (en ETP)", SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS "Effectif mensuel conventionné (en ETP)", CAST(SUM(CASE WHEN "public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" = 'VALIDE' THEN "public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION), 0.0) AS "% de réalisation" 
FROM "public"."suivi_realisation_convention_mensuelle" 
GROUP BY "public"."suivi_realisation_convention_mensuelle"."annee_af", "public"."suivi_realisation_convention_mensuelle"."type_structure", "public"."suivi_realisation_convention_mensuelle"."nom_departement_af", "public"."suivi_realisation_convention_mensuelle"."nom_region_af", DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") 
ORDER BY "public"."suivi_realisation_convention_mensuelle"."annee_af" ASC, "public"."suivi_realisation_convention_mensuelle"."type_structure" ASC, "public"."suivi_realisation_convention_mensuelle"."nom_departement_af" ASC, "public"."suivi_realisation_convention_mensuelle"."nom_region_af" ASC, DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") ASC
```

## [287] Pourcentage de réalisation par type de structure

- **ID:** 2912
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT "public"."suivi_realisation_convention_mensuelle"."type_structure" AS "type_structure", CAST(SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION), 0.0) AS "% de réalisation" 
FROM "public"."suivi_realisation_convention_mensuelle" 
GROUP BY "public"."suivi_realisation_convention_mensuelle"."type_structure" 
ORDER BY "public"."suivi_realisation_convention_mensuelle"."type_structure" ASC
```

## [287] Pourcentage de réalisation

- **ID:** 2913
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT CAST(SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION), 0.0) AS "% de réalisation" 
FROM "public"."suivi_realisation_convention_mensuelle"
```

## [287] Suivi mensuel des effectifs mensuels conventionnés et réalisés + réalisation

- **ID:** 2922
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") AS "af_date_fin_effet_v2", SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS "Effectif mensuel réalisé (en ETP)", SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS "Effectif mensuel conventionné (en ETP)", CAST(SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION), 0.0) AS "% de réalisation" 
FROM "public"."suivi_realisation_convention_mensuelle" 
GROUP BY DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") 
ORDER BY DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") ASC
```

## [287] Distribution du nombre d'ETP surconsommés

- **ID:** 2928
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_par_structure

```sql
SELECT FLOOR(("public"."suivi_realisation_convention_par_structure"."delta_etp_conventionnes_realises" / 20.0)) * 20.0 AS "delta_etp_conventionnes_realises", "public"."suivi_realisation_convention_par_structure"."type_structure" AS "type_structure", COUNT(*) AS "count" 
FROM "public"."suivi_realisation_convention_par_structure" 
WHERE ("public"."suivi_realisation_convention_par_structure"."delta_etp_conventionnes_realises" > 1) 
AND ("public"."suivi_realisation_convention_par_structure"."emi_esm_etat_code" = 'VALIDE') 
GROUP BY FLOOR(("public"."suivi_realisation_convention_par_structure"."delta_etp_conventionnes_realises" / 20.0)) * 20.0, "public"."suivi_realisation_convention_par_structure"."type_structure" 
ORDER BY FLOOR(("public"."suivi_realisation_convention_par_structure"."delta_etp_conventionnes_realises" / 20.0)) * 20.0 ASC, "public"."suivi_realisation_convention_par_structure"."type_structure" ASC
```

## [287] Nombre de structures en sur consommation

- **ID:** 2929
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_par_structure

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."suivi_realisation_convention_par_structure" 
WHERE ("public"."suivi_realisation_convention_par_structure"."delta_etp_conventionnes_realises" > 0) 
AND ("public"."suivi_realisation_convention_par_structure"."emi_esm_etat_code" = 'VALIDE')
```

## [287] Pourcentage de réalisation (états mensuels validés)

- **ID:** 2930
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT CAST(SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION), 0.0) AS "% de réalisation" 
FROM "public"."suivi_realisation_convention_mensuelle" 
WHERE "public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" = 'VALIDE'
```

## [287] Nombre de structures

- **ID:** 2931
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_par_structure

```sql
SELECT count(distinct "public"."suivi_realisation_convention_par_structure"."id_annexe_financiere") AS "count" 
FROM "public"."suivi_realisation_convention_par_structure"
```

## [287] Suivi du remplissage des états mensuels

- **ID:** 2932
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT "public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" AS "emi_esm_etat_code", DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") AS "af_date_fin_effet_v2", COUNT(*) AS "count" 
FROM "public"."suivi_realisation_convention_mensuelle" 
GROUP BY "public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code", DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") 
ORDER BY "public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" ASC, DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") ASC
```

## [287] Pourcentage de réalisation par type de structure (états mensuels validés)

- **ID:** 2933
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT "public"."suivi_realisation_convention_mensuelle"."type_structure" AS "type_structure", CAST(SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION), 0.0) AS "% de réalisation" 
FROM "public"."suivi_realisation_convention_mensuelle" 
WHERE "public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" = 'VALIDE' 
GROUP BY "public"."suivi_realisation_convention_mensuelle"."type_structure" 
ORDER BY "public"."suivi_realisation_convention_mensuelle"."type_structure" ASC
```

## Répartition orienteurs inscrits par type

- **ID:** 3504
- **Dashboard:** 337
- **Tables:** organisations

```sql
SELECT "public"."organisations"."type_prescripteur" AS "type_prescripteur", COUNT(*) AS "count" 
FROM "public"."organisations" 
WHERE ("public"."organisations"."total_membres" <> 0) 
OR ("public"."organisations"."total_membres" IS NULL) 
GROUP BY "public"."organisations"."type_prescripteur" 
ORDER BY "count" DESC, "public"."organisations"."type_prescripteur" ASC
```

## Répartition des conseilleurs inscrits par type de prescripteurs

- **ID:** 3622
- **Dashboard:** 337
- **Tables:** organisations

```sql
SELECT "public"."organisations"."type_prescripteur" AS "type_prescripteur", SUM("public"."organisations"."total_membres") AS "Nombre total de conseillers inscrits" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL 
GROUP BY "public"."organisations"."type_prescripteur" 
ORDER BY "Nombre total de conseillers inscrits" DESC, "public"."organisations"."type_prescripteur" ASC
```

## Répartition SIAE par type

- **ID:** 3623
- **Dashboard:** 337
- **Tables:** structures

```sql
SELECT "public"."structures"."type" AS "type", COUNT(*) AS "count" 
FROM "public"."structures" 
WHERE ("public"."structures"."date_inscription" IS NOT NULL) 
AND (("public"."structures"."source" = 'Export ASP') 
OR ("public"."structures"."source" = 'Staff Itou')) 
AND (("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI')) 
GROUP BY "public"."structures"."type" 
ORDER BY "count" DESC, "public"."structures"."type" ASC
```

## Carto de la répartition des SIAE

- **ID:** 3624
- **Dashboard:** 337
- **Tables:** structures

```sql
SELECT "public"."structures"."département" AS "département", COUNT(*) AS "count" 
FROM "public"."structures" 
WHERE ("public"."structures"."date_inscription" IS NOT NULL) 
AND (("public"."structures"."source" = 'Export ASP') 
OR ("public"."structures"."source" = 'Export EA+EATT') 
OR ("public"."structures"."source" = 'Export GEIQ') 
OR ("public"."structures"."source" = 'Utilisateur (OPCS)') 
OR ("public"."structures"."source" = 'Staff Itou (OPCS)')) 
AND (("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI')) 
GROUP BY "public"."structures"."département" 
ORDER BY "count" DESC, "public"."structures"."département" ASC
```

## Cartographie des prescripteurs

- **ID:** 3625
- **Dashboard:** 337
- **Tables:** organisations

```sql
SELECT "public"."organisations"."département" AS "département", COUNT(*) AS "count" 
FROM "public"."organisations" 
WHERE ("public"."organisations"."total_membres" <> 0) 
OR ("public"."organisations"."total_membres" IS NULL) 
GROUP BY "public"."organisations"."département" 
ORDER BY "count" DESC, "public"."organisations"."département" ASC
```

## % de SIAE avec un poste ouvert

- **ID:** 3644
- **Dashboard:** 337
- **Tables:** structures

```sql
SELECT CAST(SUM(CASE WHEN ("public"."structures"."total_fiches_de_poste_actives" <> 0) 
OR ("public"."structures"."total_fiches_de_poste_actives" IS NULL) THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression" 
FROM "public"."structures" 
WHERE ("public"."structures"."date_inscription" IS NOT NULL) 
AND ("public"."structures"."categorie_structure" = 'IAE') 
AND (("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI'))
```

## [287] Etats mensuels non validés et ETP conventionnés

- **ID:** 3654
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") AS "af_date_fin_effet_v2", "public"."suivi_realisation_convention_mensuelle"."type_structure" AS "type_structure", SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS "Effectif mensuel conventionné (en ETP)", COUNT(*) AS "count" 
FROM "public"."suivi_realisation_convention_mensuelle" 
WHERE (("public"."suivi_realisation_convention_mensuelle"."type_structure" = 'ACI Droit commun') 
OR ("public"."suivi_realisation_convention_mensuelle"."type_structure" = 'ETTI Droit commun') 
OR ("public"."suivi_realisation_convention_mensuelle"."type_structure" = 'EI Milieu pénitentiaire') 
OR ("public"."suivi_realisation_convention_mensuelle"."type_structure" = 'EI Droit commun') 
OR ("public"."suivi_realisation_convention_mensuelle"."type_structure" = 'AI Droit commun') 
OR ("public"."suivi_realisation_convention_mensuelle"."type_structure" = 'ACI Milieu pénitentiaire') 
OR ("public"."suivi_realisation_convention_mensuelle"."type_structure" = 'EITI Droit commun')) 
AND (("public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" <> 'VALIDE') 
OR ("public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" IS NULL)) 
GROUP BY DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2"), "public"."suivi_realisation_convention_mensuelle"."type_structure" 
ORDER BY DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") ASC, "public"."suivi_realisation_convention_mensuelle"."type_structure" ASC
```

## [287] Table etats mensuels non validés et ETP conventionnés

- **ID:** 3655
- **Dashboard:** 287
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") AS "af_date_fin_effet_v2", "public"."suivi_realisation_convention_mensuelle"."type_structure" AS "type_structure", SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS "Effectif mensuel conventionné (en ETP)", COUNT(*) AS "count" 
FROM "public"."suivi_realisation_convention_mensuelle" 
WHERE (("public"."suivi_realisation_convention_mensuelle"."type_structure" = 'ACI Droit commun') 
OR ("public"."suivi_realisation_convention_mensuelle"."type_structure" = 'ETTI Droit commun') 
OR ("public"."suivi_realisation_convention_mensuelle"."type_structure" = 'EI Milieu pénitentiaire') 
OR ("public"."suivi_realisation_convention_mensuelle"."type_structure" = 'EI Droit commun') 
OR ("public"."suivi_realisation_convention_mensuelle"."type_structure" = 'AI Droit commun') 
OR ("public"."suivi_realisation_convention_mensuelle"."type_structure" = 'ACI Milieu pénitentiaire') 
OR ("public"."suivi_realisation_convention_mensuelle"."type_structure" = 'EITI Droit commun')) 
AND (("public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" <> 'VALIDE') 
OR ("public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" IS NULL)) 
GROUP BY DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2"), "public"."suivi_realisation_convention_mensuelle"."type_structure" 
ORDER BY DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") ASC, "public"."suivi_realisation_convention_mensuelle"."type_structure" ASC
```

## % de SIAE ayant accepté une candidature sur les 30 derniers jours

- **ID:** 3663
- **Dashboard:** 337
- **Tables:** structures

```sql
SELECT CAST(SUM(CASE WHEN ("public"."structures"."total_embauches_30j" <> 0) 
OR ("public"."structures"."total_embauches_30j" IS NULL) THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression" 
FROM "public"."structures" 
WHERE ("public"."structures"."date_inscription" IS NOT NULL) 
AND (("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI')) 
AND (("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI'))
```

## [337] Nombre de structures mère

- **ID:** 3674
- **Dashboard:** 54
- **Tables:** structures

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."structures" 
WHERE ("public"."structures"."date_inscription" IS NOT NULL) 
AND (("public"."structures"."source" = 'Export ASP') 
OR ("public"."structures"."source" = 'Staff Itou')) 
AND (("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI'))
```

## [337] Nombre de structures antenne

- **ID:** 3675
- **Dashboard:** 54
- **Tables:** structures

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."structures" 
WHERE ("public"."structures"."date_inscription" IS NOT NULL) 
AND ("public"."structures"."source" = 'Utilisateur (Antenne)') 
AND (("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI')) 
AND (("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI'))
```

## [337] Nombre total (mère + antenne) de structures sur les emplois

- **ID:** 3676
- **Dashboard:** 337
- **Tables:** structures

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."structures" 
WHERE ("public"."structures"."date_inscription" IS NOT NULL) 
AND (("public"."structures"."source" = 'Utilisateur (Antenne)') 
OR ("public"."structures"."source" = 'Export ASP') 
OR ("public"."structures"."source" = 'Staff Itou')) 
AND (("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI')) 
AND (("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI'))
```

## Organisations, Nombre total de conseillers inscrits, Grouped by Date Inscription: Year, Filtered by Date Inscription is not empty, Sorted by Nombre total de conseillers inscrits descending

- **ID:** 3688
- **Dashboard:** 337
- **Tables:** organisations

```sql
SELECT CAST(DATE_TRUNC('year', "public"."organisations"."date_inscription") AS date) AS "date_inscription", SUM("public"."organisations"."total_membres") AS "Nombre total de conseillers inscrits" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL 
GROUP BY CAST(DATE_TRUNC('year', "public"."organisations"."date_inscription") AS date) 
ORDER BY "Nombre total de conseillers inscrits" DESC, CAST(DATE_TRUNC('year', "public"."organisations"."date_inscription") AS date) ASC
```

## [265] % SIAE contrôlées parmi les SIAE à contrôler - v2

- **ID:** 5017
- **Dashboard:** 32
- **Tables:** cap_campagnes, cap_structures, suivi_cap_structures

```sql
SELECT CAST(count(distinct CASE WHEN "Suivi Cap Structures - ID Structure"."état" = 'ACCEPTED' THEN "public"."cap_structures"."id_structure" WHEN "Suivi Cap Structures - ID Structure"."état" = 'REFUSED' THEN "public"."cap_structures"."id_structure" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "public"."cap_structures"."id_structure") AS DOUBLE PRECISION), 0.0) AS "% ctrl terminés" 
FROM "public"."cap_structures" LEFT 
JOIN (SELECT "public"."cap_campagnes"."id" AS "id", "public"."cap_campagnes"."nom" AS "nom", "public"."cap_campagnes"."id_institution" AS "id_institution", "public"."cap_campagnes"."date_début" AS "date_début", "public"."cap_campagnes"."date_fin" AS "date_fin", "public"."cap_campagnes"."pourcentage_sélection" AS "pourcentage_sélection", "public"."cap_campagnes"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" 
FROM "public"."cap_campagnes") AS "Cap Campagnes - ID Cap Campagne" ON "public"."cap_structures"."id_cap_campagne" = "Cap Campagnes - ID Cap Campagne"."id" LEFT 
JOIN (SELECT "public"."suivi_cap_structures"."id_cap_campagne" AS "id_cap_campagne", "public"."suivi_cap_structures"."nom_campagne" AS "nom_campagne", "public"."suivi_cap_structures"."id_cap_structure" AS "id_cap_structure", "public"."suivi_cap_structures"."id_structure" AS "id_structure", "public"."suivi_cap_structures"."type" AS "type", "public"."suivi_cap_structures"."département" AS "département", "public"."suivi_cap_structures"."nom_département" AS "nom_département", "public"."suivi_cap_structures"."région" AS "région", "public"."suivi_cap_structures"."bassin_d_emploi" AS "bassin_d_emploi", "public"."suivi_cap_structures"."état" AS "état", "public"."suivi_cap_structures"."réponse_au_contrôle" AS "réponse_au_contrôle", "public"."suivi_cap_structures"."active" AS "active", "public"."suivi_cap_structures"."controlee" AS "controlee" 
FROM "public"."suivi_cap_structures") AS "Suivi Cap Structures - ID Structure" ON "public"."cap_structures"."id_structure" = "Suivi Cap Structures - ID Structure"."id_structure"
```
