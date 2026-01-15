# Dashboard : Candidatures - Traitement et résultats des candidatures émises

**URL:** /tableaux-de-bord/etat-suivi-candidatures/

**18 cartes**

## [116]Profil des candidats embauchés

- **ID:** 821
- **Thème:** demographie
- **Tables:** candidats

```sql
SELECT DATE_TRUNC('month', CAST("source"."date_diagnostic" AS timestamp)) AS "date_diagnostic", "source"."pivot-grouping" AS "pivot-grouping", CAST(SUM(CASE WHEN "source"."critère_n1_bénéficiaire_du_rsa" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression", CAST(SUM(CASE WHEN "source"."critère_n1_detld_plus_de_24_mois" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression_2", CAST(SUM(CASE WHEN "source"."critère_n2_deld_12_à_24_mois" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression_3", CAST(SUM(CASE WHEN "source"."critère_n2_jeune_moins_de_26_ans" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression_4", CAST(SUM(CASE WHEN "source"."critère_n2_résident_qpv" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression_5" 
FROM (SELECT "public"."candidats"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidats"."critère_n1_detld_plus_de_24_mois" AS "critère_n1_detld_plus_de_24_mois", "public"."candidats"."critère_n2_deld_12_à_24_mois" AS "critère_n2_deld_12_à_24_mois", "public"."candidats"."critère_n2_jeune_moins_de_26_ans" AS "critère_n2_jeune_moins_de_26_ans", "public"."candidats"."critère_n2_résident_qpv" AS "critère_n2_résident_qpv", "public"."candidats"."date_diagnostic" AS "date_diagnostic", ABS(0) AS "pivot-grouping" 
FROM "public"."candidats" 
WHERE (("public"."candidats"."total_embauches" <> 0) 
OR ("public"."candidats"."total_embauches" IS NULL)) 
AND (("public"."candidats"."type_structure_dernière_embauche" = 'ACI') 
OR ("public"."candidats"."type_structure_dernière_embauche" = 'AI') 
OR ("public"."candidats"."type_structure_dernière_embauche" = 'EI') 
OR ("public"."candidats"."type_structure_dernière_embauche" = 'EITI') 
OR ("public"."candidats"."type_structure_dernière_embauche" = 'ETTI'))) AS "source" 
GROUP BY DATE_TRUNC('month', CAST("source"."date_diagnostic" AS timestamp)), "source"."pivot-grouping" 
ORDER BY DATE_TRUNC('month', CAST("source"."date_diagnostic" AS timestamp)) ASC, "source"."pivot-grouping" ASC
```

## [116]Etat des candidatures par métier sur les 3 derniers mois

- **ID:** 823
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale, fiches_de_poste, fiches_de_poste_par_candidature, structures

```sql
SELECT "source"."Métier" AS "Métier", COUNT(*) AS "count", CAST(SUM(CASE WHEN "source"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures acceptées", CAST(SUM(CASE WHEN "source"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures refusées" 
FROM (SELECT "public"."candidatures_echelle_locale"."état" AS "état", CONCAT("Fiches De Poste"."code_rome", ' - ', "Fiches De Poste"."nom_rome") AS "Métier" 
FROM "public"."candidatures_echelle_locale" LEFT 
JOIN (SELECT "public"."fiches_de_poste_par_candidature"."id_fiche_de_poste" AS "id_fiche_de_poste", "public"."fiches_de_poste_par_candidature"."id_candidature" AS "id_candidature", "public"."fiches_de_poste_par_candidature"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" 
FROM "public"."fiches_de_poste_par_candidature") AS "Fiches De Poste Par Candidature" ON "public"."candidatures_echelle_locale"."id" = "Fiches De Poste Par Candidature"."id_candidature" LEFT 
JOIN (SELECT "public"."fiches_de_poste"."id" AS "id", "public"."fiches_de_poste"."code_rome" AS "code_rome", "public"."fiches_de_poste"."nom_rome" AS "nom_rome", "public"."fiches_de_poste"."recrutement_ouvert" AS "recrutement_ouvert", "public"."fiches_de_poste"."type_contrat" AS "type_contrat", "public"."fiches_de_poste"."id_employeur" AS "id_employeur", "public"."fiches_de_poste"."type_employeur" AS "type_employeur", "public"."fiches_de_poste"."siret_employeur" AS "siret_employeur", "public"."fiches_de_poste"."nom_employeur" AS "nom_employeur", "public"."fiches_de_poste"."mises_a_jour_champs" AS "mises_a_jour_champs", "public"."fiches_de_poste"."département_employeur" AS "département_employeur", "public"."fiches_de_poste"."nom_département_employeur" AS "nom_département_employeur", "public"."fiches_de_poste"."région_employeur" AS "région_employeur", "public"."fiches_de_poste"."total_candidatures" AS "total_candidatures", "public"."fiches_de_poste"."date_création" AS "date_création", "public"."fiches_de_poste"."date_dernière_modification" AS "date_dernière_modification", "public"."fiches_de_poste"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" 
FROM "public"."fiches_de_poste") AS "Fiches De Poste" ON "Fiches De Poste Par Candidature"."id_fiche_de_poste" = "Fiches De Poste"."id" LEFT 
JOIN (SELECT "public"."structures"."id" AS "id", "public"."structures"."id_asp" AS "id_asp", "public"."structures"."nom" AS "nom", "public"."structures"."nom_complet" AS "nom_complet", "public"."structures"."description" AS "description", "public"."structures"."type" AS "type", "public"."structures"."siret" AS "siret", "public"."structures"."code_naf" AS "code_naf", "public"."structures"."email_public" AS "email_public", "public"."structures"."email_authentification" AS "email_authentification", "public"."structures"."convergence_france" AS "convergence_france", "p
-- ... (truncated)
```

