# Thème : candidatures

*Candidature metrics, states, flows*

**51 cartes**

## [116]Etat des candidatures par métier sur les 3 derniers mois

- **ID:** 823
- **Dashboard:** 116
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

## [136] candidats orientés par les prescripteurs habilités acceptés en IAE sur les 3 derniers mois - prescripteurs

- **ID:** 1210
- **Dashboard:** 136
- **Tables:** candidatures, taux_transformation_prescripteurs

```sql
SELECT count(distinct "public"."taux_transformation_prescripteurs"."id_candidat") AS "count" 
FROM "public"."taux_transformation_prescripteurs" LEFT 
JOIN (SELECT "public"."candidatures"."id" AS "id", "public"."candidatures"."candidature_archivee" AS "candidature_archivee", "public"."candidatures"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures"."date_candidature" AS "date_candidature", "public"."candidatures"."date_début_contrat" AS "date_début_contrat", "public"."candidatures"."date_traitement" AS "date_traitement", "public"."candidatures"."état" AS "état", "public"."candidatures"."origine" AS "origine", "public"."candidatures"."origine_détaillée" AS "origine_détaillée", "public"."candidatures"."origine_id_structure" AS "origine_id_structure", "public"."candidatures"."parcours_de_création" AS "parcours_de_création", "public"."candidatures"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures"."motif_de_refus" AS "motif_de_refus", "public"."candidatures"."id_candidat" AS "id_candidat", "public"."candidatures"."id_structure" AS "id_structure", "public"."candidatures"."type_structure" AS "type_structure", "public"."candidatures"."nom_structure" AS "nom_structure", "public"."candidatures"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures"."département_structure" AS "département_structure", "public"."candidatures"."nom_département_structure" AS "nom_département_structure", "public"."candidatures"."région_structure" AS "région_structure", "public"."candidatures"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures"."date_embauche" AS "date_embauche", "public"."candidatures"."injection_ai" AS "injection_ai", "public"."candidatures"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures"."type_contrat" AS "type_contrat", "public"."candidatures"."présence_de_cv" AS "présence_de_cv", "public"."candidatures"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" 
FROM "public"."candidatures") AS "Candidatures" ON "public"."taux_transformation_prescripteurs"."id_candidat" = "Candidatures"."id_candidat" 
WHERE ("public"."taux_transformation_prescripteurs"."date_diagnostic" IS NOT NULL) 
AND ("Candidatures"."date_embauche" IS NOT NULL)
```

## [116] Evolution des candidatures sur les 12 derniers mois, par état - échelle locale

- **ID:** 1391
- **Dashboard:** 116
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
- **Dashboard:** 116
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine" AS "origine", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."injection_ai" = 0) 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
GROUP BY "public"."candidatures_echelle_locale"."origine", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."origine" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## [116] Etat des candidatures par domaine professionnel sur les 12 derniers mois - échelle locale

- **ID:** 1395
- **Dashboard:** 116
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
- **Dashboard:** 116
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine_détaillée" AS "origine_détaillée", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures acceptées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures refusées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Embauche incompatible avec les objectifs du dialogue de gestion' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Embauche incompatible avec les objectifs du dialogu_bc7feb62", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Candidat non joignable' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Candidat non joignable", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Pas de recrutement en cours' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Pas de recrutement en cours", SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS "Nombre de candidatures refusées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Candidat indisponible (en formation)' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Candidat indisponible (en formation)", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Candidat indisponible (en emploi)' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Candidat indisponible (en emploi)", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Autre motif saisi sur les emplois de l''inclusion' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Autre motif saisi sur les emplois de l'inclusion", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Candidature en doublon' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidatur
-- ... (truncated)
```

## [116] Nombre total de candidatures

- **ID:** 1468
- **Dashboard:** 116
- **Tables:** candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non'
```

## [116] Taux candidatures acceptées

- **ID:** 1469
- **Dashboard:** 116
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non'
```

## [116] Taux candidatures déclinées

- **ID:** 1470
- **Dashboard:** 116
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures déclinées" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non'
```

## [116] Motifs de refus actualisés (mensuel)

- **ID:** 1569
- **Dashboard:** 116
- **Tables:** candidatures_echelle_locale, structures

