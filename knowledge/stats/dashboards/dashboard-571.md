# Dashboard : ESAT 2025 

**URL:** /tableaux-de-bord/zoom-esat-2025/

**18 cartes**

## Nombre de réponses au questionnaire

- **ID:** 6526
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT COUNT(*) AS "count" 
FROM "esat"."questionnaire_2025"
```

## Nombre moyen de salariés par ESAT

- **ID:** 6527
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_worked") AS "avg" 
FROM "esat"."questionnaire_2025" 
WHERE "esat"."questionnaire_2025"."nb_employee_worked" < 999
```

## Nombre moyen de travailleurs accompagnés

- **ID:** 6528
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_acc") AS "avg" 
FROM "esat"."questionnaire_2025" 
WHERE ("esat"."questionnaire_2025"."nb_employee_acc" <> 999) 
OR ("esat"."questionnaire_2025"."nb_employee_acc" IS NULL)
```

## Nombre moyen de places autorisée

- **ID:** 6529
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_places_allowed") AS "avg" 
FROM "esat"."questionnaire_2025" 
WHERE ("esat"."questionnaire_2025"."nb_places_allowed" <> 999) 
OR ("esat"."questionnaire_2025"."nb_places_allowed" IS NULL)
```

## Âge moyen des salariés

- **ID:** 6530
- **Thème:** demographie
- **Tables:** questionnaire_2025

```sql
SELECT CAST(SUM("esat"."questionnaire_2025"."mean_employee_age" * "esat"."questionnaire_2025"."nb_employee_worked") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("esat"."questionnaire_2025"."nb_employee_worked") AS DOUBLE PRECISION), 0.0) AS "âge moyen des salariés" 
FROM "esat"."questionnaire_2025" 
WHERE "esat"."questionnaire_2025"."mean_employee_age" < 100
```

## Pourcentage d'ESAT public

- **ID:** 6531
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT "esat"."questionnaire_2025"."esat_status" AS "esat_status", COUNT(*) AS "count" 
FROM "esat"."questionnaire_2025" 
GROUP BY "esat"."questionnaire_2025"."esat_status" 
ORDER BY "esat"."questionnaire_2025"."esat_status" ASC
```

## Travailleurs accompagnés (temps partiel, FT, cumuls)

- **ID:** 6533
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_half_time") AS "avg", AVG("esat"."questionnaire_2025"."nb_employee_FT_job_seekers") AS "avg_2", AVG("esat"."questionnaire_2025"."nb_employee_cumul_ESAT_EA") AS "avg_3", AVG("esat"."questionnaire_2025"."nb_employee_cumul_ESAT_ordi") AS "avg_4" 
FROM "esat"."questionnaire_2025"
```

## Travailleurs accompagnés (milieu ordi, premiere fois, temporaire, voulant sortir)

- **ID:** 6534
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_acc") AS "avg", AVG("esat"."questionnaire_2025"."nb_employee_worked") AS "avg_2", AVG("esat"."questionnaire_2025"."nb_employee_new") AS "avg_3", AVG("esat"."questionnaire_2025"."nb_employee_temporary") AS "avg_4", AVG("esat"."questionnaire_2025"."nb_employee_willing_ordinary") AS "avg_5" 
FROM "esat"."questionnaire_2025"
```

## Travailleurs accompagnés (pmsmp, mise à dispo)

- **ID:** 6544
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_PMSMP") AS "avg", AVG("esat"."questionnaire_2025"."nb_employee_dispo_indiv") AS "avg_2", AVG("esat"."questionnaire_2025"."nb_employee_dispo_collec") AS "avg_3", AVG("esat"."questionnaire_2025"."nb_employee_restau") AS "avg_4" 
FROM "esat"."questionnaire_2025"
```

## Travailleurs sortis