## [116] Taux de refus des structures

- **ID:** 997
- **Thème:** employeurs
- **Tables:** tx_refus_siae

```sql
SELECT "public"."tx_refus_siae"."type_structure" AS "type_structure", CAST(SUM("public"."tx_refus_siae"."nombre_candidatures_refusees") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."tx_refus_siae"."nombre_candidatures") AS DOUBLE PRECISION), 0.0) AS "Taux de refus", SUM("public"."tx_refus_siae"."nombre_candidatures") AS "Nombre de candidatures", SUM("public"."tx_refus_siae"."nombre_fiches_poste_ouvertes") AS "Nombre de postes ouverts", SUM("public"."tx_refus_siae"."nombre_siae") AS "Nombre de SIAE", SUM("public"."tx_refus_siae"."nombre_candidatures") - SUM("public"."tx_refus_siae"."nombre_candidatures_employeurs") AS "Nombre de candidatures hors auto-prescription", CAST(SUM("public"."tx_refus_siae"."nb_candidatures_refusees_non_emises_par_employeur_siae") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."tx_refus_siae"."nombre_candidatures") - SUM("public"."tx_refus_siae"."nombre_candidatures_employeurs") AS DOUBLE PRECISION), 0.0) AS "Taux de refus hors auto-prescription" 
FROM "public"."tx_refus_siae" 
GROUP BY "public"."tx_refus_siae"."type_structure" 
ORDER BY "public"."tx_refus_siae"."type_structure" ASC
```

## [116] Evolution des candidatures sur les 12 derniers mois, par état - échelle locale

- **ID:** 1391
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."état" AS "état", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non' 
GROUP BY "public"."candidatures_echelle_locale"."état", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."état" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## [116] Evolution des candidatures sur les 12 derniers mois, par origine - échelle locale

- **ID:** 1392
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine" AS "origine", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."injection_ai" = 0) 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
GROUP BY "public"."candidatures_echelle_locale"."origine", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."origine" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## [116] Evolution des candidatures acceptées sur les 12 derniers mois, par type d'employeur - échelle locale

- **ID:** 1393
- **Thème:** employeurs
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) AS "date_embauche", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
GROUP BY "public"."candidatures_echelle_locale"."type_structure", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) 
ORDER BY "count" DESC, "public"."candidatures_echelle_locale"."type_structure" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) ASC
```

## [116] Evolution des candidatures, par type d'orienteur - échelle locale

- **ID:** 1394
- **Thème:** prescripteurs
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine" AS "origine", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) AS "date_embauche", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
GROUP BY "public"."candidatures_echelle_locale"."origine", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."origine" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) ASC
```

## [116] Etat des candidatures par domaine professionnel sur les 12 derniers mois - échelle locale

- **ID:** 1395
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale, code_rome_domaine_professionnel, fiches_de_poste, fiches_de_poste_par_candidature

