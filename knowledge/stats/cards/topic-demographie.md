# Thème : demographie

*Age, gender, geographic breakdowns*

**35 cartes**

## [408] Carto des candidats en recherche active

- **ID:** 7025
- **Dashboard:** 408
- **Tables:** public, candidatures_candidats_recherche_active, candidats_recherche_active

```sql
SELECT "source"."département" AS "département", count(distinct "source"."id") AS "count" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidatures_candidats_recherche_active"."critè
-- ... (truncated)
```

## Candidats par genre

- **ID:** 7026
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."genre_candidat" AS "genre_candidat", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", count(distinct "public"."candidatures_echelle_locale"."id_candidat") AS "nb candidats" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
GROUP BY "public"."candidatures_echelle_locale"."genre_candidat", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."genre_candidat" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## Représentation des candidatures reçues par les SIAE par tranche d'âge

- **ID:** 7060
- **Tables:** public, candidatures_echelle_locale

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
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
GROUP BY "public"."candidatures_echelle_locale"."tranche_age", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."tranche_age" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## Candidats par tranche d'âge

- **ID:** 7061
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."tranche_age" AS "tranche_age", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", count(distinct "public"."candidatures_echelle_locale"."id_candidat") AS "nb candidats" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
GROUP BY "public"."candidatures_echelle_locale"."tranche_age", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) 
ORDER BY "public"."candidatures_echelle_locale"."tranche_age" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## Candidatures par genre

- **ID:** 7064
- **Tables:** public, candidatures_echelle_locale

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

## [216] part de femmes dans les candidatures émises - département

- **ID:** 7075
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

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

- **ID:** 7076
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

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

## [408] Carto des candidats en recherche active

- **ID:** 7079
- **Dashboard:** 408
- **Tables:** public, candidatures_candidats_recherche_active, candidats_recherche_active

```sql
SELECT "source"."département" AS "département", count(distinct "source"."id") AS "count" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidatures_candidats_recherche_active"."critè
-- ... (truncated)
```

## [216] budget genré

- **ID:** 7238
- **Dashboard:** 216
- **Tables:** etp_par_salarie, public

```sql
SELECT "public"."etp_par_salarie"."emi_sme_annee" AS "emi_sme_annee", CAST(SUM(CASE WHEN "public"."etp_par_salarie"."genre_salarie" = 'Homme' THEN "public"."etp_par_salarie"."montant_alloue" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."etp_par_salarie"."montant_alloue") AS DOUBLE PRECISION), 0.0) AS "Part du budget alloué aux hommes", CAST(SUM(CASE WHEN "public"."etp_par_salarie"."genre_salarie" = 'Femme' THEN "public"."etp_par_salarie"."montant_alloue" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."etp_par_salarie"."montant_alloue") AS DOUBLE PRECISION), 0.0) AS "Part du budget alloué aux femmes" 
FROM "public"."etp_par_salarie" 
WHERE ("public"."etp_par_salarie"."genre_salarie" = 'Femme') 
OR ("public"."etp_par_salarie"."genre_salarie" = 'Homme') 
GROUP BY "public"."etp_par_salarie"."emi_sme_annee" 
ORDER BY "public"."etp_par_salarie"."emi_sme_annee" ASC
```

## [325] moyenne d'heures travaillées par type de structure et par genre

- **ID:** 7239
- **Dashboard:** 325

```sql
[Query timeout]
```

## [408] Carto des candidats en recherche active

- **ID:** 7287
- **Dashboard:** 408
- **Tables:** public, candidatures_candidats_recherche_active, candidats_recherche_active

```sql
SELECT "source"."département" AS "département", count(distinct "source"."id") AS "count" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidatures_candidats_recherche_active"."critè
-- ... (truncated)
```

## [408] Nombre de candidats dans la file active IAE par genre

- **ID:** 7293
- **Dashboard:** 408
- **Tables:** public, candidatures_candidats_recherche_active, candidats_recherche_active

```sql
SELECT "source"."genre_candidat" AS "genre_candidat", count(distinct "source"."id") AS "count" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidatures_candidats_recherche_active".
-- ... (truncated)
```

## [408] Nombre de candidats dans la file active IAE par tranche d'âge

- **ID:** 7297
- **Dashboard:** 408
- **Tables:** public, candidatures_candidats_recherche_active, candidats_recherche_active

