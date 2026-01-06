# Dashboard : Offre - Zoom sur les employeurs

 💾 Source des données : les emplois de l'inclusion

![](https://raw.githubusercontent.com/laurinehu/test/main/Capture%20d%E2%80%99e%CC%81cran%202024-06-20%20a%CC%80%2018.55.43.png)

#### Parmi tous les employeurs inscrits sur les emplois de l'inclusion nous recensons

- Des filtres en haut du tableau de bord vous permettent d'affiner les données affichées. Utilisez le filtre "Date" par exemple pour sélectionner des dates spécifiques
[Accéder au tutoriel pour savoir utiliser les filtres](https://aide.pilotage.inclusion.beta.gouv.fr/hc/fr/articles/16883264347921--Utiliser-les-filtres)

- Vous pouvez également exporter les données au format .xls (Excel) ou en .png (Image) afin de retraiter les données si vous le souhaitez ou d'utiliser les graphiques pour vos rapports et présentations.  [Accéder au tutoriel pour exporter sous format Excel ou image](https://aide.pilotage.inclusion.beta.gouv.fr/hc/fr/articles/16883028440593--Export-des-indicateurs-et-graphiques)

#### ☝️Attention
Les donnée

**1 cartes**

## [54] Répartition des employeurs et métiers - detaillé

- **ID:** 7237
- **Thème:** employeurs
- **Tables:** public, structures

```sql
SELECT "public"."structures"."type" AS "type", "public"."structures"."total_membres" AS "total_membres", "public"."structures"."date_inscription" AS "date_inscription", "public"."structures"."adresse_ligne_1" AS "adresse_ligne_1", "public"."structures"."ville" AS "ville", "public"."structures"."code_postal" AS "code_postal", "public"."structures"."nom_département" AS "nom_département", "public"."structures"."région" AS "région", "public"."structures"."nom" AS "nom", COUNT(*) AS "count", SUM("public"."structures"."total_fiches_de_poste_actives") AS "sum" FROM "public"."structures" WHERE ("public"."structures"."date_inscription" IS NOT NULL) AND (("public"."structures"."source" = 'Export ASP') OR ("public"."structures"."source" = 'Export EA+EATT') OR ("public"."structures"."source" = 'Export GEIQ')) GROUP BY "public"."structures"."type", "public"."structures"."total_membres", "public"."structures"."date_inscription", "public"."structures"."adresse_ligne_1", "public"."structures"."ville", "public"."structures"."code_postal", "public"."structures"."nom_département", "public"."structures"."région", "public"."structures"."nom" ORDER BY "public"."structures"."type" ASC, "public"."structures"."total_membres" ASC, "public"."structures"."date_inscription" ASC, "public"."structures"."adresse_ligne_1" ASC, "public"."structures"."ville" ASC, "public"."structures"."code_postal" ASC, "public"."structures"."nom_département" ASC, "public"."structures"."région" ASC, "public"."structures"."nom" ASC
```
