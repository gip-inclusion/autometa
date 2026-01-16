# Dashboard : Pilotage dispositif - Analyses autour des conventionnements IAE

**URL:** /tableaux-de-bord/analyses-conventionnements-iae/

**3 cartes**

## [216] budget genré

- **ID:** 2579
- **Thème:** etp-effectifs
- **Tables:** etp_par_salarie

```sql
SELECT "public"."etp_par_salarie"."emi_sme_annee" AS "emi_sme_annee", CAST(SUM(CASE WHEN "public"."etp_par_salarie"."genre_salarie" = 'Homme' THEN "public"."etp_par_salarie"."montant_alloue" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."etp_par_salarie"."montant_alloue") AS DOUBLE PRECISION), 0.0) AS "Part du budget alloué aux hommes", CAST(SUM(CASE WHEN "public"."etp_par_salarie"."genre_salarie" = 'Femme' THEN "public"."etp_par_salarie"."montant_alloue" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."etp_par_salarie"."montant_alloue") AS DOUBLE PRECISION), 0.0) AS "Part du budget alloué aux femmes" 
FROM "public"."etp_par_salarie" 
WHERE ("public"."etp_par_salarie"."genre_salarie" = 'Femme') 
OR ("public"."etp_par_salarie"."genre_salarie" = 'Homme') 
GROUP BY "public"."etp_par_salarie"."emi_sme_annee" 
ORDER BY "public"."etp_par_salarie"."emi_sme_annee" ASC
```

## [325] moyenne d'heures travaillées par type de structure et par genre

- **ID:** 3439
- **Thème:** etp-effectifs
- **Tables:** etp_par_salarie

```sql
SELECT "public"."etp_par_salarie"."genre_salarie" AS "genre_salarie", "public"."etp_par_salarie"."type_structure_emplois" AS "type_structure_emplois", AVG("public"."etp_par_salarie"."nombre_heures_travaillees") AS "avg" 
FROM "public"."etp_par_salarie" 
WHERE (("public"."etp_par_salarie"."genre_salarie" = 'Femme') 
OR ("public"."etp_par_salarie"."genre_salarie" = 'Homme')) 
AND ("public"."etp_par_salarie"."af_etat_annexe_financiere_code" = 'VALIDE') 
GROUP BY "public"."etp_par_salarie"."genre_salarie", "public"."etp_par_salarie"."type_structure_emplois" 
ORDER BY "public"."etp_par_salarie"."type_structure_emplois" ASC, "public"."etp_par_salarie"."genre_salarie" ASC
```

## [325] moyenne d'heures travaillées par type de structure

- **ID:** 3440
- **Thème:** etp-effectifs
- **Tables:** etp_par_salarie

```sql
SELECT "public"."etp_par_salarie"."type_structure_emplois" AS "type_structure_emplois", AVG("public"."etp_par_salarie"."nombre_heures_travaillees") AS "avg" 
FROM "public"."etp_par_salarie" 
WHERE ("public"."etp_par_salarie"."af_etat_annexe_financiere_code" = 'VALIDE') 
AND (("public"."etp_par_salarie"."genre_salarie" = 'Femme') 
OR ("public"."etp_par_salarie"."genre_salarie" = 'Homme')) 
GROUP BY "public"."etp_par_salarie"."type_structure_emplois" 
ORDER BY "public"."etp_par_salarie"."type_structure_emplois" ASC
```
