# Thème : demographie

*Age, gender, geographic breakdowns*

**33 cartes**

## [116]Profil des candidats embauchés

- **ID:** 821
- **Dashboard:** 116
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

## Candidats inscrits sur les emplois

- **ID:** 1809
- **Dashboard:** 218
- **Tables:** candidats

```sql
SELECT "public"."candidats"."département" AS "département", COUNT(*) AS "count" 
FROM "public"."candidats" 
GROUP BY "public"."candidats"."département" 
ORDER BY "public"."candidats"."département" ASC
```

## [216] part de femmes dans les candidatures émises - département

- **ID:** 2022
- **Dashboard:** 218
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND ("public"."candidatures_echelle_locale"."date_inscription_candidat" > date '2021-11-01') 
AND (("public"."candidatures_echelle_locale"."genre_candidat" = 'Homme') 
OR ("public"."candidatures_echelle_locale"."genre_candidat" = 'Femme')) 
GROUP BY "public"."candidatures_echelle_locale"."département_structure" 
ORDER BY "public"."candidatures_echelle_locale"."département_structure" ASC
```

## [216] part de femmes dans les candidatures acceptées - département

- **ID:** 2023
- **Dashboard:** 218
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND ("public"."candidatures_echelle_locale"."date_inscription_candidat" > date '2021-11-01') 
AND (("public"."candidatures_echelle_locale"."genre_candidat" = 'Femme') 
OR ("public"."candidatures_echelle_locale"."genre_candidat" = 'Homme')) 
GROUP BY "public"."candidatures_echelle_locale"."département_structure" 
ORDER BY "public"."candidatures_echelle_locale"."département_structure" ASC
```

## [216] part de femmes dans candidatures acceptées - national

- **ID:** 2257
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes acceptées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND ("public"."candidatures_echelle_locale"."date_inscription_candidat" > date '2021-11-01') 
AND (("public"."candidatures_echelle_locale"."genre_candidat" = 'Homme') 
OR ("public"."candidatures_echelle_locale"."genre_candidat" = 'Femme'))
```

## [216] part d'hommes dans candidatures acceptées - national

- **ID:** 2258
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes acceptés" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND ("public"."candidatures_echelle_locale"."date_inscription_candidat" > date '2021-11-01') 
AND (("public"."candidatures_echelle_locale"."genre_candidat" = 'Femme') 
OR ("public"."candidatures_echelle_locale"."genre_candidat" = 'Homme'))
```

## [216] budget genré

- **ID:** 2579
- **Dashboard:** 325
- **Tables:** etp_par_salarie

```sql
SELECT "public"."etp_par_salarie"."emi_sme_annee" AS "emi_sme_annee", CAST(SUM(CASE WHEN "public"."etp_par_salarie"."genre_salarie" = 'Homme' THEN "public"."etp_par_salarie"."montant_alloue" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."etp_par_salarie"."montant_alloue") AS DOUBLE PRECISION), 0.0) AS "Part du budget alloué aux hommes", CAST(SUM(CASE WHEN "public"."etp_par_salarie"."genre_salarie" = 'Femme' THEN "public"."etp_par_salarie"."montant_alloue" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."etp_par_salarie"."montant_alloue") AS DOUBLE PRECISION), 0.0) AS "Part du budget alloué aux femmes" 
FROM "public"."etp_par_salarie" 
WHERE ("public"."etp_par_salarie"."genre_salarie" = 'Femme') 
OR ("public"."etp_par_salarie"."genre_salarie" = 'Homme') 
GROUP BY "public"."etp_par_salarie"."emi_sme_annee" 
ORDER BY "public"."etp_par_salarie"."emi_sme_annee" ASC
```

## Candidats par tranche d'âge

- **ID:** 3629
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."tranche_age" AS "tranche_age", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", count(distinct "public"."candidatures_echelle_locale"."id_candidat") AS "nb candidats" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
GROUP BY "public"."candidatures_echelle_locale"."tranche_age", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."tranche_age" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## Candidats par genre

- **ID:** 3630
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."genre_candidat" AS "genre_candidat", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", count(distinct "public"."candidatures_echelle_locale"."id_candidat") AS "nb candidats" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
GROUP BY "public"."candidatures_echelle_locale"."genre_candidat", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."genre_candidat" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## Candidatures par genre

- **ID:** 3881
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."genre_candidat" AS "genre_candidat", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
GROUP BY "public"."candidatures_echelle_locale"."genre_candidat", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."genre_candidat" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## Représentation des candidatures reçues par les SIAE par tranche d'âge

- **ID:** 3882
- **Dashboard:** 337
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."tranche_age" AS "tranche_age", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
GROUP BY "public"."candidatures_echelle_locale"."tranche_age", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."tranche_age" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## [408] Carto des candidats en recherche active

- **ID:** 4544
- **Dashboard:** 408
- **Tables:** candidats_recherche_active, candidatures_candidats_recherche_active

```sql
SELECT "source"."département" AS "département", count(distinct "source"."id") AS "count" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidatures_candidats_recherche_active"."critè
-- ... (truncated)
```

## [216] % candidatures hommes