```sql
SELECT "public"."candidatures_echelle_locale"."motif_de_refus" AS "motif_de_refus", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" LEFT 
JOIN (SELECT "public"."structures"."id" AS "id", "public"."structures"."id_asp" AS "id_asp", "public"."structures"."nom" AS "nom", "public"."structures"."nom_complet" AS "nom_complet", "public"."structures"."description" AS "description", "public"."structures"."type" AS "type", "public"."structures"."siret" AS "siret", "public"."structures"."code_naf" AS "code_naf", "public"."structures"."email_public" AS "email_public", "public"."structures"."email_authentification" AS "email_authentification", "public"."structures"."convergence_france" AS "convergence_france", "public"."structures"."adresse_ligne_1" AS "adresse_ligne_1", "public"."structures"."adresse_ligne_2" AS "adresse_ligne_2", "public"."structures"."code_postal" AS "code_postal", "public"."structures"."code_commune" AS "code_commune", "public"."structures"."longitude" AS "longitude", "public"."structures"."latitude" AS "latitude", "public"."structures"."département" AS "département", "public"."structures"."nom_département" AS "nom_département", "public"."structures"."région" AS "région", "public"."structures"."adresse_ligne_1_c1" AS "adresse_ligne_1_c1", "public"."structures"."adresse_ligne_2_c1" AS "adresse_ligne_2_c1", "public"."structures"."code_postal_c1" AS "code_postal_c1", "public"."structures"."code_commune_c1" AS "code_commune_c1", "public"."structures"."ville_c1" AS "ville_c1", "public"."structures"."longitude_c1" AS "longitude_c1", "public"."structures"."latitude_c1" AS "latitude_c1", "public"."structures"."département_c1" AS "département_c1", "public"."structures"."nom_département_c1" AS "nom_département_c1", "public"."structures"."région_c1" AS "région_c1", "public"."structures"."date_inscription" AS "date_inscription", "public"."structures"."total_membres" AS "total_membres", "public"."structures"."total_candidatures" AS "total_candidatures", "public"."structures"."total_candidatures_30j" AS "total_candidatures_30j", "public"."structures"."total_embauches" AS "total_embauches", "public"."structures"."total_embauches_30j" AS "total_embauches_30j", "public"."structures"."taux_conversion_30j" AS "taux_conversion_30j", "public"."structures"."total_auto_prescriptions" AS "total_auto_prescriptions", "public"."structures"."total_candidatures_autonomes" AS "total_candidatures_autonomes", "public"."structures"."total_candidatures_via_prescripteur" AS "total_candidatures_via_prescripteur", "public"."structures"."total_candidatures_non_traitées" AS "total_candidatures_non_traitées", "public"."structures"."total_candidatures_en_étude" AS "total_candidatures_en_étude", "public"."structures"."date_dernière_connexion" AS "date_dernière_connexion", "public"."structures"."active" AS "active", "public"."structures"."date_derniè
-- ... (truncated)
```

## [216] candidatures par métier

- **ID:** 2294
- **Dashboard:** 216
- **Tables:** metier_candidatures

```sql
SELECT "public"."metier_candidatures"."nom_rome" AS "nom_rome", CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de candidatures femmes émises", CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de candidatures hommes émises", CAST(SUM(CASE WHEN ("public"."metier_candidatures"."genre_candidat" = 'Femme') 
AND ("public"."metier_candidatures"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation des femmes", CAST(SUM(CASE WHEN ("public"."metier_candidatures"."genre_candidat" = 'Homme') 
AND ("public"."metier_candidatures"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation des hommes", COUNT(*) AS "Nombre de candidatures émises", SUM(CASE WHEN "public"."metier_candidatures"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS "Nombre de candidatures acceptées" 
FROM "public"."metier_candidatures" 
WHERE (("public"."metier_candidatures"."type_structure" = 'ACI') 
OR ("public"."metier_candidatures"."type_structure" = 'AI') 
OR ("public"."metier_candidatures"."type_structure" = 'EI') 
OR ("public"."metier_candidatures"."type_structure" = 'EITI') 
OR ("public"."metier_candidatures"."type_structure" = 'ETTI')) 
AND ("public"."metier_candidatures"."date_inscription_candidat" > date '2021-11-01') 
AND ("public"."metier_candidatures"."genre_candidat" IS NOT NULL) 
AND (("public"."metier_candidatures"."genre_candidat" <> '') 
OR ("public"."metier_candidatures"."genre_candidat" IS NULL)) 
GROUP BY "public"."metier_candidatures"."nom_rome" 
ORDER BY "public"."metier_candidatures"."nom_rome" ASC
```

