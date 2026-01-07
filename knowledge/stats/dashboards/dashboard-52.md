# Dashboard : Candidatures - Zoom sur les prescripteurs

 💾 Source des données : les emplois de l'inclusion

### Qui sont les prescripteurs ?
-  Les **prescripteurs** regroupent les prescripteurs habilités et les orienteurs
- **[Les prescripteurs habilités](https://aide.emplois.inclusion.beta.gouv.fr/hc/fr/articles/14733442624657--Liste-des-prescripteurs-habilit%C3%A9s-au-national)**   : Ces professionnels proposent les candidatures des publics qu'ils accompagnent et sont autorisés à valider l'éligibilité à un parcours IAE d'un candidat. Parmi ces prescripteurs, il y a le SPE (service public de l'emploi) qui regroupe France Travail, la Mission locale et Cap emploi.
-  **[Les orienteurs](https://aide.emplois.inclusion.beta.gouv.fr/hc/fr/articles/14741018866449--Les-orienteurs)**  : Ces professionnels proposent les candidatures des publics qu'ils accompagnent mais ne valident pas l'éligibilité IAE du candidat, c'est la structure d'insertion qui se charge de vérifier cette éligibilité.

 Les données ci-dessous ne fonctionnent pas avec le filtre

**4 cartes**

## [52] % conseillers hors SPE

- **ID:** 7108
- **Thème:** prescripteurs
- **Tables:** public, organisations

```sql
SELECT CAST(SUM(CASE WHEN (("public"."organisations"."type" <> 'FT') 
OR ("public"."organisations"."type" IS NULL)) 
AND (("public"."organisations"."type" <> 'ML') 
OR ("public"."organisations"."type" IS NULL)) 
AND (("public"."organisations"."type" <> 'CAP_EMPLOI') 
OR ("public"."organisations"."type" IS NULL)) THEN "public"."organisations"."total_membres" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."organisations"."total_membres") AS DOUBLE PRECISION), 0.0) AS "% conseillers hors SPE" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL
```

## [52] % conseillers SPE

- **ID:** 7109
- **Thème:** prescripteurs
- **Tables:** public, organisations

```sql
SELECT CAST(SUM(CASE WHEN "public"."organisations"."type" = 'FT' THEN "public"."organisations"."total_membres" ELSE 0.0 END) + SUM(CASE WHEN "public"."organisations"."type" = 'ML' THEN "public"."organisations"."total_membres" ELSE 0.0 END) + SUM(CASE WHEN "public"."organisations"."type" = 'CAP_EMPLOI' THEN "public"."organisations"."total_membres" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."organisations"."total_membres") AS DOUBLE PRECISION), 0.0) AS "% conseillers SPE" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL
```

## [52] nombre total de conseillers inscrits

- **ID:** 7110
- **Thème:** prescripteurs
- **Tables:** public, organisations

```sql
SELECT SUM("public"."organisations"."total_membres") AS "Nombre total de conseillers inscrits" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL
```

## [52] Tableau des prescripteurs par type détaillé

- **ID:** 7112
- **Thème:** prescripteurs
- **Tables:** public, organisations

```sql
SELECT "public"."organisations"."type_complet" AS "type_complet", "public"."organisations"."nom" AS "nom", "public"."organisations"."ville" AS "ville", "public"."organisations"."code_postal" AS "code_postal", "public"."organisations"."adresse_ligne_1" AS "adresse_ligne_1", "public"."organisations"."région" AS "région", "public"."organisations"."nom_département" AS "nom_département", "public"."organisations"."date_inscription" AS "date_inscription", "public"."organisations"."type" AS "type", COUNT(*) AS "count", SUM("public"."organisations"."total_membres") AS "sum" 
FROM "public"."organisations" 
WHERE "public"."organisations"."date_inscription" IS NOT NULL 
GROUP BY "public"."organisations"."type_complet", "public"."organisations"."nom", "public"."organisations"."ville", "public"."organisations"."code_postal", "public"."organisations"."adresse_ligne_1", "public"."organisations"."région", "public"."organisations"."nom_département", "public"."organisations"."date_inscription", "public"."organisations"."type" 
ORDER BY "sum" DESC, "public"."organisations"."type_complet" ASC, "public"."organisations"."nom" ASC, "public"."organisations"."ville" ASC, "public"."organisations"."code_postal" ASC, "public"."organisations"."adresse_ligne_1" ASC, "public"."organisations"."région" ASC, "public"."organisations"."nom_département" ASC, "public"."organisations"."date_inscription" ASC, "public"."organisations"."type" ASC
```