- **ID:** 4698
- **Description:** Nombre de candidatures venant d'hommes
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_con
-- ... (truncated)
```

## [216] % candidatures femmes

- **ID:** 4709
- **Description:** Pourcentage de candidatures réalisées par des femmes
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% femmes dans les candidatures" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion"
-- ... (truncated)
```

## [216] part de femmes dans les candidatures acceptées - département

- **ID:** 4743
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."département_structure" AS "département_structure", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latit
-- ... (truncated)
```

## [216] Part d'hommes et de femmes dans les candidatures acceptées en fonction de l'origine de la candidature

- **ID:** 4745
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."origine" AS "origine", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatur
-- ... (truncated)
```

## [216] Part d'hommes et de femmes dans les candidatures en fonction de l'origine de la candidature

- **ID:** 4746
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."origine" AS "origine", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatur
-- ... (truncated)
```

## [216] part d'hommes et de femmes dans les candidatures en fonction de l'origine détaillée

- **ID:** 4747
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."origine_détaillée" AS "origine_détaillée", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", 
-- ... (truncated)
```

## [216] part femme homme acceptés par SIAE

- **ID:** 4748
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."type_structure" AS "type_structure", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "publi
-- ... (truncated)
```

## [216] part femme homme par SIAE

- **ID:** 4749
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."type_structure" AS "type_structure", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "publi
-- ... (truncated)
```

## [216] Répartition du genre chez les candidats

- **ID:** 4752
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."genre_candidat" AS "genre_candidat", count(distinct "source"."id_candidat") AS "Nombre de candidats" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."a
-- ... (truncated)
```

## [216] Répartition du genre dans les candidatures

- **ID:** 4753
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."genre_candidat" AS "genre_candidat", COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "active", "public"."candidatures_e
-- ... (truncated)
```

## [216] Taux acceptation hommes

- **ID:** 4757
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN ("source"."genre_candidat" = 'Homme') 
AND ("source"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation homme" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echell
-- ... (truncated)
```

## [216] Taux acceptation par genre par département

- **ID:** 4758
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."nom_département_structure" AS "nom_département_structure", CAST(SUM(CASE WHEN ("source"."genre_candidat" = 'Femme') 
AND ("source"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation femme", CAST(SUM(CASE WHEN ("source"."genre_candidat" = 'Homme') 
AND ("source"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation homme", CAST(SUM(CASE WHEN "source"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation global" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom"
-- ... (truncated)
```

## [216] part de femmes dans les candidatures - département

- **ID:** 4759
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."département_structure" AS "département_structure", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latit
-- ... (truncated)
```

## [216] part d'hommes et de femmes dans les candidatures acceptées en fonction de l'origine détaillée

- **ID:** 4760
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."origine_détaillée" AS "origine_détaillée", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", 
-- ... (truncated)
```

## [216] Part femmes hommes chez les candidats acceptés

- **ID:** 4761
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."genre_candidat" AS "genre_candidat", count(distinct "source"."id_candidat") AS "Nb candidats acceptés" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale".
-- ... (truncated)
```

## [216] Part femmes hommes chez les candidats

- **ID:** 4762
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."genre_candidat" AS "genre_candidat", count(distinct "source"."id_candidat") AS "Nb candidats acceptés" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale".
-- ... (truncated)
```

## [408] Nombre de candidats dans la file active IAE par genre

- **ID:** 4803
- **Dashboard:** 408
- **Tables:** candidats_recherche_active, candidatures_candidats_recherche_active

```sql
SELECT "source"."genre_candidat" AS "genre_candidat", count(distinct "source"."id") AS "count" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidatures_candidats_recherche_active".
-- ... (truncated)
```

## [408] Nombre de candidats dans la file active IAE par tranche d'âge

- **ID:** 4804
- **Dashboard:** 408
- **Tables:** candidats_recherche_active, candidatures_candidats_recherche_active

```sql
SELECT "source"."tranche_age" AS "tranche_age", count(distinct "source"."id") AS "count" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidatures_candidats_recherche_active"."critè
-- ... (truncated)
```

## [408] Répartition candidats dans la file active par région

- **ID:** 4805
- **Dashboard:** 408
- **Tables:** candidats_recherche_active, candidatures_candidats_recherche_active

```sql
SELECT "source"."région" AS "région", count(distinct "source"."id") AS "count" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidatures_candidats_recherche_active"."critère_n1_béné
-- ... (truncated)
```

## [471] Age moyen des travailleurs

- **ID:** 4944
- **Dashboard:** 471
- **Tables:** Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Age moyen des travailleurs") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## Âge moyen des salariés

- **ID:** 6530
- **Dashboard:** 571
- **Tables:** questionnaire_2025

```sql
SELECT CAST(SUM("esat"."questionnaire_2025"."mean_employee_age" * "esat"."questionnaire_2025"."nb_employee_worked") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("esat"."questionnaire_2025"."nb_employee_worked") AS DOUBLE PRECISION), 0.0) AS "âge moyen des salariés" 
FROM "esat"."questionnaire_2025" 
WHERE "esat"."questionnaire_2025"."mean_employee_age" < 100
```