## [216] candidatures par domaine

- **ID:** 2296
- **Dashboard:** 216
- **Tables:** metier_candidatures

```sql
SELECT "public"."metier_candidatures"."metier" AS "metier", CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de candidatures femmes émises", CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de candidatures hommes émises", CAST(SUM(CASE WHEN ("public"."metier_candidatures"."genre_candidat" = 'Femme') 
AND ("public"."metier_candidatures"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation des femmes", CAST(SUM(CASE WHEN ("public"."metier_candidatures"."genre_candidat" = 'Homme') 
AND ("public"."metier_candidatures"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation des hommes", COUNT(*) AS "Nombre de candidatures émises", SUM(CASE WHEN "public"."metier_candidatures"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS "Nombre de candidatures acceptées" 
FROM "public"."metier_candidatures" 
WHERE (("public"."metier_candidatures"."type_structure" = 'ACI') 
OR ("public"."metier_candidatures"."type_structure" = 'AI') 
OR ("public"."metier_candidatures"."type_structure" = 'EI') 
OR ("public"."metier_candidatures"."type_structure" = 'EITI') 
OR ("public"."metier_candidatures"."type_structure" = 'ETTI')) 
AND ("public"."metier_candidatures"."date_inscription_candidat" > date '2021-11-01') 
AND (("public"."metier_candidatures"."genre_candidat" = 'Femme') 
OR ("public"."metier_candidatures"."genre_candidat" = 'Homme')) 
GROUP BY "public"."metier_candidatures"."metier" 
ORDER BY "public"."metier_candidatures"."metier" ASC
```

## [185] Repartition des motifs de refus

- **ID:** 2490
- **Dashboard:** 116
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

## Evolution annuelle du taux de candidatures acceptées et refusées à partir de 2021

- **ID:** 3510
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures refusées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
GROUP BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## Evolution annuelle des candidatures orientées par type de SIAE

- **ID:** 3511
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND (("public"."candidatures_echelle_locale"."type_prescripteur" = 'Autre') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Département') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Nouveaux prescripteurs') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE')) 
GROUP BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date), "public"."candidatures_echelle_locale"."type_structure" 
ORDER BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC, "public"."candidatures_echelle_locale"."type_structure" ASC
```

## [116] Nombre total de candidatures en cours

- **ID:** 3525
- **Dashboard:** 116
- **Tables:** candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."état" = 'Candidature à l''étude') 
OR ("public"."candidatures_echelle_locale"."état" = 'Candidature en attente') 
OR ("public"."candidatures_echelle_locale"."état" = 'Nouvelle candidature')) 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non')
```

## Candidatures toujours en cours de traitement

- **ID:** 3643
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", "public"."candidatures_echelle_locale"."origine" AS "origine", count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."état" = 'Candidature à l''étude') 
OR ("public"."candidatures_echelle_locale"."état" = 'Candidature en attente') 
OR ("public"."candidatures_echelle_locale"."état" = 'Nouvelle candidature')) 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
GROUP BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date), "public"."candidatures_echelle_locale"."origine" 
ORDER BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC, "public"."candidatures_echelle_locale"."origine" ASC
```

## Taux d'acceptation et refus des prescriptions

- **ID:** 3680
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures refusées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."candidatures_echelle_locale"."type_prescripteur" = 'Autre') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Département') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Nouveaux prescripteurs') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE')) 
GROUP BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## Taux de candidatures refusées par les SIAE en 2023

- **ID:** 3685
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures refusées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-1 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Taux de candidatures acceptées par les SIAE en 2023

- **ID:** 3686
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-1 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Nombre de candidatures acceptées en 2023

- **ID:** 3695
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-1 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Nombre de candidatures en cours de traitement en 2023

- **ID:** 3709
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."état" = 'Candidature à l''étude') 
OR ("public"."candidatures_echelle_locale"."état" = 'Candidature en attente') 
OR ("public"."candidatures_echelle_locale"."état" = 'Nouvelle candidature')) 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-1 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Motifs de refus sur 2024

- **ID:** 3828
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."motif_de_refus" AS "motif_de_refus", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND ("public"."candidatures_echelle_locale"."état" = 'Candidature refusée') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2024-01-01' 
AND date '2024-12-31' 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
GROUP BY "public"."candidatures_echelle_locale"."motif_de_refus" 
ORDER BY "count" DESC, "public"."candidatures_echelle_locale"."motif_de_refus" ASC
```

