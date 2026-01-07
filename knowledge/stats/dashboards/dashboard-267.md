# Dashboard : DDETS/DREETS - Les auto-prescription et suivi du contrôle à posteriori des structures de mon territoire

#### Les critères de niveau 1 renseignés
En savoir plus sur les critères d'éligibilité 👉​ [cliquez-ici](https://communaute.inclusion.beta.gouv.fr/doc/emplois/les-criteres-deligibilite/)

#### ☝️Attention
- Dans la partie "Critères de niveau 1" par exemple, nous comptabilisons le nombre de personnes dont l'auto-prescription a été validée par des critères de niveau 1. Si pour ces personnes des critères de niveau 2 avaient été remplies également, elles n'apparaissent pas dans la partie "critère de niveau 2", car ce sont bien les critères de niveau 1 qui ont permis de valider l'auto-prescription. 
- Les tableaux présentés dans cette partie sont construits à partir des données du processus "candidature" vers les SIAE. Lors de ce processus, **il n’est pas demandé aux SIAE de fournir des données exhaustives sur les profils des publics** (ex RQTH, QPV…). Par exemple, il peut-être mentionné qu’une personne est bRSA, mais pas qu’elle est également senior. Par conséquent, **les données que nous p

**URL:** /tableaux-de-bord/auto-prescription/

**15 cartes**

## [267] Nombre de personnes recrutées en autoprescription critères niv 2