```sql
SELECT "source"."Métier" AS "Métier", count(distinct "source"."id") AS "Nombre de candidatures", CAST(SUM(CASE WHEN "source"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures acceptées", CAST(SUM(CASE WHEN "source"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures refusées" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."état" AS "état", "Code Rome Domaine Professionnel"."domaine_professionnel" AS "Métier" 
FROM "public"."candidatures_echelle_locale" LEFT 
JOIN (SELECT "public"."fiches_de_poste_par_candidature"."id_fiche_de_poste" AS "id_fiche_de_poste", "public"."fiches_de_poste_par_candidature"."id_candidature" AS "id_candidature", "public"."fiches_de_poste_par_candidature"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" 
FROM "public"."fiches_de_poste_par_candidature") AS "Fiches De Poste Par Candidature" ON "public"."candidatures_echelle_locale"."id" = "Fiches De Poste Par Candidature"."id_candidature" LEFT 
JOIN (SELECT "public"."fiches_de_poste"."id" AS "id", "public"."fiches_de_poste"."code_rome" AS "code_rome", "public"."fiches_de_poste"."nom_rome" AS "nom_rome", "public"."fiches_de_poste"."recrutement_ouvert" AS "recrutement_ouvert", "public"."fiches_de_poste"."type_contrat" AS "type_contrat", "public"."fiches_de_poste"."id_employeur" AS "id_employeur", "public"."fiches_de_poste"."type_employeur" AS "type_employeur", "public"."fiches_de_poste"."siret_employeur" AS "siret_employeur", "public"."fiches_de_poste"."nom_employeur" AS "nom_employeur", "public"."fiches_de_poste"."mises_a_jour_champs" AS "mises_a_jour_champs", "public"."fiches_de_poste"."département_employeur" AS "département_employeur", "public"."fiches_de_poste"."nom_département_employeur" AS "nom_département_employeur", "public"."fiches_de_poste"."région_employeur" AS "région_employeur", "public"."fiches_de_poste"."total_candidatures" AS "total_candidatures", "public"."fiches_de_poste"."date_création" AS "date_création", "public"."fiches_de_poste"."date_dernière_modification" AS "date_dernière_modification", "public"."fiches_de_poste"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" 
FROM "public"."fiches_de_poste") AS "Fiches De Poste" ON "Fiches De Poste Par Candidature"."id_fiche_de_poste" = "Fiches De Poste"."id" LEFT 
JOIN (SELECT "public"."code_rome_domaine_professionnel"."grand_domaine" AS "grand_domaine", "public"."code_rome_domaine_professionnel"."domaine_professionnel" AS "domaine_professionnel", "public"."code_rome_domaine_professionnel"."code_rome" AS "code_rome", "public"."code_rome_domaine_professionnel"."description_code_rome" AS "description_code_rome", "public"."code_rome_domaine_professionnel"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" 
FROM "public"."code_rome_domaine_professi
-- ... (truncated)
```

## [116]Motifs de refus des candidatures par type de prescripteurs - échelle locale

- **ID:** 1398
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine_détaillée" AS "origine_détaillée", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures acceptées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures refusées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Embauche incompatible avec les objectifs du dialogue de gestion' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Embauche incompatible avec les objectifs du dialogu_bc7feb62", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Candidat non joignable' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Candidat non joignable", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Pas de recrutement en cours' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Pas de recrutement en cours", SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS "Nombre de candidatures refusées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Candidat indisponible (en formation)' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Candidat indisponible (en formation)", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Candidat indisponible (en emploi)' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Candidat indisponible (en emploi)", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Autre motif saisi sur les emplois de l''inclusion' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Autre motif saisi sur les emplois de l'inclusion", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Candidature en doublon' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidatur
-- ... (truncated)
```

## [116] Nombre total de candidatures

- **ID:** 1468
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non'
```

## [116] Taux candidatures acceptées

- **ID:** 1469
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non'
```

## [116] Taux candidatures déclinées

- **ID:** 1470
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures déclinées" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non'
```

## [116] Motifs de refus actualisés (mensuel)

- **ID:** 1569
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale, structures

