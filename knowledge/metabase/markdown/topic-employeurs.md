# Thème : employeurs

*SIAE and employer information*

**14 cartes**

## [267] Nombre total de SIAE

- **ID:** 7019
- **Dashboard:** 267
- **Tables:** public, siae_pratiquant_autoprescription

```sql
SELECT SUM("public"."siae_pratiquant_autoprescription"."Nombre total de structures") AS "sum" FROM "public"."siae_pratiquant_autoprescription" WHERE ("public"."siae_pratiquant_autoprescription"."type_structure" = 'ACI') OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'AI') OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'EI') OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'EITI') OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'ETTI')
```

## [337] Nombre de structures antenne

- **ID:** 7028
- **Dashboard:** 337
- **Tables:** public, structures

```sql
SELECT COUNT(*) AS "count" FROM "public"."structures" WHERE ("public"."structures"."date_inscription" IS NOT NULL) AND ("public"."structures"."source" = 'Utilisateur (Antenne)') AND (("public"."structures"."type" = 'ACI') OR ("public"."structures"."type" = 'AI') OR ("public"."structures"."type" = 'EI') OR ("public"."structures"."type" = 'EITI') OR ("public"."structures"."type" = 'ETTI')) AND (("public"."structures"."type" = 'AI') OR ("public"."structures"."type" = 'ACI') OR ("public"."structures"."type" = 'EI') OR ("public"."structures"."type" = 'EITI') OR ("public"."structures"."type" = 'ETTI'))
```

## Nombre de fiches de postes ouverts par les SIAE

- **ID:** 7047
- **Tables:** public, fiches_de_poste

```sql
SELECT COUNT(*) AS "count" FROM "public"."fiches_de_poste" WHERE (("public"."fiches_de_poste"."type_employeur" = 'ACI') OR ("public"."fiches_de_poste"."type_employeur" = 'AI') OR ("public"."fiches_de_poste"."type_employeur" = 'EI') OR ("public"."fiches_de_poste"."type_employeur" = 'EITI') OR ("public"."fiches_de_poste"."type_employeur" = 'ETTI')) AND ("public"."fiches_de_poste"."recrutement_ouvert" = 1)
```

## [337] Nombre de structures mère

- **ID:** 7048
- **Dashboard:** 337
- **Tables:** public, structures

```sql
SELECT COUNT(*) AS "count" FROM "public"."structures" WHERE ("public"."structures"."date_inscription" IS NOT NULL) AND (("public"."structures"."source" = 'Export ASP') OR ("public"."structures"."source" = 'Staff Itou')) AND (("public"."structures"."type" = 'ACI') OR ("public"."structures"."type" = 'AI') OR ("public"."structures"."type" = 'EI') OR ("public"."structures"."type" = 'EITI') OR ("public"."structures"."type" = 'ETTI'))
```

## % de SIAE ayant accepté une candidature sur les 30 derniers jours

- **ID:** 7055
- **Tables:** public, structures

```sql
SELECT CAST(SUM(CASE WHEN ("public"."structures"."total_embauches_30j" <> 0) OR ("public"."structures"."total_embauches_30j" IS NULL) THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression" FROM "public"."structures" WHERE ("public"."structures"."date_inscription" IS NOT NULL) AND (("public"."structures"."type" = 'ACI') OR ("public"."structures"."type" = 'AI') OR ("public"."structures"."type" = 'EI') OR ("public"."structures"."type" = 'EITI') OR ("public"."structures"."type" = 'ETTI')) AND (("public"."structures"."type" = 'AI') OR ("public"."structures"."type" = 'ACI') OR ("public"."structures"."type" = 'EI') OR ("public"."structures"."type" = 'EITI') OR ("public"."structures"."type" = 'ETTI'))
```

## [337] Nombre total (mère + antenne) de structures sur les emplois

- **ID:** 7057
- **Dashboard:** 337
- **Tables:** public, structures

```sql
SELECT COUNT(*) AS "count" FROM "public"."structures" WHERE ("public"."structures"."date_inscription" IS NOT NULL) AND (("public"."structures"."source" = 'Utilisateur (Antenne)') OR ("public"."structures"."source" = 'Export ASP') OR ("public"."structures"."source" = 'Staff Itou')) AND (("public"."structures"."type" = 'ACI') OR ("public"."structures"."type" = 'AI') OR ("public"."structures"."type" = 'EI') OR ("public"."structures"."type" = 'EITI') OR ("public"."structures"."type" = 'ETTI')) AND (("public"."structures"."type" = 'AI') OR ("public"."structures"."type" = 'ACI') OR ("public"."structures"."type" = 'EI') OR ("public"."structures"."type" = 'EITI') OR ("public"."structures"."type" = 'ETTI'))
```

