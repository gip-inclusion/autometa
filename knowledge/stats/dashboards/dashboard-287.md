# Dashboard : Pilotage dispositif - Conventionnements IAE

 version publique

**URL:** /tableaux-de-bord/conventionnements-iae/

**16 cartes**

## [287] Répartition par type de structure de l'effectif annuel conventionné

- **ID:** 2688
- **Thème:** etp-effectifs
- **Tables:** suivi_etp_conventionnes_v2

```sql
SELECT "public"."suivi_etp_conventionnes_v2"."type_structure" AS "type_structure", SUM("public"."suivi_etp_conventionnes_v2"."effectif_annuel_conventionné") AS "sum" 
FROM "public"."suivi_etp_conventionnes_v2" 
GROUP BY "public"."suivi_etp_conventionnes_v2"."type_structure" 
ORDER BY "public"."suivi_etp_conventionnes_v2"."type_structure" ASC
```

## [287]  Effectif annuel consommé - cumulatif

- **ID:** 2690
- **Thème:** etp-effectifs
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
- **Thème:** etp-effectifs
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT "public"."suivi_realisation_convention_mensuelle"."type_structure" AS "type_structure", SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_annuels") AS "sum" 
FROM "public"."suivi_realisation_convention_mensuelle" 
GROUP BY "public"."suivi_realisation_convention_mensuelle"."type_structure" 
ORDER BY "public"."suivi_realisation_convention_mensuelle"."type_structure" ASC
```

## [287] Table détaillée du conventionnement et de la consommation de l'effectif annuel

- **ID:** 2692
- **Thème:** etp-effectifs
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT "public"."suivi_realisation_convention_mensuelle"."annee_af" AS "annee_af", "public"."suivi_realisation_convention_mensuelle"."type_structure" AS "type_structure", "public"."suivi_realisation_convention_mensuelle"."nom_departement_af" AS "nom_departement_af", "public"."suivi_realisation_convention_mensuelle"."nom_region_af" AS "nom_region_af", CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION) / 12.0 AS "Effectif annuel conventionné (en ETP)", CAST(SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS DOUBLE PRECISION) / 12.0 AS "Effectif annuel réalisé (en ETP)", CAST(SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION), 0.0) AS "% de réalisation" 
FROM "public"."suivi_realisation_convention_mensuelle" 
GROUP BY "public"."suivi_realisation_convention_mensuelle"."annee_af", "public"."suivi_realisation_convention_mensuelle"."type_structure", "public"."suivi_realisation_convention_mensuelle"."nom_departement_af", "public"."suivi_realisation_convention_mensuelle"."nom_region_af" 
ORDER BY "public"."suivi_realisation_convention_mensuelle"."annee_af" DESC, "public"."suivi_realisation_convention_mensuelle"."type_structure" ASC, "public"."suivi_realisation_convention_mensuelle"."nom_departement_af" ASC, "public"."suivi_realisation_convention_mensuelle"."nom_region_af" ASC
```

## [287] Tableau de la répartition de l'effectif mensuel (états mensuels validés)

- **ID:** 2902
- **Thème:** etp-effectifs
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT "public"."suivi_realisation_convention_mensuelle"."annee_af" AS "annee_af", "public"."suivi_realisation_convention_mensuelle"."type_structure" AS "type_structure", "public"."suivi_realisation_convention_mensuelle"."nom_departement_af" AS "nom_departement_af", "public"."suivi_realisation_convention_mensuelle"."nom_region_af" AS "nom_region_af", DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") AS "af_date_fin_effet_v2", SUM(CASE WHEN "public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" = 'VALIDE' THEN "public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels" ELSE 0.0 END) AS "Effectif mensuel réalisé (en ETP)", SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS "Effectif mensuel conventionné (en ETP)", CAST(SUM(CASE WHEN "public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" = 'VALIDE' THEN "public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION), 0.0) AS "% de réalisation" 
FROM "public"."suivi_realisation_convention_mensuelle" 
GROUP BY "public"."suivi_realisation_convention_mensuelle"."annee_af", "public"."suivi_realisation_convention_mensuelle"."type_structure", "public"."suivi_realisation_convention_mensuelle"."nom_departement_af", "public"."suivi_realisation_convention_mensuelle"."nom_region_af", DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") 
ORDER BY "public"."suivi_realisation_convention_mensuelle"."annee_af" ASC, "public"."suivi_realisation_convention_mensuelle"."type_structure" ASC, "public"."suivi_realisation_convention_mensuelle"."nom_departement_af" ASC, "public"."suivi_realisation_convention_mensuelle"."nom_region_af" ASC, DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") ASC
```

## [287] Pourcentage de réalisation par type de structure

- **ID:** 2912
- **Thème:** etp-effectifs
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT "public"."suivi_realisation_convention_mensuelle"."type_structure" AS "type_structure", CAST(SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION), 0.0) AS "% de réalisation" 
FROM "public"."suivi_realisation_convention_mensuelle" 
GROUP BY "public"."suivi_realisation_convention_mensuelle"."type_structure" 
ORDER BY "public"."suivi_realisation_convention_mensuelle"."type_structure" ASC
```