```sql
SELECT "public"."candidatures_echelle_locale"."motif_de_refus" AS "motif_de_refus", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" LEFT 
JOIN (SELECT "public"."structures"."id" AS "id", "public"."structures"."id_asp" AS "id_asp", "public"."structures"."nom" AS "nom", "public"."structures"."nom_complet" AS "nom_complet", "public"."structures"."description" AS "description", "public"."structures"."type" AS "type", "public"."structures"."siret" AS "siret", "public"."structures"."code_naf" AS "code_naf", "public"."structures"."email_public" AS "email_public", "public"."structures"."email_authentification" AS "email_authentification", "public"."structures"."convergence_france" AS "convergence_france", "public"."structures"."adresse_ligne_1" AS "adresse_ligne_1", "public"."structures"."adresse_ligne_2" AS "adresse_ligne_2", "public"."structures"."code_postal" AS "code_postal", "public"."structures"."code_commune" AS "code_commune", "public"."structures"."longitude" AS "longitude", "public"."structures"."latitude" AS "latitude", "public"."structures"."département" AS "département", "public"."structures"."nom_département" AS "nom_département", "public"."structures"."région" AS "région", "public"."structures"."adresse_ligne_1_c1" AS "adresse_ligne_1_c1", "public"."structures"."adresse_ligne_2_c1" AS "adresse_ligne_2_c1", "public"."structures"."code_postal_c1" AS "code_postal_c1", "public"."structures"."code_commune_c1" AS "code_commune_c1", "public"."structures"."ville_c1" AS "ville_c1", "public"."structures"."longitude_c1" AS "longitude_c1", "public"."structures"."latitude_c1" AS "latitude_c1", "public"."structures"."département_c1" AS "département_c1", "public"."structures"."nom_département_c1" AS "nom_département_c1", "public"."structures"."région_c1" AS "région_c1", "public"."structures"."date_inscription" AS "date_inscription", "public"."structures"."total_membres" AS "total_membres", "public"."structures"."total_candidatures" AS "total_candidatures", "public"."structures"."total_candidatures_30j" AS "total_candidatures_30j", "public"."structures"."total_embauches" AS "total_embauches", "public"."structures"."total_embauches_30j" AS "total_embauches_30j", "public"."structures"."taux_conversion_30j" AS "taux_conversion_30j", "public"."structures"."total_auto_prescriptions" AS "total_auto_prescriptions", "public"."structures"."total_candidatures_autonomes" AS "total_candidatures_autonomes", "public"."structures"."total_candidatures_via_prescripteur" AS "total_candidatures_via_prescripteur", "public"."structures"."total_candidatures_non_traitées" AS "total_candidatures_non_traitées", "public"."structures"."total_candidatures_en_étude" AS "total_candidatures_en_étude", "public"."structures"."date_dernière_connexion" AS "date_dernière_connexion", "public"."structures"."active" AS "active", "public"."structures"."date_derniè
-- ... (truncated)
```

## [185] Repartition des motifs de refus

- **ID:** 2490
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."motif_de_refus" AS "motif_de_refus", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature refusée') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."motif_de_refus" IS NOT NULL) 
AND (("public"."candidatures_echelle_locale"."motif_de_refus" <> '') 
OR ("public"."candidatures_echelle_locale"."motif_de_refus" IS NULL))) 
GROUP BY "public"."candidatures_echelle_locale"."motif_de_refus" 
ORDER BY "count" DESC, "public"."candidatures_echelle_locale"."motif_de_refus" ASC
```

## [116] Pourcentage de candidatures acceptées par type de prescripteur v2

- **ID:** 2508
- **Thème:** prescripteurs
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine_détaillée" AS "origine_détaillée", COUNT(*) AS "count", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures acceptées" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non' 
GROUP BY "public"."candidatures_echelle_locale"."origine_détaillée" 
ORDER BY "count" DESC, "public"."candidatures_echelle_locale"."origine_détaillée" ASC
```

## [116] Nombre total de candidatures en cours

- **ID:** 3525
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."état" = 'Candidature à l''étude') 
OR ("public"."candidatures_echelle_locale"."état" = 'Candidature en attente') 
OR ("public"."candidatures_echelle_locale"."état" = 'Nouvelle candidature')) 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non')
```

## Evolution candidatures annuelles SIAE

- **ID:** 4486
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."état" AS "état", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."date_candidature" > date '2021-01-01' 
GROUP BY "public"."candidatures_echelle_locale"."état", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."état" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## [116] Evolution annuelle des candidatures, par origine

- **ID:** 4503
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine" AS "origine", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."date_candidature" > date '2021-01-01') 
AND ("public"."candidatures_echelle_locale"."injection_ai" = 0) 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
GROUP BY "public"."candidatures_echelle_locale"."origine", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."origine" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```