## Carto de la répartition des SIAE

- **ID:** 7058
- **Tables:** public, structures

```sql
SELECT "public"."structures"."département" AS "département", COUNT(*) AS "count" FROM "public"."structures" WHERE ("public"."structures"."date_inscription" IS NOT NULL) AND (("public"."structures"."source" = 'Export ASP') OR ("public"."structures"."source" = 'Export EA+EATT') OR ("public"."structures"."source" = 'Export GEIQ') OR ("public"."structures"."source" = 'Utilisateur (OPCS)') OR ("public"."structures"."source" = 'Staff Itou (OPCS)')) AND (("public"."structures"."type" = 'ACI') OR ("public"."structures"."type" = 'AI') OR ("public"."structures"."type" = 'EI') OR ("public"."structures"."type" = 'EITI') OR ("public"."structures"."type" = 'ETTI')) GROUP BY "public"."structures"."département" ORDER BY "count" DESC, "public"."structures"."département" ASC
```

## Répartition SIAE par type

- **ID:** 7065
- **Tables:** public, structures

```sql
SELECT "public"."structures"."type" AS "type", COUNT(*) AS "count" FROM "public"."structures" WHERE ("public"."structures"."date_inscription" IS NOT NULL) AND (("public"."structures"."source" = 'Export ASP') OR ("public"."structures"."source" = 'Staff Itou')) AND (("public"."structures"."type" = 'ACI') OR ("public"."structures"."type" = 'AI') OR ("public"."structures"."type" = 'EI') OR ("public"."structures"."type" = 'EITI') OR ("public"."structures"."type" = 'ETTI')) GROUP BY "public"."structures"."type" ORDER BY "count" DESC, "public"."structures"."type" ASC
```

## % de SIAE avec un poste ouvert

- **ID:** 7069
- **Tables:** public, structures

```sql
SELECT CAST(SUM(CASE WHEN ("public"."structures"."total_fiches_de_poste_actives" <> 0) OR ("public"."structures"."total_fiches_de_poste_actives" IS NULL) THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression" FROM "public"."structures" WHERE ("public"."structures"."date_inscription" IS NOT NULL) AND ("public"."structures"."categorie_structure" = 'IAE') AND (("public"."structures"."type" = 'AI') OR ("public"."structures"."type" = 'ACI') OR ("public"."structures"."type" = 'EI') OR ("public"."structures"."type" = 'EITI') OR ("public"."structures"."type" = 'ETTI'))
```

## [337] Nombre de structures antenne

- **ID:** 7235
- **Dashboard:** 337
- **Tables:** public, structures

```sql
SELECT COUNT(*) AS "count" FROM "public"."structures" WHERE ("public"."structures"."date_inscription" IS NOT NULL) AND ("public"."structures"."source" = 'Utilisateur (Antenne)') AND (("public"."structures"."type" = 'ACI') OR ("public"."structures"."type" = 'AI') OR ("public"."structures"."type" = 'EI') OR ("public"."structures"."type" = 'EITI') OR ("public"."structures"."type" = 'ETTI')) AND (("public"."structures"."type" = 'AI') OR ("public"."structures"."type" = 'ACI') OR ("public"."structures"."type" = 'EI') OR ("public"."structures"."type" = 'EITI') OR ("public"."structures"."type" = 'ETTI'))
```

## [337] Nombre de structures mère

- **ID:** 7236
- **Dashboard:** 337
- **Tables:** public, structures

```sql
SELECT COUNT(*) AS "count" FROM "public"."structures" WHERE ("public"."structures"."date_inscription" IS NOT NULL) AND (("public"."structures"."source" = 'Export ASP') OR ("public"."structures"."source" = 'Staff Itou')) AND (("public"."structures"."type" = 'ACI') OR ("public"."structures"."type" = 'AI') OR ("public"."structures"."type" = 'EI') OR ("public"."structures"."type" = 'EITI') OR ("public"."structures"."type" = 'ETTI'))
```

## [54] Répartition des employeurs et métiers - detaillé

- **ID:** 7237
- **Dashboard:** 54
- **Tables:** public, structures

