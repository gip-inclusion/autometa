# Thème : controles

*Control and compliance*

**6 cartes**

## [265] description critères refusés 

- **ID:** 7005
- **Dashboard:** 265
- **Tables:** public, suivi_cap_criteres

```sql
SELECT "public"."suivi_cap_criteres"."nom_critère" AS "nom_critère", COUNT(*) AS "count" FROM "public"."suivi_cap_criteres" WHERE "public"."suivi_cap_criteres"."état" = 'Refusé' GROUP BY "public"."suivi_cap_criteres"."nom_critère" ORDER BY "public"."suivi_cap_criteres"."nom_critère" ASC
```

## [265] Etat contrôle critères

- **ID:** 7009
- **Dashboard:** 265
- **Tables:** public, suivi_cap_criteres

```sql
SELECT "public"."suivi_cap_criteres"."nom_critère" AS "nom_critère", "public"."suivi_cap_criteres"."état" AS "état", COUNT(*) AS "count" FROM "public"."suivi_cap_criteres" GROUP BY "public"."suivi_cap_criteres"."nom_critère", "public"."suivi_cap_criteres"."état" ORDER BY "public"."suivi_cap_criteres"."nom_critère" ASC, "public"."suivi_cap_criteres"."état" ASC
```

## [265] % SIAE contrôlées parmi les SIAE à contrôler - v2

- **ID:** 7011
- **Dashboard:** 265
- **Tables:** suivi_cap_structures, public, cap_structures, cap_campagnes

```sql
SELECT CAST(count(distinct CASE WHEN "Suivi Cap Structures - ID Structure"."état" = 'ACCEPTED' THEN "public"."cap_structures"."id_structure" WHEN "Suivi Cap Structures - ID Structure"."état" = 'REFUSED' THEN "public"."cap_structures"."id_structure" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "public"."cap_structures"."id_structure") AS DOUBLE PRECISION), 0.0) AS "% ctrl terminés" FROM "public"."cap_structures" LEFT JOIN "public"."cap_campagnes" AS "Cap Campagnes - ID Cap Campagne" ON "public"."cap_structures"."id_cap_campagne" = "Cap Campagnes - ID Cap Campagne"."id" LEFT JOIN "public"."suivi_cap_structures" AS "Suivi Cap Structures - ID Structure" ON "public"."cap_structures"."id_structure" = "Suivi Cap Structures - ID Structure"."id_structure"
```

## [265] part SIAE ctrlées pos vs neg

- **ID:** 7014
- **Dashboard:** 265
- **Tables:** public, cap_structures, cap_campagnes, structures

```sql
SELECT "source"."état_2" AS "état", COUNT(*) AS "count" FROM (SELECT "public"."cap_structures"."id_cap_campagne" AS "id_cap_campagne", "public"."cap_structures"."id_structure" AS "id_structure", "public"."cap_structures"."état" AS "état", CASE WHEN "public"."cap_structures"."état" = 'ACCEPTED' THEN 'Résultats positifs' WHEN "public"."cap_structures"."état" = 'REFUSED' THEN 'Résultats négatifs' WHEN "public"."cap_structures"."état" = 'NOTIFICATION_PENDING' THEN 'Résultats négatifs' END AS "état_2", "Structures"."id" AS "Structures__id", "Structures"."id_asp" AS "Structures__id_asp", "Structures"."nom" AS "Structures__nom", "Structures"."nom_complet" AS "Structures__nom_complet", "Structures"."description" AS "Structures__description", "Structures"."type" AS "Structures__type", "Structures"."siret" AS "Structures__siret", "Structures"."code_naf" AS "Structures__code_naf", "Structures"."email_public" AS "Structures__email_public", "Structures"."email_authentification" AS "Structures__email_authentification", "Structures"."convergence_france" AS "Structures__convergence_france", "Structures"."adresse_ligne_1" AS "Structures__adresse_ligne_1", "Structures"."adresse_ligne_2" AS "Structures__adresse_ligne_2", "Structures"."code_postal" AS "Structures__code_postal", "Structures"."code_commune" AS "Structures__code_commune", "Structures"."longitude" AS "Structures__longitude", "Structures"."latitude" AS "Structures__latitude", "Structures"."département" AS "Structures__département", "Structures"."nom_département" AS "Structures__nom_département", "Structures"."région" AS "Structures__région", "Structures"."adresse_ligne_1_c1" AS "Structures__adresse_ligne_1_c1", "Structures"."adresse_ligne_2_c1" AS "Structures__adresse_ligne_2_c1", "Structures"."code_postal_c1" AS "Structures__code_postal_c1", "Structures"."code_commune_c1" AS "Structures__code_commune_c1", "Structures"."ville_c1" AS "Structures__ville_c1", "Structures"."longitude_c1" AS "Structures__longitude_c1", "Structur
-- ... (truncated)
```

## [265] SIAE à contrôler

- **ID:** 7015
- **Dashboard:** 265
- **Tables:** public, cap_structures, cap_campagnes

```sql
SELECT count(distinct "public"."cap_structures"."id_structure") AS "structures à contrôler" FROM "public"."cap_structures" LEFT JOIN "public"."cap_campagnes" AS "Cap Campagnes" ON "public"."cap_structures"."id_cap_campagne" = "Cap Campagnes"."id"
```

## [265] Nb de structures dont le contrôle est terminé

- **ID:** 7024
- **Dashboard:** 265
- **Tables:** public, suivi_cap_structures

```sql
SELECT count(distinct "public"."suivi_cap_structures"."id_structure") AS "Nb structures contrôlées" FROM "public"."suivi_cap_structures" WHERE ("public"."suivi_cap_structures"."état" = 'ACCEPTED') OR ("public"."suivi_cap_structures"."état" = 'REFUSED')
```
