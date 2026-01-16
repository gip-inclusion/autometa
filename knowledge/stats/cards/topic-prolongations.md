# Thème : prolongations

*PASS extensions*

**21 cartes**

## [336] Nombre de demandes de prolongation

- **ID:** 2681
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations"
```

## [336] Nombre de demandes de prolongation par motif (tous motifs)

- **ID:** 2682
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT "public"."suivi_demandes_prolongations"."motif" AS "motif", COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
GROUP BY "public"."suivi_demandes_prolongations"."motif" 
ORDER BY "public"."suivi_demandes_prolongations"."motif" ASC
```

## [336] Nombre de demandes de prolongation envoyées aux prescripteurs

- **ID:** 2683
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) 
AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Nombre de demandes de prolongation acceptées (prescripteurs)

- **ID:** 2684
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE (("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') 
OR ("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) 
AND ("public"."suivi_demandes_prolongations"."état" = 'Acceptée') 
AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Nombre de demandes de prolongation refusées (prescripteurs)

- **ID:** 2685
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) 
AND ("public"."suivi_demandes_prolongations"."état" = 'Refusée') 
AND ("public"."suivi_demandes_prolongations"."date_de_demande" IS NOT NULL) 
AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Proportion de demandes de prolongation refusées (prescripteurs)

- **ID:** 2686
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT CAST(SUM(CASE WHEN "public"."suivi_demandes_prolongations"."état" = 'Refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de demandes refusées " 
FROM "public"."suivi_demandes_prolongations" 
WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) 
AND ("public"."suivi_demandes_prolongations"."date_de_demande" IS NOT NULL) 
AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Proportion de demandes de prolongation acceptées (prescripteurs)

- **ID:** 2687
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT CAST(SUM(CASE WHEN "public"."suivi_demandes_prolongations"."état" = 'Acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de demandes acceptées" 
FROM "public"."suivi_demandes_prolongations" 
WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) 
AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Répartition des demandes par type de prescripteur habilité

- **ID:** 2748
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT "public"."suivi_demandes_prolongations"."type_prescripteur" AS "type_prescripteur", COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) 
AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25') 
GROUP BY "public"."suivi_demandes_prolongations"."type_prescripteur" 
ORDER BY "public"."suivi_demandes_prolongations"."type_prescripteur" ASC
```

## [336] Nombre des demandes envoyées aux prescripteurs par semaine

- **ID:** 2769
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT "public"."suivi_demandes_prolongations"."état" AS "état", CAST(DATE_TRUNC('week', "public"."suivi_demandes_prolongations"."date_de_demande") AS date) AS "date_de_demande", COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) 
AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25') 
GROUP BY "public"."suivi_demandes_prolongations"."état", CAST(DATE_TRUNC('week', "public"."suivi_demandes_prolongations"."date_de_demande") AS date) 
ORDER BY "public"."suivi_demandes_prolongations"."état" ASC, CAST(DATE_TRUNC('week', "public"."suivi_demandes_prolongations"."date_de_demande") AS date) ASC
```

## [336] Nombre des demandes envoyées aux prescripteurs par mois

- **ID:** 2770
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT "public"."suivi_demandes_prolongations"."état" AS "état", CAST(DATE_TRUNC('month', "public"."suivi_demandes_prolongations"."date_de_demande") AS date) AS "date_de_demande", COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE ("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle') 
GROUP BY "public"."suivi_demandes_prolongations"."état", CAST(DATE_TRUNC('month', "public"."suivi_demandes_prolongations"."date_de_demande") AS date) 
ORDER BY "public"."suivi_demandes_prolongations"."état" ASC, CAST(DATE_TRUNC('month', "public"."suivi_demandes_prolongations"."date_de_demande") AS date) ASC
```

## [336] Moyenne délai traitement demande de prolongation

- **ID:** 2771
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT AVG("public"."suivi_demandes_prolongations"."delai_traitement") AS "avg" 
FROM "public"."suivi_demandes_prolongations" 
WHERE ("public"."suivi_demandes_prolongations"."delai_traitement" IS NOT NULL) 
AND (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) 
AND ("public"."suivi_demandes_prolongations"."date_de_demande" IS NOT NULL)
```

## [336] Nombre de demandes à traiter ayant plus de 30j

- **ID:** 2963
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulières qui font obstacle à l''insertion durable dans l’emploi') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé')) 
AND ("public"."suivi_demandes_prolongations"."date_de_demande" IS NOT NULL) 
AND ("public"."suivi_demandes_prolongations"."duree_depuis_demande" > 30) 
AND ("public"."suivi_demandes_prolongations"."état" = 'À traiter')
```

## [336] Motif de refus des demandes

- **ID:** 3186
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT "public"."suivi_demandes_prolongations"."motif_de_refus" AS "motif_de_refus", COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) 
AND ("public"."suivi_demandes_prolongations"."état" = 'Refusée') 
AND ("public"."suivi_demandes_prolongations"."date_de_demande" IS NOT NULL) 
GROUP BY "public"."suivi_demandes_prolongations"."motif_de_refus" 
ORDER BY "public"."suivi_demandes_prolongations"."motif_de_refus" ASC
```

## [336] Demandes de prolongations acceptées par les SIAE

- **ID:** 3187
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE (("public"."suivi_demandes_prolongations"."motif" <> '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) 
AND (("public"."suivi_demandes_prolongations"."motif" <> 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle') 
OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) 
AND (("public"."suivi_demandes_prolongations"."motif" <> 'RQTH - Reconnaissance de la qualité de travailleur handicapé') 
OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) 
AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Distribution des demandes de prolongations acceptées par les SIAE

- **ID:** 3188
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT "public"."suivi_demandes_prolongations"."motif" AS "motif", COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE (("public"."suivi_demandes_prolongations"."motif" <> '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) 
AND (("public"."suivi_demandes_prolongations"."motif" <> 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle') 
OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) 
AND (("public"."suivi_demandes_prolongations"."motif" <> 'RQTH - Reconnaissance de la qualité de travailleur handicapé') 
OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) 
AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25') 
GROUP BY "public"."suivi_demandes_prolongations"."motif" 
ORDER BY "public"."suivi_demandes_prolongations"."motif" ASC
```

## [336] Demandes de prolongations validées directement par les SIAE

- **ID:** 3190
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE (("public"."suivi_demandes_prolongations"."motif" <> '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) 
AND (("public"."suivi_demandes_prolongations"."motif" <> 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle') 
OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) 
AND (("public"."suivi_demandes_prolongations"."motif" <> 'RQTH - Reconnaissance de la qualité de travailleur handicapé') 
OR ("public"."suivi_demandes_prolongations"."motif" IS NULL)) 
AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Nombre de prolongations avant le 26 juillet

- **ID:** 3191
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE "public"."suivi_demandes_prolongations"."date_de_création" < date '2023-07-26'
```

## [336] Distribution des prolongations avant le 26 juillet

- **ID:** 3192
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT "public"."suivi_demandes_prolongations"."motif" AS "motif", COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE "public"."suivi_demandes_prolongations"."date_de_création" < date '2023-07-26' 
GROUP BY "public"."suivi_demandes_prolongations"."motif" 
ORDER BY "public"."suivi_demandes_prolongations"."motif" ASC
```

## [336] Nombre de demandes ayant été traitées en plus de 30j

- **ID:** 3194
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulières qui font obstacle à l''insertion durable dans l’emploi') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé')) 
AND ("public"."suivi_demandes_prolongations"."date_de_demande" IS NOT NULL) 
AND ("public"."suivi_demandes_prolongations"."delai_traitement" > 30)
```

## [336] Nombre de demandes de prolongation à traiter (prescripteurs)

- **ID:** 3264
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE (("public"."suivi_demandes_prolongations"."motif" = '50 ans et plus') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'RQTH - Reconnaissance de la qualité de travailleur handicapé') 
OR ("public"."suivi_demandes_prolongations"."motif" = 'Difficultés particulièrement importantes dont l''absence de prise en charge ferait obstacle à son insertion professionnelle')) 
AND ("public"."suivi_demandes_prolongations"."état" = 'À traiter') 
AND ("public"."suivi_demandes_prolongations"."date_de_demande" IS NOT NULL) 
AND ("public"."suivi_demandes_prolongations"."date_de_création" > date '2023-07-25')
```

## [336] Nombre de demandes de prolongation acceptées (tous motifs)

- **ID:** 3265
- **Dashboard:** 336
- **Tables:** suivi_demandes_prolongations

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."suivi_demandes_prolongations" 
WHERE "public"."suivi_demandes_prolongations"."état" = 'Acceptée'
```