## [287] Pourcentage de réalisation

- **ID:** 2913
- **Thème:** etp-effectifs
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT CAST(SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION), 0.0) AS "% de réalisation" 
FROM "public"."suivi_realisation_convention_mensuelle"
```

## [287] Suivi mensuel des effectifs mensuels conventionnés et réalisés + réalisation

- **ID:** 2922
- **Thème:** etp-effectifs
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") AS "af_date_fin_effet_v2", SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS "Effectif mensuel réalisé (en ETP)", SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS "Effectif mensuel conventionné (en ETP)", CAST(SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION), 0.0) AS "% de réalisation" 
FROM "public"."suivi_realisation_convention_mensuelle" 
GROUP BY DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") 
ORDER BY DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") ASC
```

## [287] Distribution du nombre d'ETP surconsommés

- **ID:** 2928
- **Thème:** etp-effectifs
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
- **Thème:** etp-effectifs
- **Tables:** suivi_realisation_convention_par_structure

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."suivi_realisation_convention_par_structure" 
WHERE ("public"."suivi_realisation_convention_par_structure"."delta_etp_conventionnes_realises" > 0) 
AND ("public"."suivi_realisation_convention_par_structure"."emi_esm_etat_code" = 'VALIDE')
```

## [287] Pourcentage de réalisation (états mensuels validés)

- **ID:** 2930
- **Thème:** etp-effectifs
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT CAST(SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION), 0.0) AS "% de réalisation" 
FROM "public"."suivi_realisation_convention_mensuelle" 
WHERE "public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" = 'VALIDE'
```

## [287] Nombre de structures

- **ID:** 2931
- **Thème:** etp-effectifs
- **Tables:** suivi_realisation_convention_par_structure

```sql
SELECT count(distinct "public"."suivi_realisation_convention_par_structure"."id_annexe_financiere") AS "count" 
FROM "public"."suivi_realisation_convention_par_structure"
```

## [287] Suivi du remplissage des états mensuels

- **ID:** 2932
- **Thème:** controles
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT "public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" AS "emi_esm_etat_code", DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") AS "af_date_fin_effet_v2", COUNT(*) AS "count" 
FROM "public"."suivi_realisation_convention_mensuelle" 
GROUP BY "public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code", DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") 
ORDER BY "public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" ASC, DATE_TRUNC('month', "public"."suivi_realisation_convention_mensuelle"."af_date_fin_effet_v2") ASC
```

## [287] Pourcentage de réalisation par type de structure (états mensuels validés)

- **ID:** 2933
- **Thème:** etp-effectifs
- **Tables:** suivi_realisation_convention_mensuelle

```sql
SELECT "public"."suivi_realisation_convention_mensuelle"."type_structure" AS "type_structure", CAST(SUM("public"."suivi_realisation_convention_mensuelle"."nombre_etp_consommes_reels_mensuels") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."suivi_realisation_convention_mensuelle"."effectif_mensuel_conventionné") AS DOUBLE PRECISION), 0.0) AS "% de réalisation" 
FROM "public"."suivi_realisation_convention_mensuelle" 
WHERE "public"."suivi_realisation_convention_mensuelle"."emi_esm_etat_code" = 'VALIDE' 
GROUP BY "public"."suivi_realisation_convention_mensuelle"."type_structure" 
ORDER BY "public"."suivi_realisation_convention_mensuelle"."type_structure" ASC
```

## [287] Etats mensuels non validés et ETP conventionnés

- **ID:** 3654
- **Thème:** controles
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
- **Thème:** controles
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
