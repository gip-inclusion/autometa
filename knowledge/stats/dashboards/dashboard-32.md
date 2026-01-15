# Dashboard :  Candidatures - Activité d’auto-prescription et de contrôle à posteriori

**URL:** /tableaux-de-bord/auto-prescription/

**21 cartes**

## [267] Candidatures acceptées en auto prescription

- **ID:** 1997
- **Thème:** auto-prescription
- **Tables:** suivi_auto_prescription

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

## [267] % Embauches en auto prescription

- **ID:** 1998
- **Thème:** auto-prescription
- **Tables:** suivi_auto_prescription

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

## [267] Evolution du taux d'auto presciption dans le temps

- **ID:** 1999
- **Thème:** auto-prescription
- **Tables:** suivi_auto_prescription

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

## [267] Nombre de SIAE pratiquant l'auto prescription

- **ID:** 2006
- **Thème:** auto-prescription
- **Tables:** siae_pratiquant_autoprescription

```sql
SELECT SUM("public"."siae_pratiquant_autoprescription"."Nombre de structures utilisant l'autoprescription") AS "sum" 
FROM "public"."siae_pratiquant_autoprescription"
```

## [267] Nombre total de SIAE

- **ID:** 2007
- **Thème:** auto-prescription
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
- **Thème:** auto-prescription
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

## [267] Taux d'auto presciption par type de structure

- **ID:** 2009
- **Thème:** auto-prescription
- **Tables:** suivi_auto_prescription

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

## [265] part SIAE ctrlées pos vs neg

- **ID:** 2017
- **Thème:** controles
- **Tables:** cap_campagnes, cap_structures, structures

```sql
SELECT "source"."état" AS "état", COUNT(*) AS "count" 
FROM (SELECT CASE WHEN "public"."cap_structures"."état" = 'ACCEPTED' THEN 'Résultats positifs' WHEN "public"."cap_structures"."état" = 'REFUSED' THEN 'Résultats négatifs' WHEN "public"."cap_structures"."état" = 'NOTIFICATION_PENDING' THEN 'Résultats négatifs' END AS "état" 
FROM "public"."cap_structures" LEFT 
JOIN (SELECT "public"."structures"."id" AS "id", "public"."structures"."id_asp" AS "id_asp", "public"."structures"."nom" AS "nom", "public"."structures"."nom_complet" AS "nom_complet", "public"."structures"."description" AS "description", "public"."structures"."type" AS "type", "public"."structures"."siret" AS "siret", "public"."structures"."code_naf" AS "code_naf", "public"."structures"."email_public" AS "email_public", "public"."structures"."email_authentification" AS "email_authentification", "public"."structures"."convergence_france" AS "convergence_france", "public"."structures"."adresse_ligne_1" AS "adresse_ligne_1", "public"."structures"."adresse_ligne_2" AS "adresse_ligne_2", "public"."structures"."code_postal" AS "code_postal", "public"."structures"."code_commune" AS "code_commune", "public"."structures"."longitude" AS "longitude", "public"."structures"."latitude" AS "latitude", "public"."structures"."département" AS "département", "public"."structures"."nom_département" AS "nom_département", "public"."structures"."région" AS "région", "public"."structures"."adresse_ligne_1_c1" AS "adresse_ligne_1_c1", "public"."structures"."adresse_ligne_2_c1" AS "adresse_ligne_2_c1", "public"."structures"."code_postal_c1" AS "code_postal_c1", "public"."structures"."code_commune_c1" AS "code_commune_c1", "public"."structures"."ville_c1" AS "ville_c1", "public"."structures"."longitude_c1" AS "longitude_c1", "public"."structures"."latitude_c1" AS "latitude_c1", "public"."structures"."département_c1" AS "département_c1", "public"."structures"."nom_département_c1" AS "nom_département_c1", "public"."structures"."région_c1" AS "région_c1", "public"."structures"."date_inscription" AS "date_inscription", "public"."structures"."total_membres" AS "total_membres", "public"."structures"."total_candidatures" AS "total_candidatures", "public"."structures"."total_candidatures_30j" AS "total_candidatures_30j", "public"."structures"."total_embauches" AS "total_embauches", "public"."structures"."total_embauches_30j" AS "total_embauches_30j", "public"."structures"."taux_conversion_30j" AS "taux_conversion_30j", "public"."structures"."total_auto_prescriptions" AS "total_auto_prescriptions", "public"."structures"."total_candidatures_autonomes" AS "total_candidatures_autonomes", "public"."structures"."total_candidatures_via_prescripteur" AS "total_candidatures_via_prescripteur", "public"."structures"."total_candidatures_non_traitées" AS "total_candidatures_non_traitées", "public"."structures"."total_candidatures_en_étude" AS "total_candidatures_en_étude", "public"."structures"."date_dernière_connexion" AS "date_der
-- ... (truncated)
```

