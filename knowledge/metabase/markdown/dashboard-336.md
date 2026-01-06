# Dashboard : Pilotage dispositif - Demandes de prolongation

# 1. Vue d'ensemble des demandes de prolongation

# 2. Demandes envoyées aux prescripteurs

## 2.a Chiffres clés

## 2.b Etat et suivi des demandes 

Les demandes "à traiter" et "refusée" ci dessous concernent tous les PASS, même ceux expirant après la semaine du 27 novembre

## 2.c Répartition par prescripteurs

Exemple fictif : La semaine du 14 août, 293 demandes de prolongation ont été envoyées. Au moment où je consulte cet indicateur (le 14 septembre), 12 ont le statut "à traiter".  Cette situation évolue au fur et à mesure du temps. 

### ⚠️​  Conseils d'utilisation importants
- Ce tableau de bord est proposé par Pilotage de l'inclusion, à partir des données des Emplois de l'Inclusion. 
Pour plus d'information sur le mécanisme des prolongations, consulter [la documentation des emplois de l'inclusion ](https://aide.emplois.inclusion.beta.gouv.fr/hc/fr/articles/14738994643217--Prolonger-un-PASS-IAE#:~:text=La%20SIAE%20enregistre%20la%20demande,accord%20d'un%20prescripteur%20habilit%

**URL:** /tableaux-de-bord/suivi-demandes-prolongation/

**21 cartes**

## [336] Motif de refus des demandes

- **ID:** 7257
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT "public"."suivi_demandes_prolongations"."motif_de_refus" AS "motif_de_refus", COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) AND ("public"."suivi_demandes_prolongations"."état" = 'Refusée') AND ("public"."suivi_demandes_prolongations"."date_de_demande" IS NOT NULL) GROUP BY "public"."suivi_demandes_prolongations"."motif_de_refus" ORDER BY "public"."suivi_demandes_prolongations"."motif_de_refus" ASC
```

## [336] Nombre de demandes de prolongation refusées (prescripteurs)

- **ID:** 7258
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) AND ("public"."suivi_demandes_prolongations"."état" = 'Refusée') AND ("public"."suivi_demandes_prolongations"."date_de_demande" IS NOT NULL) AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Nombre de demandes de prolongation acceptées (prescripteurs)

- **ID:** 7259
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE (("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') OR ("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) AND ("public"."suivi_demandes_prolongations"."état" = 'Acceptée') AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Nombre de demandes de prolongation envoyées aux prescripteurs

- **ID:** 7260
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Nombre des demandes envoyées aux prescripteurs par semaine

- **ID:** 7261
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT "public"."suivi_demandes_prolongations"."état" AS "état", CAST(DATE_TRUNC('week', "public"."suivi_demandes_prolongations"."date_de_demande") AS date) AS "date_de_demande", COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25') GROUP BY "public"."suivi_demandes_prolongations"."état", CAST(DATE_TRUNC('week', "public"."suivi_demandes_prolongations"."date_de_demande") AS date) ORDER BY "public"."suivi_demandes_prolongations"."état" ASC, CAST(DATE_TRUNC('week', "public"."suivi_demandes_prolongations"."date_de_demande") AS date) ASC
```

## [336] Répartition des demandes par type de prescripteur habilité

- **ID:** 7262
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT "public"."suivi_demandes_prolongations"."type_prescripteur" AS "type_prescripteur", COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25') GROUP BY "public"."suivi_demandes_prolongations"."type_prescripteur" ORDER BY "public"."suivi_demandes_prolongations"."type_prescripteur" ASC
```

## [336] Nombre de demandes de prolongation

- **ID:** 7263
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations"
```

## [336] Proportion de demandes de prolongation refusées (prescripteurs)

