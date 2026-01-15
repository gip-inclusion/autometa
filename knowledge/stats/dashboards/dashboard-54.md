# Dashboard : Offre - Zoom sur les employeurs

**URL:** /tableaux-de-bord/zoom-employeurs/

**3 cartes**

## [54] Répartition des employeurs et métiers - detaillé

- **ID:** 2589
- **Thème:** employeurs
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

## [337] Nombre de structures mère

- **ID:** 3674
- **Thème:** employeurs
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
- **Thème:** employeurs
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