```sql
SELECT "source"."tranche_age" AS "tranche_age", count(distinct "source"."id") AS "count" 
FROM (SELECT "public"."candidatures_candidats_recherche_active"."id" AS "id", "public"."candidatures_candidats_recherche_active"."hash_nir" AS "hash_nir", "public"."candidatures_candidats_recherche_active"."sexe_selon_nir" AS "sexe_selon_nir", "public"."candidatures_candidats_recherche_active"."annee_naissance_selon_nir" AS "annee_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."mois_naissance_selon_nir" AS "mois_naissance_selon_nir", "public"."candidatures_candidats_recherche_active"."age" AS "age", "public"."candidatures_candidats_recherche_active"."date_inscription" AS "date_inscription", "public"."candidatures_candidats_recherche_active"."type_inscription" AS "type_inscription", "public"."candidatures_candidats_recherche_active"."pe_connect" AS "pe_connect", "public"."candidatures_candidats_recherche_active"."pe_inscrit" AS "pe_inscrit", "public"."candidatures_candidats_recherche_active"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_candidats_recherche_active"."date_premiere_connexion" AS "date_premiere_connexion", "public"."candidatures_candidats_recherche_active"."actif" AS "actif", "public"."candidatures_candidats_recherche_active"."code_postal" AS "code_postal", "public"."candidatures_candidats_recherche_active"."département" AS "département", "public"."candidatures_candidats_recherche_active"."nom_département" AS "nom_département", "public"."candidatures_candidats_recherche_active"."région" AS "région", "public"."candidatures_candidats_recherche_active"."adresse_en_qpv" AS "adresse_en_qpv", "public"."candidatures_candidats_recherche_active"."total_candidatures" AS "total_candidatures", "public"."candidatures_candidats_recherche_active"."total_embauches" AS "total_embauches", "public"."candidatures_candidats_recherche_active"."total_diagnostics" AS "total_diagnostics", "public"."candidatures_candidats_recherche_active"."date_diagnostic" AS "date_diagnostic", "public"."candidatures_candidats_recherche_active"."date_expiration_diagnostic" AS "date_expiration_diagnostic", "public"."candidatures_candidats_recherche_active"."type_auteur_diagnostic" AS "type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."sous_type_auteur_diagnostic" AS "sous_type_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."nom_auteur_diagnostic" AS "nom_auteur_diagnostic", "public"."candidatures_candidats_recherche_active"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_1" AS "total_critères_niveau_1", "public"."candidatures_candidats_recherche_active"."total_critères_niveau_2" AS "total_critères_niveau_2", "public"."candidatures_candidats_recherche_active"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidatures_candidats_recherche_active"."critè
-- ... (truncated)
```

## Nombre de fdp ouvertes par département

- **ID:** 7305
- **Tables:** public, fiches_de_poste

```sql
SELECT "source"."département_employeur" AS "département_employeur", COUNT(*) AS "count" 
FROM (SELECT "public"."fiches_de_poste"."id" AS "id", "public"."fiches_de_poste"."code_rome" AS "code_rome", "public"."fiches_de_poste"."nom_rome" AS "nom_rome", "public"."fiches_de_poste"."recrutement_ouvert" AS "recrutement_ouvert", "public"."fiches_de_poste"."type_contrat" AS "type_contrat", "public"."fiches_de_poste"."id_employeur" AS "id_employeur", "public"."fiches_de_poste"."type_employeur" AS "type_employeur", "public"."fiches_de_poste"."siret_employeur" AS "siret_employeur", "public"."fiches_de_poste"."nom_employeur" AS "nom_employeur", "public"."fiches_de_poste"."mises_a_jour_champs" AS "mises_a_jour_champs", "public"."fiches_de_poste"."département_employeur" AS "département_employeur", "public"."fiches_de_poste"."nom_département_employeur" AS "nom_département_employeur", "public"."fiches_de_poste"."région_employeur" AS "région_employeur", "public"."fiches_de_poste"."total_candidatures" AS "total_candidatures", "public"."fiches_de_poste"."date_création" AS "date_création", "public"."fiches_de_poste"."date_dernière_modification" AS "date_dernière_modification", "public"."fiches_de_poste"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" 
FROM "public"."fiches_de_poste") AS "source" 
WHERE ("source"."recrutement_ouvert" = 1) 
AND (("source"."type_employeur" = 'ACI') 
OR ("source"."type_employeur" = 'AI') 
OR ("source"."type_employeur" = 'EITI') 
OR ("source"."type_employeur" = 'EI') 
OR ("source"."type_employeur" = 'ETTI')) 
GROUP BY "source"."département_employeur" 
ORDER BY "source"."département_employeur" ASC
```