- **ID:** 7264
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT CAST(SUM(CASE WHEN "public"."suivi_demandes_prolongations"."état" = 'Refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de demandes refusées " FROM "public"."suivi_demandes_prolongations" WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) AND ("public"."suivi_demandes_prolongations"."date_de_demande" IS NOT NULL) AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Proportion de demandes de prolongation acceptées (prescripteurs)

- **ID:** 7265
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT CAST(SUM(CASE WHEN "public"."suivi_demandes_prolongations"."état" = 'Acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de demandes acceptées" FROM "public"."suivi_demandes_prolongations" WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Nombre de demandes ayant été traitées en plus de 30j

- **ID:** 7266
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulières qui font obstacle à l''insertion durable dans l’emploi') OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé')) AND ("public"."suivi_demandes_prolongations"."date_de_demande" IS NOT NULL) AND ("public"."suivi_demandes_prolongations"."delai_traitement" > 30)
```

## [336] Demandes de prolongations validées directement par les SIAE

- **ID:** 7268
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE (("public"."suivi_demandes_prolongations"."motif" <> '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) AND (("public"."suivi_demandes_prolongations"."motif" <> 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle') OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) AND (("public"."suivi_demandes_prolongations"."motif" <> 'RQTH - Reconnaissance de la qualité de travailleur handicapé') OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Distribution des demandes de prolongations acceptées par les SIAE

- **ID:** 7269
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT "public"."suivi_demandes_prolongations"."motif" AS "motif", COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE (("public"."suivi_demandes_prolongations"."motif" <> '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) AND (("public"."suivi_demandes_prolongations"."motif" <> 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle') OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) AND (("public"."suivi_demandes_prolongations"."motif" <> 'RQTH - Reconnaissance de la qualité de travailleur handicapé') OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25') GROUP BY "public"."suivi_demandes_prolongations"."motif" ORDER BY "public"."suivi_demandes_prolongations"."motif" ASC
```

## [336] Demandes de prolongations acceptées par les SIAE

- **ID:** 7270
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE (("public"."suivi_demandes_prolongations"."motif" <> '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) AND (("public"."suivi_demandes_prolongations"."motif" <> 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle') OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) AND (("public"."suivi_demandes_prolongations"."motif" <> 'RQTH - Reconnaissance de la qualité de travailleur handicapé') OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Nombre de prolongations avant le 26 juillet

- **ID:** 7271
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE "public"."suivi_demandes_prolongations"."date_de_création" < date '2023-07-26'
```

## [336] Nombre de demandes à traiter ayant plus de 30j

- **ID:** 7272
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulières qui font obstacle à l''insertion durable dans l’emploi') OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé')) AND ("public"."suivi_demandes_prolongations"."date_de_demande" IS NOT NULL) AND ("public"."suivi_demandes_prolongations"."duree_depuis_demande" > 30) AND ("public"."suivi_demandes_prolongations"."état" = 'À traiter')
```

## [336] Nombre de demandes de prolongation par motif (tous motifs)

- **ID:** 7273
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT "public"."suivi_demandes_prolongations"."motif" AS "motif", COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" GROUP BY "public"."suivi_demandes_prolongations"."motif" ORDER BY "public"."suivi_demandes_prolongations"."motif" ASC
```

## [336] Nombre des demandes envoyées aux prescripteurs par mois

- **ID:** 7274
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT "public"."suivi_demandes_prolongations"."état" AS "état", CAST(DATE_TRUNC('month', "public"."suivi_demandes_prolongations"."date_de_demande") AS date) AS "date_de_demande", COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE ("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle') GROUP BY "public"."suivi_demandes_prolongations"."état", CAST(DATE_TRUNC('month', "public"."suivi_demandes_prolongations"."date_de_demande") AS date) ORDER BY "public"."suivi_demandes_prolongations"."état" ASC, CAST(DATE_TRUNC('month', "public"."suivi_demandes_prolongations"."date_de_demande") AS date) ASC
```

## [336] Moyenne délai traitement demande de prolongation

- **ID:** 7275
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT AVG("public"."suivi_demandes_prolongations"."delai_traitement") AS "avg" FROM "public"."suivi_demandes_prolongations" WHERE ("public"."suivi_demandes_prolongations"."delai_traitement" IS NOT NULL) AND (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) AND ("public"."suivi_demandes_prolongations"."date_de_demande" IS NOT NULL)
```

## [336] Nombre de demandes de prolongation à traiter (prescripteurs)

- **ID:** 7276
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) AND ("public"."suivi_demandes_prolongations"."état" = 'À traiter') AND ("public"."suivi_demandes_prolongations"."date_de_demande" IS NOT NULL) AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Distribution des prolongations avant le 26 juillet

- **ID:** 7277
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT "public"."suivi_demandes_prolongations"."motif" AS "motif", COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE "public"."suivi_demandes_prolongations"."date_de_création" < date '2023-07-26' GROUP BY "public"."suivi_demandes_prolongations"."motif" ORDER BY "public"."suivi_demandes_prolongations"."motif" ASC
```

## [336] Nombre de demandes de prolongation acceptées (tous motifs)

- **ID:** 7278
- **Thème:** prolongations
- **Tables:** public, suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" FROM "public"."suivi_demandes_prolongations" WHERE "public"."suivi_demandes_prolongations"."état" = 'Acceptée'
```
