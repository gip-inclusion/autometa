# Dashboard : Candidatures - Cartographies des orientations vers les SIAE

**URL:** /tableaux-de-bord/cartographies-iae/

**7 cartes**

## Carte des orienteurs

- **ID:** 1749
- **Thème:** prescripteurs
- **Tables:** organisations

```sql
SELECT "public"."organisations"."département" AS "département", COUNT(*) AS "count" 
FROM "public"."organisations" 
WHERE (("public"."organisations"."total_membres" <> 0) 
OR ("public"."organisations"."total_membres" IS NULL)) 
AND ("public"."organisations"."habilitée" = 0) 
GROUP BY "public"."organisations"."département" 
ORDER BY "public"."organisations"."département" ASC
```

## Candidats inscrits sur les emplois

- **ID:** 1809
- **Thème:** demographie
- **Tables:** candidats

```sql
SELECT "public"."candidats"."département" AS "département", COUNT(*) AS "count" 
FROM "public"."candidats" 
GROUP BY "public"."candidats"."département" 
ORDER BY "public"."candidats"."département" ASC
```

## carte de france des fiches de poste au recrutement ouvert

- **ID:** 1810
- **Thème:** postes-tension
- **Tables:** fiches_de_poste

```sql
SELECT "public"."fiches_de_poste"."département_employeur" AS "département_employeur", COUNT(*) AS "count" 
FROM "public"."fiches_de_poste" 
WHERE "public"."fiches_de_poste"."recrutement_ouvert" = 1 
GROUP BY "public"."fiches_de_poste"."département_employeur" 
ORDER BY "public"."fiches_de_poste"."département_employeur" ASC
```

## [216] part de femmes dans les candidatures émises - département

- **ID:** 2022
- **Thème:** demographie
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
- **Thème:** demographie
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

## [150] Carte des SIAE avec au moins une fiche de poste en difficulté de recrutement - Modifié

- **ID:** 4832
- **Thème:** postes-tension
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT "public"."fiches_deposte_en_tension_recrutement"."département_structure" AS "département_structure", count(distinct "public"."fiches_deposte_en_tension_recrutement"."id_structure") AS "Nombre de SIAE avec au moins une fiche de poste en _0a37a889" 
FROM "public"."fiches_deposte_en_tension_recrutement" 
WHERE ("public"."fiches_deposte_en_tension_recrutement"."etape" = '5- Fiches de poste en difficulté de recrutement') 
AND ("public"."fiches_deposte_en_tension_recrutement"."valeur" > 0) 
AND ("public"."fiches_deposte_en_tension_recrutement"."categorie_structure" = 'IAE') 
GROUP BY "public"."fiches_deposte_en_tension_recrutement"."département_structure" 
ORDER BY "public"."fiches_deposte_en_tension_recrutement"."département_structure" ASC
```

## [150] Cartographie SIAE avec au moins une fiche de poste en difficulté de recrutement sans candidature

- **ID:** 4833
- **Thème:** postes-tension
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT "public"."fiches_deposte_en_tension_recrutement"."département_structure" AS "département_structure", count(distinct "public"."fiches_deposte_en_tension_recrutement"."id_structure") AS "Nombre de SIAE avec au moins une fiche de poste en _0a37a889" 
FROM "public"."fiches_deposte_en_tension_recrutement" 
WHERE ("public"."fiches_deposte_en_tension_recrutement"."etape" = '6- Fiches de poste en difficulté de recrutement n ayant jamais reçu de candidatures') 
AND ("public"."fiches_deposte_en_tension_recrutement"."valeur" > 0) 
AND ("public"."fiches_deposte_en_tension_recrutement"."categorie_structure" = 'IAE') 
GROUP BY "public"."fiches_deposte_en_tension_recrutement"."département_structure" 
ORDER BY "public"."fiches_deposte_en_tension_recrutement"."département_structure" ASC
```