## [216] part de femmes dans candidatures acceptées - national

- **ID:** 7308
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

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

## [216] % candidatures hommes

- **ID:** 7310
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_con
-- ... (truncated)
```

## [216] Part femmes hommes chez les candidats

- **ID:** 7314
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."genre_candidat" AS "genre_candidat", count(distinct "source"."id_candidat") AS "Nb candidats acceptés" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale".
-- ... (truncated)
```

## [216] % candidatures femmes

- **ID:** 7315
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% femmes dans les candidatures" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion"
-- ... (truncated)
```

## [216] Répartition du genre chez les candidats

- **ID:** 7316
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."genre_candidat" AS "genre_candidat", count(distinct "source"."id_candidat") AS "Nombre de candidats" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."a
-- ... (truncated)
```

## [216] Part femmes hommes chez les candidats acceptés

- **ID:** 7317
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."genre_candidat" AS "genre_candidat", count(distinct "source"."id_candidat") AS "Nb candidats acceptés" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale".
-- ... (truncated)
```

## [216] part femme homme acceptés par SIAE

- **ID:** 7318
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."type_structure" AS "type_structure", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "publi
-- ... (truncated)
```

## [216] Part d'hommes et de femmes dans les candidatures acceptées en fonction de l'origine de la candidature

- **ID:** 7319
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."origine" AS "origine", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatur
-- ... (truncated)
```

## [216] orientation SIAE selon genre

- **ID:** 7320
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."type_structure" AS "type_structure", "source"."genre_candidat" AS "genre_candidat", COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"
-- ... (truncated)
```

## [216] part de femmes dans les candidatures acceptées - département

- **ID:** 7322
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."département_structure" AS "département_structure", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latit
-- ... (truncated)
```

## [216] part femme homme par SIAE

- **ID:** 7323
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."type_structure" AS "type_structure", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "publi
-- ... (truncated)
```

## [216] part d'hommes et de femmes dans les candidatures en fonction de l'origine détaillée

- **ID:** 7324
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."origine_détaillée" AS "origine_détaillée", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", 
-- ... (truncated)
```

## [216] Taux acceptation par genre par département

- **ID:** 7325
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."nom_département_structure" AS "nom_département_structure", CAST(SUM(CASE WHEN ("source"."genre_candidat" = 'Femme') 
AND ("source"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation femme", CAST(SUM(CASE WHEN ("source"."genre_candidat" = 'Homme') 
AND ("source"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation homme", CAST(SUM(CASE WHEN "source"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation global" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom"
-- ... (truncated)
```

## [216] candidatures par domaine

- **ID:** 7326
- **Dashboard:** 216
- **Tables:** metier_candidatures, public

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

## [216] part d'hommes et de femmes dans les candidatures acceptées en fonction de l'origine détaillée

- **ID:** 7327
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."origine_détaillée" AS "origine_détaillée", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", 
-- ... (truncated)
```

## [216] Répartition du genre dans les candidatures

- **ID:** 7328
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."genre_candidat" AS "genre_candidat", COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "active", "public"."candidatures_e
-- ... (truncated)
```

## [216] Part d'hommes et de femmes dans les candidatures en fonction de l'origine de la candidature

- **ID:** 7330
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."origine" AS "origine", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatur
-- ... (truncated)
```

## [216] part de femmes dans les candidatures - département

- **ID:** 7332
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."département_structure" AS "département_structure", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latit
-- ... (truncated)
```

## [216] part d'hommes dans candidatures acceptées - national

- **ID:** 7334
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

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

## [216] répartition des candidatures par origine candidat et par genre

- **ID:** 7335
- **Dashboard:** 216
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."origine" AS "origine", "source"."genre_candidat" AS "genre_candidat", COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "
-- ... (truncated)
```

## [216] candidatures par métier

- **ID:** 7336
- **Dashboard:** 216
- **Tables:** metier_candidatures, public

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