## Nombre de candidatures acceptées en 2024

- **ID:** 3865
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2024-01-01' 
AND date '2024-12-31' 
AND ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Taux de candidatures acceptées par les SIAE en 2024

- **ID:** 3866
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2024-01-01' 
AND date '2024-12-31' 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Nombre de candidatures en attente d'être clôturée sur 2024

- **ID:** 3867
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."état" = 'Candidature à l''étude') 
OR ("public"."candidatures_echelle_locale"."état" = 'Candidature en attente') 
OR ("public"."candidatures_echelle_locale"."état" = 'Nouvelle candidature')) 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2024-01-01' 
AND date '2024-12-31' 
AND ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Taux de candidatures refusées par les SIAE en 2024

- **ID:** 3868
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures refusées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2024-01-01' 
AND date '2024-12-31' 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Répartition des orientations par type de SIAE

- **ID:** 3873
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND ("public"."candidatures_echelle_locale"."injection_ai" = 0) 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
GROUP BY "public"."candidatures_echelle_locale"."type_structure", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."type_structure" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## Taux d'acceptation et refus des prescriptions par type de SIAE en 2023

- **ID:** 3875
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures refusées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-1 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."candidatures_echelle_locale"."type_prescripteur" = 'Autre') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Département') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Nouveaux prescripteurs') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE')) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
GROUP BY "public"."candidatures_echelle_locale"."type_structure" 
ORDER BY "public"."candidatures_echelle_locale"."type_structure" ASC
```

## Taux d'acceptation et refus des prescriptions par type de SIAE en 2024

- **ID:** 3876
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures refusées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2024-01-01' 
AND date '2024-12-31' 
AND (("public"."candidatures_echelle_locale"."type_prescripteur" = 'Autre') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Département') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Nouveaux prescripteurs') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE')) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND ("public"."candidatures_echelle_locale"."région_structure" = 'Nouvelle-Aquitaine') 
GROUP BY "public"."candidatures_echelle_locale"."type_structure" 
ORDER BY "public"."candidatures_echelle_locale"."type_structure" ASC
```

## [408] répartition des motifs de refus par type de SIAE

- **ID:** 4293
- **Dashboard:** 408
- **Tables:** candidats_recherche_active, candidatures_candidats_recherche_active

```sql
SELECT "source"."type_structure" AS "type_structure", COUNT(*) AS "count", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat non joignable' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat non joignable", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Pas de recrutement en cours' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Pas de recrutement en cours", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Freins à l''emploi incompatible avec le poste proposé' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Un des freins à l'emploi du candidat est incompati_4d898484", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat ne s’étant pas présenté à l’entretien' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat ne s’étant pas présenté à l’entretien", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat non éligible' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat non éligible", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat non intéressé' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat non intéressé", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat indisponible (en emploi)' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat indisponible : en emploi", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Embauche incompatible avec les objectifs du dialogue de gestion' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Embauche incompatible avec les objectifs du dialogu_bc7feb62", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Compétences insuffisantes pour le poste' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Le candidat n’a pas les compétences requises pou_b980daed", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat non mobile' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat non mobile", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidature en doublon' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidature en doublon", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat indisponible (en formation)' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat indisponible : en formation", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Autre motif saisi sur les emplois de l''inclusion' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Motif autre saisi sur les emplois" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "
-- ... (truncated)
```

## Evolution du nombre de candidatures acceptées les 6 derniers mois

