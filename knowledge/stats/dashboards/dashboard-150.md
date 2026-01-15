# Dashboard : Offre - Postes en tension

Une fiche de poste est considérée en tension si elle rempli les 4 conditions suivantes :
- elle est active (l'employeur a déclaré sur les emplois de l'inclusion que le recrutement est ouvert sur cette fiche de poste)
-  elle est sans recrutement sur les 30 derniers jours (fiches de poste sans candidatures sur les 30 derniers jours ou avec des candidatures mais sans recrutement) et a été publiée depuis plus de 30 jours (En moyenne une fiche de poste reçoit une première candidature 30 jours après sa création. Toutes les fiches de poste qui ont au moins 30 jours d'ancienneté font partie du périmètre de l'analyse)
 - et l’employeur n'a pas refusé des candidatures dans les 30 derniers jours pour le motif “Pas de poste ouvert”


**URL:** /tableaux-de-bord/postes-en-tension/

**6 cartes**

## [150] Nombre de fiches de poste en difficulté de recrutement n'ayant jamais reçu de candidature

- **ID:** 1411
- **Thème:** postes-tension
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT SUM("public"."fiches_deposte_en_tension_recrutement"."valeur") AS "Nombre de fiches de poste en difficulté de recrutement" 
FROM "public"."fiches_deposte_en_tension_recrutement" 
WHERE "public"."fiches_deposte_en_tension_recrutement"."etape" = '6- Fiches de poste en difficulté de recrutement n ayant jamais reçu de candidatures'
```

## [150] % fiches de poste en difficulté de recrutement sans candidature

- **ID:** 1421
- **Thème:** postes-tension
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT CAST(SUM(CASE WHEN "public"."fiches_deposte_en_tension_recrutement"."etape" = '6- Fiches de poste en difficulté de recrutement n ayant jamais reçu de candidatures' THEN "public"."fiches_deposte_en_tension_recrutement"."valeur" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."fiches_deposte_en_tension_recrutement"."etape" = '2- Fiches de poste actives' THEN "public"."fiches_deposte_en_tension_recrutement"."valeur" ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "% fiches de poste en difficulté de recrutement san_cb86b9fc" 
FROM "public"."fiches_deposte_en_tension_recrutement"
```

## [150] % FDP en difficulté de recrutement

- **ID:** 2485
- **Thème:** postes-tension
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT CAST(SUM(CASE WHEN "public"."fiches_deposte_en_tension_recrutement"."etape" = '5- Fiches de poste en difficulté de recrutement' THEN "public"."fiches_deposte_en_tension_recrutement"."valeur" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."fiches_deposte_en_tension_recrutement"."etape" = '2- Fiches de poste actives' THEN "public"."fiches_deposte_en_tension_recrutement"."valeur" ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "% fiches de poste en difficulté de recrutement " 
FROM "public"."fiches_deposte_en_tension_recrutement"
```

## [150] Nombre de SIAE avec au moins une fiche de poste en difficulté de recrutement sans candidature

- **ID:** 2486
- **Thème:** postes-tension
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT count(distinct "public"."fiches_deposte_en_tension_recrutement"."id_structure") AS "Nombre de SIAE avec au moins une fiche de poste en _0a37a889" 
FROM "public"."fiches_deposte_en_tension_recrutement" 
WHERE ("public"."fiches_deposte_en_tension_recrutement"."etape" = '6- Fiches de poste en difficulté de recrutement n ayant jamais reçu de candidatures') 
AND ("public"."fiches_deposte_en_tension_recrutement"."valeur" > 0)
```

## [150] Nombre de fiches de poste en difficulté de recrutement n'ayant jamais reçu de candidature par grand domaine

- **ID:** 3683
- **Thème:** postes-tension
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
- **Thème:** postes-tension
- **Tables:** fiches_deposte_en_tension_recrutement

```sql
SELECT "public"."fiches_deposte_en_tension_recrutement"."domaine_professionnel" AS "domaine_professionnel", SUM("public"."fiches_deposte_en_tension_recrutement"."valeur") AS "Nombre de fiches de poste en difficulté de recrutement" 
FROM "public"."fiches_deposte_en_tension_recrutement" 
WHERE "public"."fiches_deposte_en_tension_recrutement"."etape" = '6- Fiches de poste en difficulté de recrutement n ayant jamais reçu de candidatures' 
GROUP BY "public"."fiches_deposte_en_tension_recrutement"."domaine_professionnel" 
ORDER BY "Nombre de fiches de poste en difficulté de recrutement" DESC, "public"."fiches_deposte_en_tension_recrutement"."domaine_professionnel" ASC
```
