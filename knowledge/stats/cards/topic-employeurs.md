# Thème : employeurs

*SIAE and employer information*

**14 cartes**

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

## [116] Evolution des candidatures acceptées sur les 12 derniers mois, par type d'employeur - échelle locale

- **ID:** 1393
- **Dashboard:** 116
- **Tables:** candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) AS "date_embauche", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
GROUP BY "public"."candidatures_echelle_locale"."type_structure", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) 
ORDER BY "count" DESC, "public"."candidatures_echelle_locale"."type_structure" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) ASC
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

## Nombre de fdp ouvertes par SIAE

- **ID:** 4313
- **Dashboard:** 408
- **Tables:** fiches_de_poste

```sql
SELECT "source"."type_employeur" AS "type_employeur", COUNT(*) AS "count" 
FROM (SELECT "public"."fiches_de_poste"."id" AS "id", "public"."fiches_de_poste"."code_rome" AS "code_rome", "public"."fiches_de_poste"."nom_rome" AS "nom_rome", "public"."fiches_de_poste"."recrutement_ouvert" AS "recrutement_ouvert", "public"."fiches_de_poste"."type_contrat" AS "type_contrat", "public"."fiches_de_poste"."id_employeur" AS "id_employeur", "public"."fiches_de_poste"."type_employeur" AS "type_employeur", "public"."fiches_de_poste"."siret_employeur" AS "siret_employeur", "public"."fiches_de_poste"."nom_employeur" AS "nom_employeur", "public"."fiches_de_poste"."mises_a_jour_champs" AS "mises_a_jour_champs", "public"."fiches_de_poste"."département_employeur" AS "département_employeur", "public"."fiches_de_poste"."nom_département_employeur" AS "nom_département_employeur", "public"."fiches_de_poste"."région_employeur" AS "région_employeur", "public"."fiches_de_poste"."total_candidatures" AS "total_candidatures", "public"."fiches_de_poste"."date_création" AS "date_création", "public"."fiches_de_poste"."date_dernière_modification" AS "date_dernière_modification", "public"."fiches_de_poste"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" 
FROM "public"."fiches_de_poste") AS "source" 
WHERE ("source"."recrutement_ouvert" = 1) 
AND (("source"."type_employeur" = 'ACI') 
OR ("source"."type_employeur" = 'AI') 
OR ("source"."type_employeur" = 'EITI') 
OR ("source"."type_employeur" = 'EI') 
OR ("source"."type_employeur" = 'ETTI')) 
GROUP BY "source"."type_employeur" 
ORDER BY "source"."type_employeur" ASC
```

## Nombre de fdp ouvertes par département

- **ID:** 4315
- **Dashboard:** 408
- **Tables:** fiches_de_poste

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

## [216] orientation SIAE selon genre

- **ID:** 4691
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."type_structure" AS "type_structure", "source"."genre_candidat" AS "genre_candidat", COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"
-- ... (truncated)
```

## [216] orientation SIAE - tous

- **ID:** 4742
- **Dashboard:** 216
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."type_structure" AS "type_structure", COUNT(*) AS "count" 
FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_echelle_locale"."mode_attribution_pass_iae" AS "mode_attribution_pass_iae", "public"."candidatures_echelle_locale"."présence_de_cv" AS "présence_de_cv", "public"."candidatures_echelle_locale"."nom" AS "nom", "public"."candidatures_echelle_locale"."habilitée" AS "habilitée", "public"."candidatures_echelle_locale"."adresse_ligne_1" AS "adresse_ligne_1", "public"."candidatures_echelle_locale"."adresse_ligne_2" AS "adresse_ligne_2", "public"."candidatures_echelle_locale"."code_postal" AS "code_postal", "public"."candidatures_echelle_locale"."longitude" AS "longitude", "public"."candidatures_echelle_locale"."latitude" AS "latitude", "public"."candidatures_echelle_locale"."département" AS "département", "public"."candidatures_echelle_locale"."code_safir" AS "code_safir", "public"."candidatures_echelle_locale"."date_dernière_connexion" AS "date_dernière_connexion", "public"."candidatures_echelle_locale"."active" AS "active", "public"."candidatures_e
-- ... (truncated)
```

## Pourcentage moyen du CA avec secteur public

- **ID:** 5407
- **Dashboard:** 471
- **Tables:** ESAT

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Pourcentage du CA avec secteur public") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Financement OPCO

- **ID:** 5409
- **Dashboard:** 471
- **Tables:** ESAT

```sql
SELECT "source"."Financement Opco" AS "Financement Opco", COUNT(*) AS "count" 
FROM (SELECT CASE WHEN "public"."ESAT - Questionnaire transfo"."OPCO" = 1 THEN 'oui' WHEN "public"."ESAT - Questionnaire transfo"."OPCO" = 0 THEN 'non' END AS "Financement Opco" 
FROM "public"."ESAT - Questionnaire transfo") AS "source" 
GROUP BY "source"."Financement Opco" 
ORDER BY "source"."Financement Opco" ASC
```