## [267] Nombre candidats concernés auto-prescription

- **ID:** 2025
- **Thème:** auto-prescription
- **Tables:** candidats_auto_prescription

```sql
SELECT COUNT(*) AS "Candidats concernés par l'auto-prescription" 
FROM "public"."candidats_auto_prescription" 
WHERE ((("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") <> 0) 
OR (("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") IS NULL)) 
AND ("public"."candidats_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."candidats_auto_prescription"."type_de_candidature" = 'Autoprescription')
```

## [267] Nombre de personnes recrutées en autoprescription critères niv 1

- **ID:** 2027
- **Thème:** auto-prescription
- **Tables:** candidats_auto_prescription

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

## [267] Détails critère de niveau 1

- **ID:** 2028
- **Thème:** auto-prescription
- **Tables:** candidats_auto_prescription

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

- **ID:** 2029
- **Thème:** auto-prescription
- **Tables:** candidats_auto_prescription

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

## [267] Nombre de personnes recrutées en autoprescription critères niv 2

- **ID:** 2030
- **Thème:** auto-prescription
- **Tables:** candidats_auto_prescription

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."candidats_auto_prescription" 
WHERE ((("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") <> 0) 
OR (("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") IS NULL)) 
AND ("public"."candidats_auto_prescription"."total_critères_niveau_1" = 0) 
AND ("public"."candidats_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."candidats_auto_prescription"."type_de_candidature" = 'Autoprescription')
```

## [267] Détails critère de niveau 2

- **ID:** 2032
- **Thème:** auto-prescription

## [265] Etat contrôle critères

- **ID:** 2140
- **Thème:** controles
- **Tables:** suivi_cap_criteres

```sql
SELECT "public"."suivi_cap_criteres"."nom_critère" AS "nom_critère", "public"."suivi_cap_criteres"."état" AS "état", COUNT(*) AS "count" 
FROM "public"."suivi_cap_criteres" 
GROUP BY "public"."suivi_cap_criteres"."nom_critère", "public"."suivi_cap_criteres"."état" 
ORDER BY "public"."suivi_cap_criteres"."nom_critère" ASC, "public"."suivi_cap_criteres"."état" ASC
```

## [265] description critères refusés

- **ID:** 2179
- **Thème:** controles
- **Tables:** suivi_cap_criteres

```sql
SELECT "public"."suivi_cap_criteres"."nom_critère" AS "nom_critère", COUNT(*) AS "count" 
FROM "public"."suivi_cap_criteres" 
WHERE "public"."suivi_cap_criteres"."état" = 'Refusé' 
GROUP BY "public"."suivi_cap_criteres"."nom_critère" 
ORDER BY "public"."suivi_cap_criteres"."nom_critère" ASC
```

## [267] Candidatures acceptées (toutes)

- **ID:** 2280
- **Thème:** auto-prescription
- **Tables:** suivi_auto_prescription

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

## [265] Nb de structures dont le contrôle est terminé

- **ID:** 2291
- **Thème:** controles
- **Tables:** suivi_cap_structures

```sql
SELECT count(distinct "public"."suivi_cap_structures"."id_structure") AS "Nb structures contrôlées" 
FROM "public"."suivi_cap_structures" 
WHERE ("public"."suivi_cap_structures"."état" = 'ACCEPTED') 
OR ("public"."suivi_cap_structures"."état" = 'REFUSED')
```

## [267] Candidats - Nombre de critères de niveau 1 (w/ 0)

- **ID:** 2368
- **Thème:** auto-prescription
- **Tables:** candidats_auto_prescription

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

## [265] SIAE à contrôler

- **ID:** 2438
- **Thème:** controles
- **Tables:** cap_campagnes, cap_structures

```sql
SELECT count(distinct "public"."cap_structures"."id_structure") AS "structures à contrôler" 
FROM "public"."cap_structures" LEFT 
JOIN (SELECT "public"."cap_campagnes"."id" AS "id", "public"."cap_campagnes"."nom" AS "nom", "public"."cap_campagnes"."id_institution" AS "id_institution", "public"."cap_campagnes"."date_début" AS "date_début", "public"."cap_campagnes"."date_fin" AS "date_fin", "public"."cap_campagnes"."pourcentage_sélection" AS "pourcentage_sélection", "public"."cap_campagnes"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" 
FROM "public"."cap_campagnes") AS "Cap Campagnes" ON "public"."cap_structures"."id_cap_campagne" = "Cap Campagnes"."id"
```

## [265] % SIAE contrôlées parmi les SIAE à contrôler - v2

- **ID:** 5017
- **Thème:** controles
- **Tables:** cap_campagnes, cap_structures, suivi_cap_structures

```sql
SELECT CAST(count(distinct CASE WHEN "Suivi Cap Structures - ID Structure"."état" = 'ACCEPTED' THEN "public"."cap_structures"."id_structure" WHEN "Suivi Cap Structures - ID Structure"."état" = 'REFUSED' THEN "public"."cap_structures"."id_structure" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "public"."cap_structures"."id_structure") AS DOUBLE PRECISION), 0.0) AS "% ctrl terminés" 
FROM "public"."cap_structures" LEFT 
JOIN (SELECT "public"."cap_campagnes"."id" AS "id", "public"."cap_campagnes"."nom" AS "nom", "public"."cap_campagnes"."id_institution" AS "id_institution", "public"."cap_campagnes"."date_début" AS "date_début", "public"."cap_campagnes"."date_fin" AS "date_fin", "public"."cap_campagnes"."pourcentage_sélection" AS "pourcentage_sélection", "public"."cap_campagnes"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" 
FROM "public"."cap_campagnes") AS "Cap Campagnes - ID Cap Campagne" ON "public"."cap_structures"."id_cap_campagne" = "Cap Campagnes - ID Cap Campagne"."id" LEFT 
JOIN (SELECT "public"."suivi_cap_structures"."id_cap_campagne" AS "id_cap_campagne", "public"."suivi_cap_structures"."nom_campagne" AS "nom_campagne", "public"."suivi_cap_structures"."id_cap_structure" AS "id_cap_structure", "public"."suivi_cap_structures"."id_structure" AS "id_structure", "public"."suivi_cap_structures"."type" AS "type", "public"."suivi_cap_structures"."département" AS "département", "public"."suivi_cap_structures"."nom_département" AS "nom_département", "public"."suivi_cap_structures"."région" AS "région", "public"."suivi_cap_structures"."bassin_d_emploi" AS "bassin_d_emploi", "public"."suivi_cap_structures"."état" AS "état", "public"."suivi_cap_structures"."réponse_au_contrôle" AS "réponse_au_contrôle", "public"."suivi_cap_structures"."active" AS "active", "public"."suivi_cap_structures"."controlee" AS "controlee" 
FROM "public"."suivi_cap_structures") AS "Suivi Cap Structures - ID Structure" ON "public"."cap_structures"."id_structure" = "Suivi Cap Structures - ID Structure"."id_structure"
```