- **ID:** 7004
- **Thème:** auto-prescription
- **Tables:** public, candidats_auto_prescription

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."candidats_auto_prescription" 
WHERE ((("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") <> 0) 
OR (("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") IS NULL)) 
AND ("public"."candidats_auto_prescription"."total_critères_niveau_1" = 0) 
AND ("public"."candidats_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."candidats_auto_prescription"."type_de_candidature" = 'Autoprescription')
```

## [267] Candidatures acceptées en auto prescription

- **ID:** 7006
- **Thème:** auto-prescription
- **Tables:** public, suivi_auto_prescription

```sql
SELECT COUNT(*) AS "Candidatures acceptées en auto-prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription') 
AND ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI'))
```

## [267] Détails critère de niveau 1

- **ID:** 7007
- **Thème:** auto-prescription
- **Tables:** public, candidats_auto_prescription

```sql
SELECT SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_allocataire_aah" = 1 THEN 1 ELSE 0.0 END) AS "Nombre AAH", CAST(SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_allocataire_aah" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% AAH", SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_allocataire_ass" = 1 THEN 1 ELSE 0.0 END) AS "Nombre ASS", CAST(SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_allocataire_ass" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% ASS", SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_bénéficiaire_du_rsa" = 1 THEN 1 ELSE 0.0 END) AS "Nombre bRSA", CAST(SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_bénéficiaire_du_rsa" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% bRSA", SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_detld_plus_de_24_mois" = 1 THEN 1 ELSE 0.0 END) AS "Nombre DETLD", CAST(SUM(CASE WHEN "public"."candidats_auto_prescription"."critère_n1_detld_plus_de_24_mois" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% DETLD", COUNT(*) AS "Total de candidats" 
FROM "public"."candidats_auto_prescription" 
WHERE ((("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") <> 0) 
OR (("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") IS NULL)) 
AND (("public"."candidats_auto_prescription"."total_critères_niveau_1" <> 0) 
OR ("public"."candidats_auto_prescription"."total_critères_niveau_1" IS NULL)) 
AND ("public"."candidats_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."candidats_auto_prescription"."type_de_candidature" = 'Autoprescription')
```

## [267] Candidatures acceptées (toutes)

- **ID:** 7008
- **Thème:** candidatures
- **Tables:** public, suivi_auto_prescription

```sql
SELECT COUNT(*) AS "Candidatures acceptées en auto-prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI'))
```

## [267] Candidats - Nombre de critères de niveau 2

- **ID:** 7010
- **Thème:** auto-prescription
- **Tables:** public, candidats_auto_prescription

```sql
SELECT "public"."candidats_auto_prescription"."total_critères_niveau_2" AS "total_critères_niveau_2", COUNT(*) AS "count" 
FROM "public"."candidats_auto_prescription" 
WHERE ((("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") <> 0) 
OR (("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") IS NULL)) 
AND ("public"."candidats_auto_prescription"."total_critères_niveau_1" = 0) 
AND ("public"."candidats_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."candidats_auto_prescription"."type_de_candidature" = 'Autoprescription') 
GROUP BY "public"."candidats_auto_prescription"."total_critères_niveau_2" 
ORDER BY "public"."candidats_auto_prescription"."total_critères_niveau_2" ASC
```

## [267] % Embauches en auto prescription

- **ID:** 7012
- **Thème:** auto-prescription
- **Tables:** public, suivi_auto_prescription

```sql
SELECT CAST(SUM(CASE WHEN "public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% embauches en auto-prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI'))
```

## [267] % de structures pratiquant l'auto prescription

- **ID:** 7013
- **Thème:** auto-prescription
- **Tables:** public, siae_pratiquant_autoprescription

```sql
SELECT CAST(SUM("public"."siae_pratiquant_autoprescription"."Nombre de structures utilisant l'autoprescription") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."siae_pratiquant_autoprescription"."Nombre total de structures") AS DOUBLE PRECISION), 0.0) AS "% de Siae pratiquant l'auto prescription" 
FROM "public"."siae_pratiquant_autoprescription" 
WHERE ("public"."siae_pratiquant_autoprescription"."type_structure" = 'ACI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'AI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'EI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'ETTI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'EITI')
```

## [267] Nombre de personnes recrutées en autoprescription critères niv 1

- **ID:** 7016
- **Thème:** auto-prescription
- **Tables:** public, candidats_auto_prescription

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."candidats_auto_prescription" 
WHERE ((("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") <> 0) 
OR (("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") IS NULL)) 
AND (("public"."candidats_auto_prescription"."total_critères_niveau_1" <> 0) 
OR ("public"."candidats_auto_prescription"."total_critères_niveau_1" IS NULL)) 
AND ("public"."candidats_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."candidats_auto_prescription"."type_de_candidature" = 'Autoprescription')
```

## [267] Nombre candidats concernés auto-prescription

- **ID:** 7017
- **Thème:** auto-prescription
- **Tables:** public, candidats_auto_prescription

```sql
SELECT COUNT(*) AS "Candidats concernés par l'auto-prescription" 
FROM "public"."candidats_auto_prescription" 
WHERE ((("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") <> 0) 
OR (("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") IS NULL)) 
AND ("public"."candidats_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."candidats_auto_prescription"."type_de_candidature" = 'Autoprescription')
```

## [267] Candidats - Nombre de critères de niveau 1 (w/ 0)

- **ID:** 7018
- **Thème:** auto-prescription
- **Tables:** public, candidats_auto_prescription

```sql
SELECT "public"."candidats_auto_prescription"."total_critères_niveau_1" AS "total_critères_niveau_1", COUNT(*) AS "count" 
FROM "public"."candidats_auto_prescription" 
WHERE ((("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") <> 0) 
OR (("public"."candidats_auto_prescription"."total_critères_niveau_1" + "public"."candidats_auto_prescription"."total_critères_niveau_2") IS NULL)) 
AND ("public"."candidats_auto_prescription"."état" = 'Candidature acceptée') 
AND ("public"."candidats_auto_prescription"."type_de_candidature" = 'Autoprescription') 
GROUP BY "public"."candidats_auto_prescription"."total_critères_niveau_1" 
ORDER BY "public"."candidats_auto_prescription"."total_critères_niveau_1" ASC
```

## [267] Nombre total de SIAE

- **ID:** 7019
- **Thème:** employeurs
- **Tables:** public, siae_pratiquant_autoprescription

```sql
SELECT SUM("public"."siae_pratiquant_autoprescription"."Nombre total de structures") AS "sum" 
FROM "public"."siae_pratiquant_autoprescription" 
WHERE ("public"."siae_pratiquant_autoprescription"."type_structure" = 'ACI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'AI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'EI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'EITI') 
OR ("public"."siae_pratiquant_autoprescription"."type_structure" = 'ETTI')
```

## [267] Nombre de SIAE pratiquant l'auto prescription

- **ID:** 7020
- **Thème:** auto-prescription
- **Tables:** public, siae_pratiquant_autoprescription

```sql
SELECT SUM("public"."siae_pratiquant_autoprescription"."Nombre de structures utilisant l'autoprescription") AS "sum" 
FROM "public"."siae_pratiquant_autoprescription"
```

## [267] Taux d'auto presciption par type de structure

- **ID:** 7021
- **Thème:** auto-prescription
- **Tables:** public, suivi_auto_prescription

```sql
SELECT "public"."suivi_auto_prescription"."type_structure" AS "type_structure", COUNT(*) AS "Nombre total de candidatures acceptées", CAST(SUM(CASE WHEN "public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux d'auto prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI')) 
GROUP BY "public"."suivi_auto_prescription"."type_structure" 
ORDER BY "public"."suivi_auto_prescription"."type_structure" ASC
```

## [267] Evolution du taux d'auto presciption dans le temps

- **ID:** 7022
- **Thème:** auto-prescription
- **Tables:** public, suivi_auto_prescription

```sql
SELECT CAST(DATE_TRUNC('month', "public"."suivi_auto_prescription"."date_diagnostic") AS date) AS "date_diagnostic", COUNT(*) AS "Nombre total de candidatures acceptées", CAST(SUM(CASE WHEN "public"."suivi_auto_prescription"."type_de_candidature" = 'Autoprescription' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux d'auto prescription" 
FROM "public"."suivi_auto_prescription" 
WHERE ("public"."suivi_auto_prescription"."état" = 'Candidature acceptée') 
AND (("public"."suivi_auto_prescription"."type_structure" = 'ACI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'AI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'ETTI') 
OR ("public"."suivi_auto_prescription"."type_structure" = 'EITI')) 
GROUP BY CAST(DATE_TRUNC('month', "public"."suivi_auto_prescription"."date_diagnostic") AS date) 
ORDER BY CAST(DATE_TRUNC('month', "public"."suivi_auto_prescription"."date_diagnostic") AS date) ASC
```

## [267] Détails critère de niveau 2

- **ID:** 7023
- **Thème:** auto-prescription

```sql
[No SQL in native_form]
```
