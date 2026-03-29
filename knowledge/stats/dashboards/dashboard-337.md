# Dashboard : Candidatures - Bilan annuel des candidatures émises vers les SIAE

**URL:** /tableaux-de-bord/bilan-candidatures-iae/

**44 cartes**

## Répartition orienteurs inscrits par type

- **ID:** 3504
- **Thème:** employeurs
- **Tables:** organisations

```sql
SELECT "public"."organisations"."type_prescripteur" AS "type_prescripteur", COUNT(*) AS "count" 
FROM "public"."organisations" 
WHERE ("public"."organisations"."total_membres" <> 0) 
OR ("public"."organisations"."total_membres" IS NULL) 
GROUP BY "public"."organisations"."type_prescripteur" 
ORDER BY "count" DESC, "public"."organisations"."type_prescripteur" ASC
```

## Evolution annuelle du taux de candidatures acceptées et refusées à partir de 2021

- **ID:** 3510
- **Thème:** candidatures
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
- **Thème:** candidatures
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

## Suivi des orientations par orienteur

- **ID:** 3608
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", "public"."candidatures_echelle_locale"."type_prescripteur" AS "type_prescripteur", count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
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
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND ("public"."candidatures_echelle_locale"."injection_ai" = 0) 
GROUP BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date), "public"."candidatures_echelle_locale"."type_prescripteur" 
ORDER BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC, "public"."candidatures_echelle_locale"."type_prescripteur" ASC
```

## Répartition des conseilleurs inscrits par type de prescripteurs

- **ID:** 3622
- **Thème:** employeurs
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
- **Thème:** employeurs
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
- **Thème:** employeurs
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
- **Thème:** employeurs
- **Tables:** organisations

```sql
SELECT "public"."organisations"."département" AS "département", COUNT(*) AS "count" 
FROM "public"."organisations" 
WHERE ("public"."organisations"."total_membres" <> 0) 
OR ("public"."organisations"."total_membres" IS NULL) 
GROUP BY "public"."organisations"."département" 
ORDER BY "count" DESC, "public"."organisations"."département" ASC
```

## Candidats par tranche d'âge

- **ID:** 3629
- **Thème:** candidatures
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
- **Thème:** candidatures
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

## Nombre de candidats accompagnés par les prescripteurs habilités

- **ID:** 3635
- **Thème:** prescripteurs
- **Tables:** taux_transformation_prescripteurs

```sql
SELECT "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" AS "type_auteur_diagnostic_detaille", CAST(DATE_TRUNC('year', "public"."taux_transformation_prescripteurs"."date_diagnostic") AS date) AS "date_diagnostic", COUNT(*) AS "count" 
FROM "public"."taux_transformation_prescripteurs" 
WHERE ("public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" IS NOT NULL) 
AND (("public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" <> '') 
OR ("public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" IS NULL)) 
AND (("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'ACI') 
OR ("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'AI') 
OR ("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'EI') 
OR ("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'EITI') 
OR ("public"."taux_transformation_prescripteurs"."type_structure_dernière_embauche" = 'ETTI')) 
AND ("public"."taux_transformation_prescripteurs"."date_diagnostic" < date '2025-01-01') 
GROUP BY "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille", CAST(DATE_TRUNC('year', "public"."taux_transformation_prescripteurs"."date_diagnostic") AS date) 
ORDER BY CAST(DATE_TRUNC('year', "public"."taux_transformation_prescripteurs"."date_diagnostic") AS date) ASC, "public"."taux_transformation_prescripteurs"."type_auteur_diagnostic_detaille" ASC
```

## Candidatures toujours en cours de traitement

- **ID:** 3643
- **Thème:** candidatures
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

## % de SIAE avec un poste ouvert

- **ID:** 3644
- **Thème:** employeurs
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

## Nombre de fiches de postes ouverts par les SIAE

- **ID:** 3662
- **Thème:** postes-tension
- **Tables:** fiches_de_poste

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."fiches_de_poste" 
WHERE (("public"."fiches_de_poste"."type_employeur" = 'ACI') 
OR ("public"."fiches_de_poste"."type_employeur" = 'AI') 
OR ("public"."fiches_de_poste"."type_employeur" = 'EI') 
OR ("public"."fiches_de_poste"."type_employeur" = 'EITI') 
OR ("public"."fiches_de_poste"."type_employeur" = 'ETTI')) 
AND ("public"."fiches_de_poste"."recrutement_ouvert" = 1)
```

## % de SIAE ayant accepté une candidature sur les 30 derniers jours

- **ID:** 3663
- **Thème:** employeurs
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

## Nb de SIAE avec des fiches de poste en tension n'ayant reçu aucune candidature

- **ID:** 3664
- **Thème:** postes-tension
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT count(distinct "public"."fiches_deposte_en_tension_recrutement"."id_structure") AS "Nombre de SIAE avec au moins une fiche de poste en _0a37a889" 
FROM "public"."fiches_deposte_en_tension_recrutement" 
WHERE ("public"."fiches_deposte_en_tension_recrutement"."etape" = '6- Fiches de poste en difficulté de recrutement n ayant jamais reçu de candidatures') 
AND ("public"."fiches_deposte_en_tension_recrutement"."valeur" > 0) 
AND (("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'ACI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'AI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'EI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'EITI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'ETTI'))
```

## Répartition des orientations vers l'IAE

- **ID:** 3665
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT "source"."Origine simple" AS "Origine simple", DATE_TRUNC('year', CAST("source"."date_candidature" AS timestamp)) AS "date_candidature", COUNT(*) AS "count" 
FROM (SELECT CASE WHEN "public"."candidatures_echelle_locale"."origine_détaillée" = 'Prescripteur habilité PE' THEN 'Pôle emploi' WHEN "public"."candidatures_echelle_locale"."origine_détaillée" = 'Prescripteur habilité ML' THEN 'Mission Locale' WHEN "public"."candidatures_echelle_locale"."origine_détaillée" = 'Prescripteur habilité CAP_EMPLOI' THEN 'Cap Emploi' WHEN "public"."candidatures_echelle_locale"."origine_détaillée" = 'Prescripteur habilité PLIE' THEN 'PLIE - Plan local pour l''insertion et l''emploi' WHEN "public"."candidatures_echelle_locale"."origine_détaillée" = 'Prescripteur habilité DEPT' THEN 'Service social du conseil départemental' WHEN "public"."candidatures_echelle_locale"."origine_détaillée" LIKE 'Employeur%' THEN 'Employeur' WHEN "public"."candidatures_echelle_locale"."origine_détaillée" = 'Candidat' THEN 'Candidat' WHEN "public"."candidatures_echelle_locale"."origine_détaillée" LIKE 'Orienteur%' THEN 'Autres orienteurs' ELSE 'Autres prescripteurs' END AS "Origine simple", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND ("public"."candidatures_echelle_locale"."injection_ai" = 0) 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))) AS "source" 
GROUP BY "source"."Origine simple", DATE_TRUNC('year', CAST("source"."date_candidature" AS timestamp)) 
ORDER BY "source"."Origine simple" ASC, DATE_TRUNC('year', CAST("source"."date_candidature" AS timestamp)) ASC
```

## Evolution du taux d'auto-prescription

- **ID:** 3668
- **Thème:** auto-prescription
- **Tables:** suivi_auto_prescription

```sql
SELECT CAST(DATE_TRUNC('year', "public"."suivi_auto_prescription"."date_candidature") AS date) AS "date_candidature", CAST(SUM(CASE WHEN "public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux d'auto prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."suivi_auto_prescription"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."suivi_auto_prescription"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND ("public"."suivi_auto_prescription"."categorie_structure" = 'IAE') 
GROUP BY CAST(DATE_TRUNC('year', "public"."suivi_auto_prescription"."date_candidature") AS date) 
ORDER BY CAST(DATE_TRUNC('year', "public"."suivi_auto_prescription"."date_candidature") AS date) ASC
```

## [337] Nombre total (mère + antenne) de structures sur les emplois

- **ID:** 3676
- **Thème:** employeurs
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

## Nombre de fiches de postes en tension sans candidature pour les SIAE

- **ID:** 3677
- **Thème:** postes-tension
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT SUM("public"."fiches_deposte_en_tension_recrutement"."valeur") AS "Nombre de fiches de poste en difficulté de recrutement" 
FROM "public"."fiches_deposte_en_tension_recrutement" 
WHERE ("public"."fiches_deposte_en_tension_recrutement"."etape" = '6- Fiches de poste en difficulté de recrutement n ayant jamais reçu de candidatures') 
AND (("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'ACI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'AI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'EI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'EITI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'ETTI'))
```

## % fiches de poste en tension sans candidature

- **ID:** 3679
- **Thème:** postes-tension
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT CAST(SUM(CASE WHEN "public"."fiches_deposte_en_tension_recrutement"."etape" = '6- Fiches de poste en difficulté de recrutement n ayant jamais reçu de candidatures' THEN "public"."fiches_deposte_en_tension_recrutement"."valeur" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."fiches_deposte_en_tension_recrutement"."etape" = '2- Fiches de poste actives' THEN "public"."fiches_deposte_en_tension_recrutement"."valeur" ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "% fiches de poste en difficulté de recrutement san_cb86b9fc" 
FROM "public"."fiches_deposte_en_tension_recrutement" 
WHERE ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'ACI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'AI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'EI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'EITI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'ETTI')
```

## Taux d'acceptation et refus des prescriptions

- **ID:** 3680
- **Thème:** candidatures
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

## Evolution des prescriptions des PH

- **ID:** 3682
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", "public"."candidatures_echelle_locale"."type_complet" AS "type_complet", count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."date_candidature" < date '2025-01-01') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND (("public"."candidatures_echelle_locale"."type_prescripteur" = 'Autre') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Département') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'Nouveaux prescripteurs') 
OR ("public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE')) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
GROUP BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date), "public"."candidatures_echelle_locale"."type_complet" 
ORDER BY CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC, "public"."candidatures_echelle_locale"."type_complet" ASC
```

## Taux de candidatures refusées par les SIAE - année précedente

- **ID:** 3685
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures refusées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."date_candidature" >= (DATE_TRUNC('year', (NOW() + INTERVAL '-1 year')) + INTERVAL '-1 year')) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < (DATE_TRUNC('year', NOW()) + INTERVAL '-1 year'))) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Taux de candidatures acceptées par les SIAE - année précedente

- **ID:** 3686
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."date_candidature" >= (DATE_TRUNC('year', (NOW() + INTERVAL '-1 year')) + INTERVAL '-1 year')) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < (DATE_TRUNC('year', NOW()) + INTERVAL '-1 year'))) 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Organisations, Nombre total de conseillers inscrits, Grouped by Date Inscription: Year, Filtered by Date Inscription is not empty, Sorted by Nombre total de conseillers inscrits descending

- **ID:** 3688
- **Thème:** employeurs
- **Tables:** organisations

```sql
SELECT CAST(DATE_TRUNC('year', "public"."organisations"."date_inscription") AS date) AS "date_inscription", SUM("public"."organisations"."total_membres") AS "Nombre total de conseillers inscrits" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL 
GROUP BY CAST(DATE_TRUNC('year', "public"."organisations"."date_inscription") AS date) 
ORDER BY "Nombre total de conseillers inscrits" DESC, CAST(DATE_TRUNC('year', "public"."organisations"."date_inscription") AS date) ASC
```

## Taux d'auto-prescription année précedente

- **ID:** 3689
- **Thème:** auto-prescription
- **Tables:** suivi_auto_prescription

```sql
SELECT CAST(SUM(CASE WHEN "public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux d'auto prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI')) 
AND (("public"."suivi_auto_prescription"."date_candidature" >= (DATE_TRUNC('year', (NOW() + INTERVAL '-1 year')) + INTERVAL '-1 year')) 
AND ("public"."suivi_auto_prescription"."date_candidature" < (DATE_TRUNC('year', NOW()) + INTERVAL '-1 year'))) 
AND (("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI'))
```

## Nombre de candidatures acceptées - année précedente

- **ID:** 3695
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND (("public"."candidatures_echelle_locale"."date_candidature" >= (DATE_TRUNC('year', (NOW() + INTERVAL '-1 year')) + INTERVAL '-1 year')) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < (DATE_TRUNC('year', NOW()) + INTERVAL '-1 year'))) 
AND ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Nombre de candidatures en cours de traitement - année précedente

- **ID:** 3709
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."état" = 'Candidature à l''étude') 
OR ("public"."candidatures_echelle_locale"."état" = 'Candidature en attente') 
OR ("public"."candidatures_echelle_locale"."état" = 'Nouvelle candidature')) 
AND (("public"."candidatures_echelle_locale"."date_candidature" >= (DATE_TRUNC('year', (NOW() + INTERVAL '-1 year')) + INTERVAL '-1 year')) 
AND ("public"."candidatures_echelle_locale"."date_candidature" < (DATE_TRUNC('year', NOW()) + INTERVAL '-1 year'))) 
AND ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Part de prescriptions du SPE

- **ID:** 3815
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de prescriptions du SPE" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2024-01-01' 
AND date '2024-12-31'
```

## Motifs de refus sur 2024

- **ID:** 3828
- **Thème:** candidatures
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

## Part de prescriptions du SPE en 2025

- **ID:** 3863
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."type_prescripteur" = 'SPE' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de prescriptions du SPE" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2025-01-01' 
AND date '2025-12-31'
```

## Taux d'auto-prescription en 2025

- **ID:** 3864
- **Thème:** auto-prescription
- **Tables:** suivi_auto_prescription

```sql
SELECT CAST(SUM(CASE WHEN "public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux d'auto prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI')) 
AND "public"."suivi_auto_prescription"."date_candidature" BETWEEN date '2025-01-01' 
AND date '2025-12-31' 
AND (("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI'))
```

## Nombre de candidatures acceptées en 2025

- **ID:** 3865
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2025-01-01' 
AND date '2025-12-31' 
AND ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Taux de candidatures acceptées par les SIAE en 2025

- **ID:** 3866
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2025-01-01' 
AND date '2025-12-31' 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Nombre de candidatures en attente d'être clôturée sur 2025

- **ID:** 3867
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE (("public"."candidatures_echelle_locale"."état" = 'Candidature à l''étude') 
OR ("public"."candidatures_echelle_locale"."état" = 'Candidature en attente') 
OR ("public"."candidatures_echelle_locale"."état" = 'Nouvelle candidature')) 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2025-01-01' 
AND date '2025-12-31' 
AND ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Taux de candidatures refusées par les SIAE en 2025

- **ID:** 3868
- **Thème:** candidatures
- **Tables:** candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures refusées" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."categorie_structure" = 'IAE') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND "public"."candidatures_echelle_locale"."date_candidature" BETWEEN date '2025-01-01' 
AND date '2025-12-31' 
AND (("public"."candidatures_echelle_locale"."type_structure" = 'AI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ACI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') 
OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI'))
```

## Répartition des orientations par type de SIAE

- **ID:** 3873
- **Thème:** candidatures
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

## Evolution du taux d'auto-prescription par type de SIAE

- **ID:** 3874
- **Thème:** auto-prescription
- **Tables:** suivi_auto_prescription

```sql
SELECT "public"."suivi_auto_prescription"."type_structure" AS "type_structure", CAST(DATE_TRUNC('year', "public"."suivi_auto_prescription"."date_candidature") AS date) AS "date_candidature", CAST(SUM(CASE WHEN "public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux d'auto prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI')) 
AND ("public"."suivi_auto_prescription"."date_candidature" >= DATE_TRUNC('year', (NOW() + INTERVAL '-2 year'))) 
AND ("public"."suivi_auto_prescription"."date_candidature" < DATE_TRUNC('year', NOW())) 
AND (("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI')) 
GROUP BY "public"."suivi_auto_prescription"."type_structure", CAST(DATE_TRUNC('year', "public"."suivi_auto_prescription"."date_candidature") AS date) 
ORDER BY "public"."suivi_auto_prescription"."type_structure" ASC, CAST(DATE_TRUNC('year', "public"."suivi_auto_prescription"."date_candidature") AS date) ASC
```

## Taux d'acceptation et refus des prescriptions par type de SIAE en 2023

- **ID:** 3875
- **Thème:** candidatures
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
- **Thème:** candidatures
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

## Candidatures par genre

- **ID:** 3881
- **Thème:** candidatures
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
- **Thème:** candidatures
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

## Nombre de pass agréments délivrés par année

- **ID:** 6236
- **Thème:** candidatures
- **Tables:** pass_agréments

```sql
SELECT CAST(DATE_TRUNC('year', "public"."pass_agréments"."date_début") AS date) AS "date_début", count(distinct "public"."pass_agréments"."id") AS "count" 
FROM "public"."pass_agréments" 
WHERE ("public"."pass_agréments"."date_début" > date '2020-12-31') 
AND ("public"."pass_agréments"."date_début" < date '2025-01-01') 
GROUP BY CAST(DATE_TRUNC('year', "public"."pass_agréments"."date_début") AS date) 
ORDER BY CAST(DATE_TRUNC('year', "public"."pass_agréments"."date_début") AS date) ASC
```