- **ID:** 4316
- **Dashboard:** 408
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) AS "date_embauche", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND ("public"."candidatures_echelle_locale"."date_embauche" >= DATE_TRUNC('month', (NOW() + INTERVAL '-6 month'))) 
AND ("public"."candidatures_echelle_locale"."date_embauche" < DATE_TRUNC('month', NOW())) 
GROUP BY CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) 
ORDER BY CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) ASC
```

## [408] Nombre de candidats en recherche active qui ont émis leur première candidature il y a plus de 30 jours et n'ont aucune candidature acceptée aujd

- **ID:** 4413
- **Dashboard:** 408
- **Tables:** candidats_recherche_active, candidatures_candidats_recherche_active

```sql
SELECT count(distinct "source"."id") AS "count" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa_certifié" AS "c
-- ... (truncated)
```

## Evolution candidatures annuelles SIAE

- **ID:** 4486
- **Dashboard:** 116
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."état" AS "état", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE "public"."candidatures_echelle_locale"."date_candidature" > date '2021-01-01' 
GROUP BY "public"."candidatures_echelle_locale"."état", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."état" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## [408] Nombre de fdp ouvertes

- **ID:** 4493
- **Dashboard:** 408
- **Tables:** fiches_de_poste

```sql
SELECT COUNT(*) AS "count" 
FROM (SELECT "public"."fiches_de_poste"."id" AS "id", "public"."fiches_de_poste"."code_rome" AS "code_rome", "public"."fiches_de_poste"."nom_rome" AS "nom_rome", "public"."fiches_de_poste"."recrutement_ouvert" AS "recrutement_ouvert", "public"."fiches_de_poste"."type_contrat" AS "type_contrat", "public"."fiches_de_poste"."id_employeur" AS "id_employeur", "public"."fiches_de_poste"."type_employeur" AS "type_employeur", "public"."fiches_de_poste"."siret_employeur" AS "siret_employeur", "public"."fiches_de_poste"."nom_employeur" AS "nom_employeur", "public"."fiches_de_poste"."mises_a_jour_champs" AS "mises_a_jour_champs", "public"."fiches_de_poste"."département_employeur" AS "département_employeur", "public"."fiches_de_poste"."nom_département_employeur" AS "nom_département_employeur", "public"."fiches_de_poste"."région_employeur" AS "région_employeur", "public"."fiches_de_poste"."total_candidatures" AS "total_candidatures", "public"."fiches_de_poste"."date_création" AS "date_création", "public"."fiches_de_poste"."date_dernière_modification" AS "date_dernière_modification", "public"."fiches_de_poste"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" 
FROM "public"."fiches_de_poste") AS "source" 
WHERE ("source"."recrutement_ouvert" = 1) 
AND (("source"."type_employeur" = 'ACI') 
OR ("source"."type_employeur" = 'AI') 
OR ("source"."type_employeur" = 'EITI') 
OR ("source"."type_employeur" = 'EI') 
OR ("source"."type_employeur" = 'ETTI'))
```

## [116] Evolution annuelle des candidatures, par origine

- **ID:** 4503
- **Dashboard:** 116
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

## [408] Motifs de refus

- **ID:** 4532
- **Dashboard:** 408
- **Tables:** candidats_recherche_active, candidatures_candidats_recherche_active

```sql
SELECT "source"."MR" AS "MR", COUNT(*) AS "count" 
FROM (SELECT CASE WHEN "source"."motif_de_refus" = 'Autre' THEN 'Motif autre saisi sur les Emplois de l''Inclusion' ELSE "source"."motif_de_refus" END AS "MR" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critè
-- ... (truncated)
```

## [408] répartition des motifs de refus par origine

- **ID:** 4535
- **Dashboard:** 408
- **Tables:** candidats_recherche_active, candidatures_candidats_recherche_active

```sql
SELECT "source"."origine" AS "origine", COUNT(*) AS "count", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat non joignable' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat non joignable", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Pas de recrutement en cours' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Pas de recrutement en cours", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Freins à l''emploi incompatible avec le poste proposé' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Un des freins à l'emploi du candidat est incompati_4d898484", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat ne s’étant pas présenté à l’entretien' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat ne s’étant pas présenté à l’entretien", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat non éligible' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat non éligible", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat non intéressé' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat non intéressé", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat indisponible (en emploi)' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat indisponible : en emploi", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Embauche incompatible avec les objectifs du dialogue de gestion' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS " Embauche incompatible avec les objectifs du dialog_c6f6bccb", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Compétences insuffisantes pour le poste' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Le candidat n’a pas les compétences requises pou_b980daed", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat non mobile' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat non mobile", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidature en doublon' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidature en doublon", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat indisponible (en formation)' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat indisponible : en formation", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Autre motif saisi sur les emplois de l''inclusion' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Motif autre saisi sur les emplois" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candi
-- ... (truncated)
```

## [408] répartition des motifs de refus par origine détaillée

- **ID:** 4536
- **Dashboard:** 408
- **Tables:** candidats_recherche_active, candidatures_candidats_recherche_active

```sql
SELECT "source"."origine_détaillée" AS "origine_détaillée", COUNT(*) AS "count", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat non joignable' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat non joignable", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Pas de recrutement en cours' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Pas de recrutement en cours", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Freins à l''emploi incompatible avec le poste proposé' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Freins à l'emploi incompatible avec le poste proposé", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat ne s’étant pas présenté à l’entretien' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat ne s’étant pas présenté à l’entretien", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat non éligible' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat non éligible", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat non intéressé' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat non intéressé", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat indisponible (en emploi)' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat indisponible : en emploi", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Embauche incompatible avec les objectifs du dialogue de gestion' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Embauche incompatible avec les objectifs du dialogu_bc7feb62", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Compétences insuffisantes pour le poste' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Compétences insuffisantes pour le poste", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat non mobile' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat non mobile", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidature en doublon' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidature en doublon", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Candidat indisponible (en formation)' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Candidat indisponible : en formation", CAST(SUM(CASE WHEN "source"."motif_de_refus" = 'Autre motif saisi sur les emplois de l''inclusion' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Motif autre saisi sur les emplois" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatur
-- ... (truncated)
```

## [408] Candidatures en cours vs clôturée

- **ID:** 4538
- **Dashboard:** 408
- **Tables:** candidats_recherche_active, candidatures_candidats_recherche_active

```sql
SELECT "source"."refus_vs_encours" AS "refus_vs_encours", COUNT(*) AS "count" 
FROM (SELECT CASE WHEN "source"."état" = 'Candidature refusée' THEN 'Clôturée' WHEN "source"."état" = 'Embauché ailleurs' THEN 'Clôturée' WHEN "source"."état" = 'Embauche annulée' THEN 'Clôturée' ELSE 'En cours' END AS "refus_vs_encours" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total
-- ... (truncated)
```

## [408] Origine des candidatures de la file active

- **ID:** 4539
- **Dashboard:** 408
- **Tables:** candidats_recherche_active, candidatures_candidats_recherche_active

```sql
SELECT "source"."origine" AS "origine", COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa_cer
-- ... (truncated)
```

## [408] Évolution de l'état des candidatures

- **ID:** 4540
- **Dashboard:** 408
- **Tables:** candidats_recherche_active, candidatures_candidats_recherche_active

```sql
SELECT "source"."état" AS "état", DATE_TRUNC('month', CAST("source"."date_candidature" AS timestamp)) AS "date_candidature", COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "
-- ... (truncated)
```

## [216] nb candidatures

- **ID:** 4695
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "active", "public"."candidatures_echelle_locale"."brsa" AS "brsa", "public"."cand
-- ... (truncated)
```

## [216] nb de candidatures acceptées

- **ID:** 4704
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "active", "public"."candidatures_echelle_locale"."brsa" AS "brsa", "public"."cand
-- ... (truncated)
```

## [216] Nombre de candidats acceptés

- **ID:** 4718
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT count(distinct "source"."id_candidat") AS "Nb candidats acceptés" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "active", "public"."candidatures_ec
-- ... (truncated)
```

## [216] répartition des candidatures par origine candidat et par genre

- **ID:** 4750
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."origine" AS "origine", "source"."genre_candidat" AS "genre_candidat", COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "
-- ... (truncated)
```

## [216] répartition des candidatures par origine candidat - tous

- **ID:** 4751
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."origine" AS "origine", COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "active", "public"."candidatures_echelle_locale"
-- ... (truncated)
```

## [216] taux acceptation des candidatures (global)

- **ID:** 4754
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "source"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date
-- ... (truncated)
```

## [216] Taux acceptation femmes

- **ID:** 4756
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN ("source"."genre_candidat" = 'Femme') 
AND ("source"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation femme" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echell
-- ... (truncated)
```

## [216] Nombre de candidats

- **ID:** 4766
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT count(distinct "source"."id_candidat") AS "Nb candidats acceptés" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "active", "public"."candidatures_ec
-- ... (truncated)
```

## [408] Origine des candidatures de la file active - origine détaillée

- **ID:** 4802
- **Dashboard:** 408
- **Tables:** candidats_recherche_active, candidatures_candidats_recherche_active

```sql
SELECT "source"."origine_détaillée" AS "origine_détaillée", COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidatures_candidats_recherche_active"."critère_n1_bén
-- ... (truncated)
```
