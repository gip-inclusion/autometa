# Thème : autre

*Uncategorized*

**1 cartes**

## Organisations, Nombre total de conseillers inscrits, Grouped by Date Inscription: Year, Filtered by Date Inscription is not empty, Sorted by Nombre total de conseillers inscrits descending

- **ID:** 7040
- **Tables:** public, organisations

```sql
SELECT CAST(DATE_TRUNC('year', "public"."organisations"."date_inscription") AS date) AS "date_inscription", SUM("public"."organisations"."total_membres") AS "Nombre total de conseillers inscrits" FROM "public"."organisations" WHERE "public"."organisations"."date_inscription" IS NOT NULL GROUP BY CAST(DATE_TRUNC('year', "public"."organisations"."date_inscription") AS date) ORDER BY "Nombre total de conseillers inscrits" DESC, CAST(DATE_TRUNC('year', "public"."organisations"."date_inscription") AS date) ASC
```
