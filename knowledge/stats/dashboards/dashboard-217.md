# Dashboard : Pilotage dispositif - Suivi des PASS IAE

# 2. Quelle est la situation de mon département durant la semaine du 23 novembre 2025 ? 
Nous étudions cette semaine précise, car un pic y est constaté comme vous pouvez le voir dans le graphique ci-dessus.

**Explications :** 
- En survolant votre département sur la carte de gauche, vous connaîtrez le nombre de PASS IAE arrivant à expiration en **moyenne chaque semaine de l'année 2025** dans votre département
- Ensuite, en survolant votre département sur la carte de droite, vous connaîtrez le nombre de PASS IAE y arrivant à expiration **la semaine du 23 novembre 2025**


# 1. Chaque semaine, combien de PASS IAE vont arriver à expiration ?  
## Des pics sont-ils prévus ? 


**Explications** : 
Chaque barre représente le nombre de PASS IAE qui arriveront à expiration durant la semaine sélectionnée en abscisse.  Une barre supérieure à la tendance globale indique que le  volume des PASS IAE arrivant à expiration cette semaine là sera supérieur à la normale.

💾 Source des données : le serv

**4 cartes**

## [217] Expiration PASS reprise de stock AI

- **ID:** 7267
- **Thème:** generalites-iae
- **Tables:** public, pass_agréments

```sql
SELECT CAST(DATE_TRUNC('week', "public"."pass_agréments"."date_fin") AS date) AS "date_fin", COUNT(*) AS "count" 
FROM "public"."pass_agréments" 
WHERE CAST(("public"."pass_agréments"."date_fin" + INTERVAL '0 month') AS date) BETWEEN DATE_TRUNC('month', NOW()) 
AND DATE_TRUNC('month', (NOW() + INTERVAL '24 month')) 
GROUP BY CAST(DATE_TRUNC('week', "public"."pass_agréments"."date_fin") AS date) 
ORDER BY CAST(DATE_TRUNC('week', "public"."pass_agréments"."date_fin") AS date) ASC
```

## [217] Expiration PASS reprise de stock AI

- **ID:** 7279
- **Thème:** generalites-iae
- **Tables:** public, pass_agréments

```sql
SELECT CAST(DATE_TRUNC('week', "public"."pass_agréments"."date_fin") AS date) AS "date_fin", COUNT(*) AS "count" 
FROM "public"."pass_agréments" 
WHERE CAST(("public"."pass_agréments"."date_fin" + INTERVAL '0 month') AS date) BETWEEN DATE_TRUNC('month', NOW()) 
AND DATE_TRUNC('month', (NOW() + INTERVAL '24 month')) 
GROUP BY CAST(DATE_TRUNC('week', "public"."pass_agréments"."date_fin") AS date) 
ORDER BY CAST(DATE_TRUNC('week', "public"."pass_agréments"."date_fin") AS date) ASC
```

## [217] Moyenne hebdo du Nombre de pass expirant en 2025

- **ID:** 7280
- **Thème:** generalites-iae
- **Tables:** public, pass_agréments

```sql
SELECT "public"."pass_agréments"."département_structure_ou_org_pe" AS "département_structure_ou_org_pe", CAST(COUNT(*) AS DOUBLE PRECISION) / 52.0 AS "Moyenne hebdomadaire PASS expirés" 
FROM "public"."pass_agréments" 
WHERE "public"."pass_agréments"."date_fin" BETWEEN date '2025-01-01' 
AND date '2025-12-31' 
AND ("public"."pass_agréments"."type_structure" = 'AI') 
AND (CASE WHEN "public"."pass_agréments"."injection_ai" = 0 THEN 'Non' ELSE 'Oui' END = 'Oui') 
GROUP BY "public"."pass_agréments"."département_structure_ou_org_pe" 
ORDER BY "public"."pass_agréments"."département_structure_ou_org_pe" ASC
```

## [217] Nombre de pass expirant entre le 27/11/23 et 3/12/23

- **ID:** 7281
- **Thème:** generalites-iae
- **Tables:** public, pass_agréments

```sql
SELECT "public"."pass_agréments"."département_structure_ou_org_pe" AS "département_structure_ou_org_pe", COUNT(*) AS "count" 
FROM "public"."pass_agréments" 
WHERE "public"."pass_agréments"."date_fin" BETWEEN date '2023-11-27' 
AND date '2023-12-03' 
AND ("public"."pass_agréments"."type_structure" = 'AI') 
AND (CASE WHEN "public"."pass_agréments"."injection_ai" = 0 THEN 'Non' ELSE 'Oui' END = 'Oui') 
GROUP BY "public"."pass_agréments"."département_structure_ou_org_pe" 
ORDER BY "public"."pass_agréments"."département_structure_ou_org_pe" ASC
```