```sql
SELECT "public"."structures"."type" AS "type", "public"."structures"."total_membres" AS "total_membres", "public"."structures"."date_inscription" AS "date_inscription", "public"."structures"."adresse_ligne_1" AS "adresse_ligne_1", "public"."structures"."ville" AS "ville", "public"."structures"."code_postal" AS "code_postal", "public"."structures"."nom_département" AS "nom_département", "public"."structures"."région" AS "région", "public"."structures"."nom" AS "nom", COUNT(*) AS "count", SUM("public"."structures"."total_fiches_de_poste_actives") AS "sum" FROM "public"."structures" WHERE ("public"."structures"."date_inscription" IS NOT NULL) AND (("public"."structures"."source" = 'Export ASP') OR ("public"."structures"."source" = 'Export EA+EATT') OR ("public"."structures"."source" = 'Export GEIQ')) GROUP BY "public"."structures"."type", "public"."structures"."total_membres", "public"."structures"."date_inscription", "public"."structures"."adresse_ligne_1", "public"."structures"."ville", "public"."structures"."code_postal", "public"."structures"."nom_département", "public"."structures"."région", "public"."structures"."nom" ORDER BY "public"."structures"."type" ASC, "public"."structures"."total_membres" ASC, "public"."structures"."date_inscription" ASC, "public"."structures"."adresse_ligne_1" ASC, "public"."structures"."ville" ASC, "public"."structures"."code_postal" ASC, "public"."structures"."nom_département" ASC, "public"."structures"."région" ASC, "public"."structures"."nom" ASC
```

## Nombre de fdp ouvertes par SIAE

- **ID:** 7288
- **Tables:** public, fiches_de_poste

```sql
SELECT "source"."type_employeur" AS "type_employeur", COUNT(*) AS "count" FROM (SELECT "public"."fiches_de_poste"."id" AS "id", "public"."fiches_de_poste"."code_rome" AS "code_rome", "public"."fiches_de_poste"."nom_rome" AS "nom_rome", "public"."fiches_de_poste"."recrutement_ouvert" AS "recrutement_ouvert", "public"."fiches_de_poste"."type_contrat" AS "type_contrat", "public"."fiches_de_poste"."id_employeur" AS "id_employeur", "public"."fiches_de_poste"."type_employeur" AS "type_employeur", "public"."fiches_de_poste"."siret_employeur" AS "siret_employeur", "public"."fiches_de_poste"."nom_employeur" AS "nom_employeur", "public"."fiches_de_poste"."mises_a_jour_champs" AS "mises_a_jour_champs", "public"."fiches_de_poste"."département_employeur" AS "département_employeur", "public"."fiches_de_poste"."nom_département_employeur" AS "nom_département_employeur", "public"."fiches_de_poste"."région_employeur" AS "région_employeur", "public"."fiches_de_poste"."total_candidatures" AS "total_candidatures", "public"."fiches_de_poste"."date_création" AS "date_création", "public"."fiches_de_poste"."date_dernière_modification" AS "date_dernière_modification", "public"."fiches_de_poste"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" FROM "public"."fiches_de_poste") AS "source" WHERE ("source"."recrutement_ouvert" = 1) AND (("source"."type_employeur" = 'ACI') OR ("source"."type_employeur" = 'AI') OR ("source"."type_employeur" = 'EITI') OR ("source"."type_employeur" = 'EI') OR ("source"."type_employeur" = 'ETTI')) GROUP BY "source"."type_employeur" ORDER BY "source"."type_employeur" ASC
```

## [408] Nombre de fdp ouvertes

- **ID:** 7304
- **Dashboard:** 408
- **Tables:** public, fiches_de_poste

```sql
SELECT COUNT(*) AS "count" FROM (SELECT "public"."fiches_de_poste"."id" AS "id", "public"."fiches_de_poste"."code_rome" AS "code_rome", "public"."fiches_de_poste"."nom_rome" AS "nom_rome", "public"."fiches_de_poste"."recrutement_ouvert" AS "recrutement_ouvert", "public"."fiches_de_poste"."type_contrat" AS "type_contrat", "public"."fiches_de_poste"."id_employeur" AS "id_employeur", "public"."fiches_de_poste"."type_employeur" AS "type_employeur", "public"."fiches_de_poste"."siret_employeur" AS "siret_employeur", "public"."fiches_de_poste"."nom_employeur" AS "nom_employeur", "public"."fiches_de_poste"."mises_a_jour_champs" AS "mises_a_jour_champs", "public"."fiches_de_poste"."département_employeur" AS "département_employeur", "public"."fiches_de_poste"."nom_département_employeur" AS "nom_département_employeur", "public"."fiches_de_poste"."région_employeur" AS "région_employeur", "public"."fiches_de_poste"."total_candidatures" AS "total_candidatures", "public"."fiches_de_poste"."date_création" AS "date_création", "public"."fiches_de_poste"."date_dernière_modification" AS "date_dernière_modification", "public"."fiches_de_poste"."date_mise_à_jour_metabase" AS "date_mise_à_jour_metabase" FROM "public"."fiches_de_poste") AS "source" WHERE ("source"."recrutement_ouvert" = 1) AND (("source"."type_employeur" = 'ACI') OR ("source"."type_employeur" = 'AI') OR ("source"."type_employeur" = 'EITI') OR ("source"."type_employeur" = 'EI') OR ("source"."type_employeur" = 'ETTI'))
```