- **ID:** 6545
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_CDI") AS "avg", AVG("esat"."questionnaire_2025"."nb_employee_CDD") AS "avg_2", AVG("esat"."questionnaire_2025"."nb_employee_interim") AS "avg_3", AVG("esat"."questionnaire_2025"."nb_employee_prof") AS "avg_4", AVG("esat"."questionnaire_2025"."nb_employee_apprentice") AS "avg_5" 
FROM "esat"."questionnaire_2025"
```

## Travailleurs sortis (structure)

- **ID:** 6546
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_left_EA") AS "avg", AVG("esat"."questionnaire_2025"."nb_employee_left_public") AS "avg_2", AVG("esat"."questionnaire_2025"."nb_employee_left_private") AS "avg_3", AVG("esat"."questionnaire_2025"."nb_employee_left_asso") AS "avg_4" 
FROM "esat"."questionnaire_2025"
```

## Formation

- **ID:** 6624
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT CAST(SUM(CASE WHEN "esat"."questionnaire_2025"."contrib_OPCO" = 'Oui' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part des ESAT contribuant à l'OPCO Santé ou ANFH", AVG("esat"."questionnaire_2025"."pct_OPCO") AS "avg", CAST(SUM("esat"."questionnaire_2025"."nb_employee_RAE_RSFP") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("esat"."questionnaire_2025"."nb_employee_worked") AS DOUBLE PRECISION), 0.0) AS "% employee RAE", AVG("esat"."questionnaire_2025"."nb_employee_formation_OPCO") AS "avg_2", AVG("esat"."questionnaire_2025"."nb_employee_RAE_RSFP") AS "avg_3" 
FROM "esat"."questionnaire_2025" 
WHERE ("esat"."questionnaire_2025"."pct_OPCO" < 100) 
AND ("esat"."questionnaire_2025"."nb_employee_formation_OPCO" < 999)
```

## Formation (CPF, UATT...)

- **ID:** 6678
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employeed_CPF_unused") AS "avg", CAST(SUM("esat"."questionnaire_2025"."nb_employeed_CPF_unused") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("esat"."questionnaire_2025"."nb_employee_acc") AS DOUBLE PRECISION), 0.0) AS "% employee cpf unused", AVG("esat"."questionnaire_2025"."nb_employee_intern_formation") AS "avg_2", CAST(SUM("esat"."questionnaire_2025"."nb_employee_intern_formation") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("esat"."questionnaire_2025"."nb_employee_acc") AS DOUBLE PRECISION), 0.0) AS "% de salariés ayant suivi une formation en interne", AVG("esat"."questionnaire_2025"."nb_employee_autodetermination") AS "avg_3", CAST(SUM("esat"."questionnaire_2025"."nb_employee_autodetermination") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("esat"."questionnaire_2025"."nb_employee_acc") AS DOUBLE PRECISION), 0.0) AS "% de salariés ayant eu une formation en autosensibilisation", SUM(CASE WHEN "esat"."questionnaire_2025"."autodetermination_formation" = 'Oui' THEN 1 ELSE 0.0 END) AS "Nombre d'ESAT ayant mis en place l'auto sensibilisa_bdb52947", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."autodetermination_formation" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant mis en place l'auto sensibilisation" 
FROM "esat"."questionnaire_2025"
```

## Partenariats et conseillers

- **ID:** 6679
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT SUM(CASE WHEN "esat"."questionnaire_2025"."RPE_convention_signed" = 'Oui' THEN 1 ELSE 0.0 END) AS "Nombre d'ESAT ayant signé une convention de partenariat RPE", CAST(SUM(CASE WHEN "esat"."questionnaire_2025"."RPE_convention_signed" = 'Oui' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant signé une convention de partenariat RPE", SUM(CASE WHEN "esat"."questionnaire_2025"."PEA_convention_signed" = 'Oui' THEN 1 ELSE 0.0 END) AS "Nombre d'ESAT ayant signé une convention de parten_6e666bed", CAST(SUM(CASE WHEN "esat"."questionnaire_2025"."PEA_convention_signed" = 'Oui' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant signé une convention de partenariat_2aa7c1be", AVG("esat"."questionnaire_2025"."nb_insertion_staff") AS "avg", AVG("esat"."questionnaire_2025"."nb_insertion_dispo") AS "avg_2", count(distinct CASE WHEN "esat"."questionnaire_2025"."cap_emploi_convention_considered" = FALSE THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT envisageant un partenariat avec Cap Emploi", count(distinct CASE WHEN "esat"."questionnaire_2025"."mission_locale_convention_considered" = FALSE THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT envisageant un partenariat avec Mission Locale", count(distinct CASE WHEN "esat"."questionnaire_2025"."no_convention_considered" = FALSE THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT n'envisageant aucun autre partenariat" 
FROM "esat"."questionnaire_2025"
```

## Chiffres d'affaires

- **ID:** 6680
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT PERCENTILE_CONT(0.5) within group (order by "esat"."questionnaire_2025"."annual_CA") AS "median", PERCENTILE_CONT(0.5) within group (order by "esat"."questionnaire_2025"."annual_CA_production") AS "median_2", PERCENTILE_CONT(0.5) within group (order by "esat"."questionnaire_2025"."annual_CA_service") AS "median_3", PERCENTILE_CONT(0.5) within group (order by "esat"."questionnaire_2025"."annual_CA_dispo") AS "median_4" 
FROM "esat"."questionnaire_2025"
```

## Investissements

- **ID:** 6681
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT PERCENTILE_CONT(0.5) within group (order by CASE WHEN "esat"."questionnaire_2025"."budget_accessibility" > 0 THEN "esat"."questionnaire_2025"."budget_accessibility" END) AS "Budget médian pour les ESAT ayant investi pour la _d51c98e0", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."budget_accessibility" > 0 THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant investi pour la mise aux normes séc_bd0786ad", PERCENTILE_CONT(0.5) within group (order by CASE WHEN "esat"."questionnaire_2025"."budget_diversity" > 0 THEN "esat"."questionnaire_2025"."budget_diversity" END) AS "Budget médian pour les ESAT ayant investi pour la _59a440ba", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."budget_diversity" > 0 THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant investi pour la diversification des _5583d22f" 
FROM "esat"."questionnaire_2025"
```

## Formation (duoday)

- **ID:** 6684
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_duoday") AS "avg", count(distinct CASE WHEN "esat"."questionnaire_2025"."duoday_board" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT ayant mis en place un carnet de parco_eac31f6b", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."duoday_board" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant mis en place un carnet de parcours e_909f373f", count(distinct CASE WHEN "esat"."questionnaire_2025"."duoday_software_used" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT ayant utilisé un logiciel pour la mi_056d090a", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."duoday_software_used" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant utilisé un logiciel pour la mise en_331ff581", count(distinct CASE WHEN "esat"."questionnaire_2025"."duoday_software_financial_help" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT ayant bénéficié d'une aide financi_2ae01c0f", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."duoday_software_financial_help" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant bénéficié d'une aide financière _d8c6ddeb" 
FROM "esat"."questionnaire_2025"
```

## Avantages des salariés

- **ID:** 6687
- **Thème:** esat
- **Tables:** questionnaire_2025

```sql
SELECT count(distinct CASE WHEN "esat"."questionnaire_2025"."holiday_voucher" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT proposant des chèques vacances aux t_b75b7ee4", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."holiday_voucher" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT proposant des chèques vacances aux travailleurs", count(distinct CASE WHEN "esat"."questionnaire_2025"."gift_voucher" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT proposant des chèques cadeaux aux tr_0a1b7f7d", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."gift_voucher" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT proposant des chèques cadeaux aux travailleurs", AVG("esat"."questionnaire_2025"."holiday_voucher_annual_budget") AS "avg", AVG("esat"."questionnaire_2025"."gift_voucher_annual_budget") AS "avg_2", count(distinct CASE WHEN "esat"."questionnaire_2025"."health_complementary" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT prenant en charge une partie de la co_ac9247b4" 
FROM "esat"."questionnaire_2025"
```
