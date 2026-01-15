# Thème : postes-tension

*Postes en tension (difficult to recruit)*

**16 cartes**

## [150] Nombre de fiches de poste en difficulté de recrutement n'ayant jamais reçu de candidature

- **ID:** 1411
- **Dashboard:** 150
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT SUM("public"."fiches_deposte_en_tension_recrutement"."valeur") AS "Nombre de fiches de poste en difficulté de recrutement" 
FROM "public"."fiches_deposte_en_tension_recrutement" 
WHERE "public"."fiches_deposte_en_tension_recrutement"."etape" = '6- Fiches de poste en difficulté de recrutement n ayant jamais reçu de candidatures'
```

## [150] % fiches de poste en difficulté de recrutement sans candidature

- **ID:** 1421
- **Dashboard:** 150
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT CAST(SUM(CASE WHEN "public"."fiches_deposte_en_tension_recrutement"."etape" = '6- Fiches de poste en difficulté de recrutement n ayant jamais reçu de candidatures' THEN "public"."fiches_deposte_en_tension_recrutement"."valeur" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."fiches_deposte_en_tension_recrutement"."etape" = '2- Fiches de poste actives' THEN "public"."fiches_deposte_en_tension_recrutement"."valeur" ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "% fiches de poste en difficulté de recrutement san_cb86b9fc" 
FROM "public"."fiches_deposte_en_tension_recrutement"
```

## carte de france des fiches de poste au recrutement ouvert

- **ID:** 1810
- **Dashboard:** 218
- **Tables:** fiches_de_poste

```sql
SELECT "public"."fiches_de_poste"."département_employeur" AS "département_employeur", COUNT(*) AS "count" 
FROM "public"."fiches_de_poste" 
WHERE "public"."fiches_de_poste"."recrutement_ouvert" = 1 
GROUP BY "public"."fiches_de_poste"."département_employeur" 
ORDER BY "public"."fiches_de_poste"."département_employeur" ASC
```

## [150] % FDP en difficulté de recrutement

- **ID:** 2485
- **Dashboard:** 150
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT CAST(SUM(CASE WHEN "public"."fiches_deposte_en_tension_recrutement"."etape" = '5- Fiches de poste en difficulté de recrutement' THEN "public"."fiches_deposte_en_tension_recrutement"."valeur" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."fiches_deposte_en_tension_recrutement"."etape" = '2- Fiches de poste actives' THEN "public"."fiches_deposte_en_tension_recrutement"."valeur" ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "% fiches de poste en difficulté de recrutement " 
FROM "public"."fiches_deposte_en_tension_recrutement"
```

## [150] Nombre de SIAE avec au moins une fiche de poste en difficulté de recrutement sans candidature

- **ID:** 2486
- **Dashboard:** 150
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT count(distinct "public"."fiches_deposte_en_tension_recrutement"."id_structure") AS "Nombre de SIAE avec au moins une fiche de poste en _0a37a889" 
FROM "public"."fiches_deposte_en_tension_recrutement" 
WHERE ("public"."fiches_deposte_en_tension_recrutement"."etape" = '6- Fiches de poste en difficulté de recrutement n ayant jamais reçu de candidatures') 
AND ("public"."fiches_deposte_en_tension_recrutement"."valeur" > 0)
```

## % de SIAE avec un poste ouvert

- **ID:** 3644
- **Dashboard:** 337
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
- **Dashboard:** 337
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
- **Dashboard:** 337
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
- **Dashboard:** 337
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

## Nombre de fiches de postes en tension sans candidature pour les SIAE

- **ID:** 3677
- **Dashboard:** 337
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

## [408] Nombre de fiches de poste en tension

- **ID:** 3678
- **Dashboard:** 408
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT SUM("public"."fiches_deposte_en_tension_recrutement"."valeur") AS "Nombre de fiches de poste en difficulté de recrutement" 
FROM "public"."fiches_deposte_en_tension_recrutement" 
WHERE ("public"."fiches_deposte_en_tension_recrutement"."etape" = '5- Fiches de poste en difficulté de recrutement') 
AND (("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'ACI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'AI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'EI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'EITI') 
OR ("public"."fiches_deposte_en_tension_recrutement"."type_structure" = 'ETTI'))
```

## % fiches de poste en tension sans candidature

- **ID:** 3679
- **Dashboard:** 337
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

## [150] Nombre de fiches de poste en difficulté de recrutement n'ayant jamais reçu de candidature par grand domaine

- **ID:** 3683
- **Dashboard:** 150
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT "public"."fiches_deposte_en_tension_recrutement"."grand_domaine" AS "grand_domaine", SUM("public"."fiches_deposte_en_tension_recrutement"."valeur") AS "Nombre de fiches de poste en difficulté de recrutement" 
FROM "public"."fiches_deposte_en_tension_recrutement" 
WHERE "public"."fiches_deposte_en_tension_recrutement"."etape" = '6- Fiches de poste en difficulté de recrutement n ayant jamais reçu de candidatures' 
GROUP BY "public"."fiches_deposte_en_tension_recrutement"."grand_domaine" 
ORDER BY "Nombre de fiches de poste en difficulté de recrutement" DESC, "public"."fiches_deposte_en_tension_recrutement"."grand_domaine" ASC
```

## [150] Nombre de fiches de poste en difficulté de recrutement n'ayant jamais reçu de candidature par domaine professionnel

- **ID:** 3684
- **Dashboard:** 150
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT "public"."fiches_deposte_en_tension_recrutement"."domaine_professionnel" AS "domaine_professionnel", SUM("public"."fiches_deposte_en_tension_recrutement"."valeur") AS "Nombre de fiches de poste en difficulté de recrutement" 
FROM "public"."fiches_deposte_en_tension_recrutement" 
WHERE "public"."fiches_deposte_en_tension_recrutement"."etape" = '6- Fiches de poste en difficulté de recrutement n ayant jamais reçu de candidatures' 
GROUP BY "public"."fiches_deposte_en_tension_recrutement"."domaine_professionnel" 
ORDER BY "Nombre de fiches de poste en difficulté de recrutement" DESC, "public"."fiches_deposte_en_tension_recrutement"."domaine_professionnel" ASC
```

## [150] Carte des SIAE avec au moins une fiche de poste en difficulté de recrutement - Modifié

- **ID:** 4832
- **Dashboard:** 218
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
- **Dashboard:** 218
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
