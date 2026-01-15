# Thème : controles

*Control and compliance*

**9 cartes**

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

## [265] Etat contrôle critères

- **ID:** 2140
- **Dashboard:** 32
- **Tables:** suivi_cap_criteres

```sql
SELECT "public"."suivi_cap_criteres"."nom_critère" AS "nom_critère", "public"."suivi_cap_criteres"."état" AS "état", COUNT(*) AS "count" 
FROM "public"."suivi_cap_criteres" 
GROUP BY "public"."suivi_cap_criteres"."nom_critère", "public"."suivi_cap_criteres"."état" 
ORDER BY "public"."suivi_cap_criteres"."nom_critère" ASC, "public"."suivi_cap_criteres"."état" ASC
```

## [265] description critères refusés

- **ID:** 2179
- **Dashboard:** 32
- **Tables:** suivi_cap_criteres

```sql
SELECT "public"."suivi_cap_criteres"."nom_critère" AS "nom_critère", COUNT(*) AS "count" 
FROM "public"."suivi_cap_criteres" 
WHERE "public"."suivi_cap_criteres"."état" = 'Refusé' 
GROUP BY "public"."suivi_cap_criteres"."nom_critère" 
ORDER BY "public"."suivi_cap_criteres"."nom_critère" ASC
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
