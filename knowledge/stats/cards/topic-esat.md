# Thème : esat

*ESAT-specific data*

**116 cartes**

## Travailleurs accompagnés (pmsmp, mise à dispo)

- **ID:** 7113
- **Tables:** esat, questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_PMSMP") AS "avg", AVG("esat"."questionnaire_2025"."nb_employee_dispo_indiv") AS "avg_2", AVG("esat"."questionnaire_2025"."nb_employee_dispo_collec") AS "avg_3", AVG("esat"."questionnaire_2025"."nb_employee_restau") AS "avg_4" 
FROM "esat"."questionnaire_2025"
```

## Formation (duoday)

- **ID:** 7114
- **Tables:** esat, questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_duoday") AS "avg", count(distinct CASE WHEN "esat"."questionnaire_2025"."duoday_board" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT ayant mis en place un carnet de parco_eac31f6b", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."duoday_board" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant mis en place un carnet de parcours e_909f373f", count(distinct CASE WHEN "esat"."questionnaire_2025"."duoday_software_used" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT ayant utilisé un logiciel pour la mi_056d090a", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."duoday_software_used" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant utilisé un logiciel pour la mise en_331ff581", count(distinct CASE WHEN "esat"."questionnaire_2025"."duoday_software_financial_help" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT ayant bénéficié d'une aide financi_2ae01c0f", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."duoday_software_financial_help" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant bénéficié d'une aide financière _d8c6ddeb" 
FROM "esat"."questionnaire_2025"
```

## Travailleurs sortis

- **ID:** 7115
- **Tables:** esat, questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_CDI") AS "avg", AVG("esat"."questionnaire_2025"."nb_employee_CDD") AS "avg_2", AVG("esat"."questionnaire_2025"."nb_employee_interim") AS "avg_3", AVG("esat"."questionnaire_2025"."nb_employee_prof") AS "avg_4", AVG("esat"."questionnaire_2025"."nb_employee_apprentice") AS "avg_5" 
FROM "esat"."questionnaire_2025"
```

## Chiffres d'affaires

- **ID:** 7116
- **Tables:** esat, questionnaire_2025

```sql
SELECT PERCENTILE_CONT(0.5) within group (order by "esat"."questionnaire_2025"."annual_CA") AS "median", PERCENTILE_CONT(0.5) within group (order by "esat"."questionnaire_2025"."annual_CA_production") AS "median_2", PERCENTILE_CONT(0.5) within group (order by "esat"."questionnaire_2025"."annual_CA_service") AS "median_3", PERCENTILE_CONT(0.5) within group (order by "esat"."questionnaire_2025"."annual_CA_dispo") AS "median_4" 
FROM "esat"."questionnaire_2025"
```

## Partenariats et conseillers

- **ID:** 7117
- **Tables:** esat, questionnaire_2025

```sql
SELECT SUM(CASE WHEN "esat"."questionnaire_2025"."RPE_convention_signed" = 'Oui' THEN 1 ELSE 0.0 END) AS "Nombre d'ESAT ayant signé une convention de partenariat RPE", CAST(SUM(CASE WHEN "esat"."questionnaire_2025"."RPE_convention_signed" = 'Oui' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant signé une convention de partenariat RPE", SUM(CASE WHEN "esat"."questionnaire_2025"."PEA_convention_signed" = 'Oui' THEN 1 ELSE 0.0 END) AS "Nombre d'ESAT ayant signé une convention de parten_6e666bed", CAST(SUM(CASE WHEN "esat"."questionnaire_2025"."PEA_convention_signed" = 'Oui' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant signé une convention de partenariat_2aa7c1be", AVG("esat"."questionnaire_2025"."nb_insertion_staff") AS "avg", AVG("esat"."questionnaire_2025"."nb_insertion_dispo") AS "avg_2", count(distinct CASE WHEN "esat"."questionnaire_2025"."cap_emploi_convention_considered" = FALSE THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT envisageant un partenariat avec Cap Emploi", count(distinct CASE WHEN "esat"."questionnaire_2025"."mission_locale_convention_considered" = FALSE THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT envisageant un partenariat avec Mission Locale", count(distinct CASE WHEN "esat"."questionnaire_2025"."no_convention_considered" = FALSE THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT n'envisageant aucun autre partenariat" 
FROM "esat"."questionnaire_2025"
```

## Nombre moyen de salariés par ESAT

- **ID:** 7118
- **Tables:** esat, questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_worked") AS "avg" 
FROM "esat"."questionnaire_2025" 
WHERE "esat"."questionnaire_2025"."nb_employee_worked" < 999
```

## Nombre moyen de travailleurs accompagnés

- **ID:** 7119
- **Tables:** esat, questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_acc") AS "avg" 
FROM "esat"."questionnaire_2025" 
WHERE ("esat"."questionnaire_2025"."nb_employee_acc" <> 999) 
OR ("esat"."questionnaire_2025"."nb_employee_acc" IS NULL)
```

## Formation

- **ID:** 7120
- **Tables:** esat, questionnaire_2025

```sql
SELECT CAST(SUM(CASE WHEN "esat"."questionnaire_2025"."contrib_OPCO" = 'Oui' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part des ESAT contribuant à l'OPCO Santé ou ANFH", AVG("esat"."questionnaire_2025"."pct_OPCO") AS "avg", CAST(SUM("esat"."questionnaire_2025"."nb_employee_RAE_RSFP") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("esat"."questionnaire_2025"."nb_employee_worked") AS DOUBLE PRECISION), 0.0) AS "% employee RAE", AVG("esat"."questionnaire_2025"."nb_employee_formation_OPCO") AS "avg_2", AVG("esat"."questionnaire_2025"."nb_employee_RAE_RSFP") AS "avg_3" 
FROM "esat"."questionnaire_2025" 
WHERE ("esat"."questionnaire_2025"."pct_OPCO" < 100) 
AND ("esat"."questionnaire_2025"."nb_employee_formation_OPCO" < 999)
```

## Nombre de réponses au questionnaire

- **ID:** 7121
- **Tables:** esat, questionnaire_2025

```sql
SELECT COUNT(*) AS "count" 
FROM "esat"."questionnaire_2025"
```

## Formation (CPF, UATT...)

- **ID:** 7122
- **Tables:** esat, questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employeed_CPF_unused") AS "avg", CAST(SUM("esat"."questionnaire_2025"."nb_employeed_CPF_unused") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("esat"."questionnaire_2025"."nb_employee_acc") AS DOUBLE PRECISION), 0.0) AS "% employee cpf unused", AVG("esat"."questionnaire_2025"."nb_employee_intern_formation") AS "avg_2", CAST(SUM("esat"."questionnaire_2025"."nb_employee_intern_formation") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("esat"."questionnaire_2025"."nb_employee_acc") AS DOUBLE PRECISION), 0.0) AS "% de salariés ayant suivi une formation en interne", AVG("esat"."questionnaire_2025"."nb_employee_autodetermination") AS "avg_3", CAST(SUM("esat"."questionnaire_2025"."nb_employee_autodetermination") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("esat"."questionnaire_2025"."nb_employee_acc") AS DOUBLE PRECISION), 0.0) AS "% de salariés ayant eu une formation en autosensibilisation", SUM(CASE WHEN "esat"."questionnaire_2025"."autodetermination_formation" = 'Oui' THEN 1 ELSE 0.0 END) AS "Nombre d'ESAT ayant mis en place l'auto sensibilisa_bdb52947", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."autodetermination_formation" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant mis en place l'auto sensibilisation" 
FROM "esat"."questionnaire_2025"
```

## Travailleurs accompagnés (temps partiel, FT, cumuls)

- **ID:** 7123
- **Tables:** esat, questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_half_time") AS "avg", AVG("esat"."questionnaire_2025"."nb_employee_FT_job_seekers") AS "avg_2", AVG("esat"."questionnaire_2025"."nb_employee_cumul_ESAT_EA") AS "avg_3", AVG("esat"."questionnaire_2025"."nb_employee_cumul_ESAT_ordi") AS "avg_4" 
FROM "esat"."questionnaire_2025"
```

## Pourcentage d'ESAT public

- **ID:** 7124
- **Tables:** esat, questionnaire_2025

```sql
SELECT "esat"."questionnaire_2025"."esat_status" AS "esat_status", COUNT(*) AS "count" 
FROM "esat"."questionnaire_2025" 
GROUP BY "esat"."questionnaire_2025"."esat_status" 
ORDER BY "esat"."questionnaire_2025"."esat_status" ASC
```

## Nombre moyen de places autorisée

- **ID:** 7125
- **Tables:** esat, questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_places_allowed") AS "avg" 
FROM "esat"."questionnaire_2025" 
WHERE ("esat"."questionnaire_2025"."nb_places_allowed" <> 999) 
OR ("esat"."questionnaire_2025"."nb_places_allowed" IS NULL)
```

## Avantages des salariés

- **ID:** 7126
- **Tables:** esat, questionnaire_2025

```sql
SELECT count(distinct CASE WHEN "esat"."questionnaire_2025"."holiday_voucher" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT proposant des chèques vacances aux t_b75b7ee4", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."holiday_voucher" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT proposant des chèques vacances aux travailleurs", count(distinct CASE WHEN "esat"."questionnaire_2025"."gift_voucher" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT proposant des chèques cadeaux aux tr_0a1b7f7d", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."gift_voucher" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT proposant des chèques cadeaux aux travailleurs", AVG("esat"."questionnaire_2025"."holiday_voucher_annual_budget") AS "avg", AVG("esat"."questionnaire_2025"."gift_voucher_annual_budget") AS "avg_2", count(distinct CASE WHEN "esat"."questionnaire_2025"."health_complementary" = 'Oui' THEN "esat"."questionnaire_2025"."esat_siret" END) AS "Nombre d'ESAT prenant en charge une partie de la co_ac9247b4" 
FROM "esat"."questionnaire_2025"
```

## Travailleurs sortis (structure)

- **ID:** 7127
- **Tables:** esat, questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_left_EA") AS "avg", AVG("esat"."questionnaire_2025"."nb_employee_left_public") AS "avg_2", AVG("esat"."questionnaire_2025"."nb_employee_left_private") AS "avg_3", AVG("esat"."questionnaire_2025"."nb_employee_left_asso") AS "avg_4" 
FROM "esat"."questionnaire_2025"
```

## Travailleurs accompagnés (milieu ordi, premiere fois, temporaire, voulant sortir)

- **ID:** 7128
- **Tables:** esat, questionnaire_2025

```sql
SELECT AVG("esat"."questionnaire_2025"."nb_employee_acc") AS "avg", AVG("esat"."questionnaire_2025"."nb_employee_worked") AS "avg_2", AVG("esat"."questionnaire_2025"."nb_employee_new") AS "avg_3", AVG("esat"."questionnaire_2025"."nb_employee_temporary") AS "avg_4", AVG("esat"."questionnaire_2025"."nb_employee_willing_ordinary") AS "avg_5" 
FROM "esat"."questionnaire_2025"
```

## Âge moyen des salariés

- **ID:** 7129
- **Tables:** esat, questionnaire_2025

```sql
SELECT CAST(SUM("esat"."questionnaire_2025"."mean_employee_age" * "esat"."questionnaire_2025"."nb_employee_worked") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("esat"."questionnaire_2025"."nb_employee_worked") AS DOUBLE PRECISION), 0.0) AS "âge moyen des salariés" 
FROM "esat"."questionnaire_2025" 
WHERE "esat"."questionnaire_2025"."mean_employee_age" < 100
```

## Investissements

- **ID:** 7130
- **Tables:** esat, questionnaire_2025

```sql
SELECT PERCENTILE_CONT(0.5) within group (order by CASE WHEN "esat"."questionnaire_2025"."budget_accessibility" > 0 THEN "esat"."questionnaire_2025"."budget_accessibility" END) AS "Budget médian pour les ESAT ayant investi pour la _d51c98e0", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."budget_accessibility" > 0 THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant investi pour la mise aux normes séc_bd0786ad", PERCENTILE_CONT(0.5) within group (order by CASE WHEN "esat"."questionnaire_2025"."budget_diversity" > 0 THEN "esat"."questionnaire_2025"."budget_diversity" END) AS "Budget médian pour les ESAT ayant investi pour la _59a440ba", CAST(count(distinct CASE WHEN "esat"."questionnaire_2025"."budget_diversity" > 0 THEN "esat"."questionnaire_2025"."esat_siret" END) AS DOUBLE PRECISION) / NULLIF(CAST(count(distinct "esat"."questionnaire_2025"."esat_siret") AS DOUBLE PRECISION), 0.0) AS "% d'ESAT ayant investi pour la diversification des _5583d22f" 
FROM "esat"."questionnaire_2025"
```

## [471] Pourcentage moyen de travailleurs ayant travaillé au moins 1 dimanche en 2023

- **ID:** 7131
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant travaillé un dimanche") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Nombre moyen par ESAT de travailleurs partis pour une entreprise adaptée, pour le public, pour le privé ou pour une association

- **ID:** 7132
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour entreprise adaptée") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour le public") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour le privé") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour association") AS "avg_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## Nombre d'ESAT ayant répondu au questionnaire

- **ID:** 7133
- **Tables:** ESAT, public

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo"
```

## [471] Nombre de répondants

- **ID:** 7134
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471]  Travailleurs accompagnés par ESAT, dont emploi en milieu ordinaire avant ESAT , Esat pour la 1ere fois, en remplacement, et voulant sortir du milieu protégé - Modifié

- **ID:** 7135
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs accompagnés") AS "sum", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant occupé un emploi en milieu ordina") AS "sum_2", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs étant en ESAT pour la 1ere fois") AS "sum_3", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs admis temporairement en remplacement") AS "sum_4", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs voulant sortir du milieu protégé") AS "sum_5" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Somme des places autorisées par ESAT

- **ID:** 7136
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Places autorisées par ARS") AS "sum" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Montant médian du CA total

- **ID:** 7137
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT PERCENTILE_CONT(0.5) within group (order by "public"."Esat - Questionnaire 2024"."Montant du CA total") AS "median" 
FROM "public"."Esat - Questionnaire 2024"
```

## Financement OPCO

- **ID:** 7138
- **Tables:** ESAT, public

```sql
SELECT "source"."Financement Opco" AS "Financement Opco", COUNT(*) AS "count" 
FROM (SELECT "public"."ESAT - Questionnaire transfo"."OPCO" AS "OPCO", CASE WHEN "public"."ESAT - Questionnaire transfo"."OPCO" = 1 THEN 'oui' WHEN "public"."ESAT - Questionnaire transfo"."OPCO" = 0 THEN 'non' END AS "Financement Opco" 
FROM "public"."ESAT - Questionnaire transfo") AS "source" 
GROUP BY "source"."Financement Opco" 
ORDER BY "source"."Financement Opco" ASC
```

## [471] Somme du nombre de  salariés en droit commun (ETP)

- **ID:** 7139
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de salariés en droit commun") AS "sum" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Montant médian en investissement de production (parmi les ESAT ayant investi)

- **ID:** 7140
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT PERCENTILE_CONT(0.5) within group (order by "public"."Esat - Questionnaire 2024"."Montant investissement production") AS "median" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant investissement production" > 0
```

## [471] Moyenne du nombre de travailleurs accompagnés

- **ID:** 7141
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs accompagnés") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Montant moyen par travailleur de la prime de partage de la valeur (PPV) pour les travailleurs l'ayant touché

- **ID:** 7142
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Montant moyen PPV") AS "avg" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant moyen PPV" > 0
```

## [471] Pourcentage de travailleurs ayant bénéficié du dispositif UAAT

- **ID:** 7143
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié dispositif UAAT") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Votre ESAT contribue t'il à l'OPCO Santé ou l'OPCA ANFH?

- **ID:** 7144
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Contribution OPCO ou OPCA" AS "Contribution OPCO ou OPCA", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Contribution OPCO ou OPCA" 
ORDER BY "public"."Esat - Questionnaire 2024"."Contribution OPCO ou OPCA" ASC
```

## [471] Age moyen des travailleurs

- **ID:** 7145
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Age moyen des travailleurs") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage moyen de travailleurs par ESAT  ayant bénéficié d'une RAE ou RSFP

- **ID:** 7146
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié de RAE ou RSFP") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471]  Montant médian de l'investissement mise aux normes sécurité  et accessibilité

- **ID:** 7147
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT PERCENTILE_CONT(0.5) within group (order by "public"."Esat - Questionnaire 2024"."Montant investissement mise aux normes sécurité accessibilit") AS "median" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant investissement mise aux normes sécurité accessibilit" > 0
```

## [471] Pourcentage moyen par ESAT de travailleurs partis avec CDI,  CDD, contrat intérim, contrat de professionalisation, contrat d'apprentissage

- **ID:** 7148
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec CDI") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec CDD") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec interim") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec contrat pro") AS "avg_4", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec contrat apprentissage") AS "avg_5" 
FROM "public"."Esat - Questionnaire 2024"
```

## Budget commercial, au national

- **ID:** 7149
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Budget commercial" AS "Budget commercial", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
WHERE ("public"."ESAT - Questionnaire transfo"."Budget commercial" <> 'excédentaires') 
OR ("public"."ESAT - Questionnaire transfo"."Budget commercial" IS NULL) 
GROUP BY "public"."ESAT - Questionnaire transfo"."Budget commercial" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Budget commercial" ASC
```

## Travailleurs en temps partiel, inscrits comme DE à France Travail, en cumul temps partiel entreprise adaptée et ESAT, en cumul temps partiel milieu ordinaire et ESAT

- **ID:** 7150
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs en temps partiel") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs inscrits comme DE à France travail") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant cumulé entreprise adaptée et tem") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant cumulé  milieu ordinaire et temps") AS "avg_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Budget activité sociale

- **ID:** 7151
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Budget activité sociale" AS "Budget activité sociale", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Budget activité sociale" 
ORDER BY "public"."Esat - Questionnaire 2024"."Budget activité sociale" ASC
```

## [471] Pourcentage moyen par ESAT de travailleurs partis pour une entreprise adaptée, pour le public, pour le privé ou pour une association

- **ID:** 7152
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis pour entreprise adaptée") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis pour le public") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis pour le privé") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis pour association") AS "avg_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Mise en place documents pour travailleurs en FALC (en % d'ESAT)

- **ID:** 7153
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Mise en place documents pour travailleurs en FALC" AS "Mise en place documents pour travailleurs en FALC", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Mise en place documents pour travailleurs en FALC" 
ORDER BY "public"."Esat - Questionnaire 2024"."Mise en place documents pour travailleurs en FALC" ASC
```

## [471] Pourcentage moyen du CA avec secteur public

- **ID:** 7154
- **Dashboard:** 471

```sql
[No SQL in native_form]
```

## [471] Nombre moyen de conseillers insertion et inclusion (en ETP)

- **ID:** 7155
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de conseillers insertion et inclusion") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Taux de contribution moyen OPCO Santé ou OPCA ANFH

- **ID:** 7156
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Taux de contribution Opco santé ou ANFH") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Type de complémentaire santé mise en place (en % d'ESAT)

- **ID:** 7157
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Complémentaire santé" AS "Complémentaire santé", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Complémentaire santé" 
ORDER BY "public"."Esat - Questionnaire 2024"."Complémentaire santé" ASC
```

## [471] Pourcentage d'ESAT ayant investi pour la production en 2023

- **ID:** 7158
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT CAST(SUM(CASE WHEN "public"."Esat - Questionnaire 2024"."Montant investissement production" > 0 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Pourcentage d'ESAT ayant investi pour la production en 2023" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Moyenne  du nombre de  salariés en droit commun (ETP)

- **ID:** 7159
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de salariés en droit commun") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Nombre moyen par ESAT de travailleurs partis pour une entreprise adaptée, pour le public, pour le privé ou pour une association

- **ID:** 7160
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour entreprise adaptée") AS "sum", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour le public") AS "sum_2", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour le privé") AS "sum_3", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis pour association") AS "sum_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage d'ESAT ayant reçu un soutien FATESAT, parmi les ESAT ayant investi pour leur production

- **ID:** 7161
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT CAST(SUM(CASE WHEN "public"."Esat - Questionnaire 2024"."Montant soutien FATESAT" > 0 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Pourcentage d'ESAT ayant reçu un soutien FATESAT" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant investissement production" > 0
```

## [471] Somme du nombre de travailleurs accompagnés

- **ID:** 7162
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs accompagnés") AS "sum" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage moyen de travailleurs ayant bénéficié d'une formation par les salariés de l'ESAT

- **ID:** 7163
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié formation par sa") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Mise en place d'une instance QVT

- **ID:** 7164
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Instance mixte QVT" AS "Instance mixte QVT", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Instance mixte QVT" 
ORDER BY "public"."Esat - Questionnaire 2024"."Instance mixte QVT" ASC
```

## [471] Nombre moyen par ESAT de travailleurs ayant effectué une PMSMP,  une prestation extérieure pour une entreprise, et une MAD (mise à disposition)

- **ID:** 7165
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant effectué une PMSMP") AS "sum", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant réalisé une prestation pour une ") AS "sum_2", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant réalisé une MAD") AS "sum_3" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Combien d'ESAT  ont eu des refus de PMSMP par des organismes du SPE?

- **ID:** 7166
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Refus de PMSMP par des organismes du SPE?" AS "Refus de PMSMP par des organismes du SPE?", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Refus de PMSMP par des organismes du SPE?" 
ORDER BY "public"."Esat - Questionnaire 2024"."Refus de PMSMP par des organismes du SPE?" ASC
```

## Budget activité sociale, au national

- **ID:** 7167
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Budget activité sociale" AS "Budget activité sociale", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Budget activité sociale" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Budget activité sociale" ASC
```

## [471] Pourcentage moyen de la rémunération des travailleurs prise en charge par l'ESAT

- **ID:** 7168
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de rémunération du travailleur pris en charge par") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Suite de parcours après RAE / RSFP

- **ID:** 7169
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Suite de parcours après reconnaissance - regroupé" AS "Suite de parcours après reconnaissance - regroupé", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant bénéficié de RAE ou RSFP" > 0 
GROUP BY "public"."Esat - Questionnaire 2024"."Suite de parcours après reconnaissance - regroupé" 
ORDER BY "public"."Esat - Questionnaire 2024"."Suite de parcours après reconnaissance - regroupé" ASC
```

## [471] Budget commercial

- **ID:** 7170
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Budget commercial" AS "Budget commercial", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Budget commercial" 
ORDER BY "public"."Esat - Questionnaire 2024"."Budget commercial" ASC
```

## Travailleurs en temps partiel, inscrits comme DE à France Travail, en cumul temps partiel entreprise adaptée et ESAT, en cumul temps partiel milieu ordinaire et ESAT

- **ID:** 7171
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs en temps partiel") AS "sum", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs inscrits comme DE à France travail") AS "sum_2", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant cumulé entreprise adaptée et tem") AS "sum_3", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant cumulé  milieu ordinaire et temps") AS "sum_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Mise en place auto sensibilisation (en % d'ESAT)

- **ID:** 7172
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Mise en place formation auto sensilibisation" AS "Mise en place formation auto sensilibisation", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Mise en place formation auto sensilibisation" 
ORDER BY "public"."Esat - Questionnaire 2024"."Mise en place formation auto sensilibisation" ASC
```

## [471] Mise en place d'un carnet de parcours et compétences (en % d'ESAT)

- **ID:** 7173
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Mise en place carnet de parcours et compétence" AS "Mise en place carnet de parcours et compétence", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Mise en place carnet de parcours et compétence" 
ORDER BY "public"."Esat - Questionnaire 2024"."Mise en place carnet de parcours et compétence" ASC
```

## [471] Conventions de partenariat (en % d'ESAT)

- **ID:** 7174
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Conventions partenariat - regroupé" AS "Conventions partenariat - regroupé", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Conventions partenariat - regroupé" 
ORDER BY "public"."Esat - Questionnaire 2024"."Conventions partenariat - regroupé" ASC
```

## [471] Pourcentage moyen du financement de la complémentaire santé par les ESAT

- **ID:** 7175
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage financement complémentaire santé ESAT") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage de travailleurs ayant bénéficié formation à l'auto sensibilisation, parmi les ESAT l'ayant mis en place, en 2023

- **ID:** 7176
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié formation auto s") AS "avg" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant bénéficié formation auto s" > 0
```

## Nombre moyen de travailleurs accompagnés par ESAT, au national

- **ID:** 7177
- **Tables:** ESAT, public

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs accompagnés") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## [471] Pourcentage d'ESAT public

- **ID:** 7178
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."ESAT public" AS "ESAT public", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."ESAT public" 
ORDER BY "public"."Esat - Questionnaire 2024"."ESAT public" ASC
```

## [471] Nombre moyen par ESAT de travailleurs partis avec CDI,  CDD, contrat intérim, contrat de professionalisation, contrat d'apprentissage

- **ID:** 7179
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec CDI") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs partis avec CDD") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec interim") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec contrat pro") AS "avg_4", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec contrat apprentissage") AS "avg_5" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage  de travailleurs ayant effectué une PMSMP,  une prestation extérieure pour une entreprise, et une MAD (mise à disposition)

- **ID:** 7180
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant effectué une PMSMP") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant réalisé une prestation pour") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant réalisé une MAD") AS "avg_3" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Nombre moyen par ESAT de travailleurs ayant effectué une PMSMP,  une prestation extérieure pour une entreprise, et une MAD (mise à disposition)

- **ID:** 7181
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant effectué une PMSMP") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant réalisé une prestation pour une ") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Nombre de travailleurs ayant réalisé une MAD") AS "avg_3" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Types de formation dont ont bénéficié les travailleurs pour reconnaître et développer leurs compétences

- **ID:** 7182
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Types de formations dont ont benéficié les travailleurs - reg" AS "Types de formations dont ont benéficié les travai_90d6594d", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Types de formations dont ont benéficié les travailleurs - reg" 
ORDER BY "public"."Esat - Questionnaire 2024"."Types de formations dont ont benéficié les travailleurs - reg" ASC
```

## [471] Travailleurs en temps partiel (%), inscrits comme DE à France Travail (%), en cumul temps partiel entreprise adaptée et ESAT (%), en cumul temps partiel milieu ordinaire et ESAT (%)

- **ID:** 7183
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs en temps partiel") AS "avg", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs inscrits comme DE à France travail") AS "avg_2", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant cumulé entreprise adaptée e") AS "avg_3", AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs ayant cumulé  milieu ordinaire et ") AS "avg_4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Pourcentage d'ESAT ayant investi pour la mise aux normes sécurité et accessibilité en 2023

- **ID:** 7184
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT CAST(SUM(CASE WHEN "public"."Esat - Questionnaire 2024"."Montant investissement mise aux normes sécurité accessibilit" > 0 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Pourcentage d'ESAT ayant investi pour la mise aux n_4ce75df4" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Travailleurs partis avec CDI,  CDD, contrat intérim, contrat de professionalisation, contrat d'apprentissage - Modifié

- **ID:** 7185
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec CDI") AS "sum", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec CDD") AS "sum_2", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec interim") AS "sum_3", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec contrat pro") AS "sum_4", SUM("public"."Esat - Questionnaire 2024"."Nombre de travailleurs partis avec contrat apprentissage") AS "sum_5" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Moyenne des places autorisées par ESAT

- **ID:** 7186
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Places autorisées par ARS") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Montant moyen de la prime d'intéressement par travailleur, pour les travailleurs l'ayant touché

- **ID:** 7187
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Montant moyen prime interessement des travailleurs") AS "avg" 
FROM "public"."Esat - Questionnaire 2024" 
WHERE "public"."Esat - Questionnaire 2024"."Montant moyen prime interessement des travailleurs" > 0
```

## Nombre de conseillers insertion et inclusion (en ETP)

- **ID:** 7188
- **Tables:** ESAT, public

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."nombre de conseillers") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## [471] Prime d'activité versée aux travailleurs (en % d'ESAT)

- **ID:** 7189
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Prime activité pour travailleurs" AS "Prime activité pour travailleurs", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Prime activité pour travailleurs" 
ORDER BY "public"."Esat - Questionnaire 2024"."Prime activité pour travailleurs" ASC
```

## Pourcentage moyen du CA avec secteur public

- **ID:** 7190
- **Tables:** ESAT, public

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Pourcentage du CA avec secteur public") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## [471] Election d'un délégué en 2023

- **ID:** 7191
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Délégué élu" AS "Délégué élu", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Délégué élu" 
ORDER BY "public"."Esat - Questionnaire 2024"."Délégué élu" ASC
```

## [471]  Pourcentage moyen de travailleurs sans utilisation CPF

- **ID:** 7192
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT AVG("public"."Esat - Questionnaire 2024"."Pourcentage de travailleurs sans utilisation CPF") AS "avg" 
FROM "public"."Esat - Questionnaire 2024"
```

## [471] Il y a t'il eu des refus de financement par l'OPCO Santé ou l'OPCA ANFH?

- **ID:** 7193
- **Dashboard:** 471
- **Tables:** public, Esat

```sql
SELECT "public"."Esat - Questionnaire 2024"."Refus de financement OPCO Santé ou ANFH" AS "Refus de financement OPCO Santé ou ANFH", COUNT(*) AS "count" 
FROM "public"."Esat - Questionnaire 2024" 
GROUP BY "public"."Esat - Questionnaire 2024"."Refus de financement OPCO Santé ou ANFH" 
ORDER BY "public"."Esat - Questionnaire 2024"."Refus de financement OPCO Santé ou ANFH" ASC
```

## Nombre de PMSMP réalisées, au national

- **ID:** 7194
- **Tables:** ESAT, public

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombres de PMSMP réalisées") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Mise en place d'une formation d'auto-sensibilisation pour les salarié(e)s de l'ESAT, au niveau national

- **ID:** 7195
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Mise en place formation auto sensibilisation pour les professio" AS "Mise en place formation auto sensibilisation pour l_2995b879", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Mise en place formation auto sensibilisation pour les professio" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Mise en place formation auto sensibilisation pour les professio" ASC
```

## Nombre d'ESAT ayant répondu au questionnaire

- **ID:** 7196
- **Tables:** ESAT, public

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre de MAD (mises à disposition), filtré sur la région choisie

- **ID:** 7197
- **Tables:** ESAT, public

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombre de MAD") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Partenariat Avec Entreprise Adaptée, filtré sur la région choisie

- **ID:** 7198
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Partenariats avec entreprise adaptée" AS "Partenariats avec entreprise adaptée", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Partenariats avec entreprise adaptée" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Partenariats avec entreprise adaptée" ASC
```

## Mise en place d'une instance mixte salariés / travailleurs sur QVT, hygiène et sécurité et éval risques pro, filtré sur la région choisie

- **ID:** 7199
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Instance mixte QVT" AS "Instance mixte QVT", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Instance mixte QVT" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Instance mixte QVT" ASC
```

## Mise en place d'une prime PEPA pour les travailleur(se)s, au national

- **ID:** 7200
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."PEPA" AS "PEPA", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."PEPA" 
ORDER BY "public"."ESAT - Questionnaire transfo"."PEPA" ASC
```

## Nombre moyen de salarié(e)s en droit commun

- **ID:** 7201
- **Tables:** ESAT, public

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Nombre de salariés en droit commun") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Moyenne de travailleur(se)s accompagné(e)s par ESAT, au national

- **ID:** 7202
- **Tables:** ESAT, public

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs accompagnés") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Budget commercial, au national

- **ID:** 7203
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Budget commercial" AS "Budget commercial", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
WHERE ("public"."ESAT - Questionnaire transfo"."Budget commercial" <> 'excédentaires') 
OR ("public"."ESAT - Questionnaire transfo"."Budget commercial" IS NULL) 
GROUP BY "public"."ESAT - Questionnaire transfo"."Budget commercial" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Budget commercial" ASC
```

## Mise en place d'une instance mixte salariés / travailleurs sur QVT, hygiène et sécurité et éval risques pro, au national

- **ID:** 7204
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Instance mixte QVT" AS "Instance mixte QVT", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Instance mixte QVT" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Instance mixte QVT" ASC
```

## Nombre de travailleurs inscrits à Pôle Emploi, filtré sur la région choisie

- **ID:** 7205
- **Tables:** ESAT, public

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs inscrits à Pôle Emploi") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre d'ESAT ayant répondu au questionnaire

- **ID:** 7206
- **Tables:** ESAT, public

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Moyenne des places agréées par ESAT, au national

- **ID:** 7207
- **Tables:** ESAT, public

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Nombre de places agréées") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Moyenne des places agréées par ESAT, au national - Dupliquer

- **ID:** 7208
- **Tables:** ESAT, public

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Nombre de places agréées") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Mise en place d'une prime PEPA pour les travailleur(se)s, filtré sur la région choisie

- **ID:** 7209
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."PEPA" AS "PEPA", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."PEPA" 
ORDER BY "public"."ESAT - Questionnaire transfo"."PEPA" ASC
```

## Budget activité sociale, au national

- **ID:** 7210
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Budget activité sociale" AS "Budget activité sociale", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Budget activité sociale" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Budget activité sociale" ASC
```

## Somme des Travailleurs parti de l'ESAT avec contrat CDI, CDD et intérim par Région

- **ID:** 7211
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Region" AS "Region", SUM("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs partis avec CDI") AS "sum", SUM("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs partis avec CDD") AS "sum_2", SUM("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs partis avec interim") AS "sum_3" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Region" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Region" ASC
```

## Convention de partenariat avec un ou plusieurs acteurs du SPE (pole emploi, cap emploi, ML) , au national

- **ID:** 7212
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Convention de partenariat" AS "Convention de partenariat", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Convention de partenariat" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Convention de partenariat" ASC
```

## Chiffre d'Affaires (CA) total moyen, pourcentage moyen du CA réalisé avec secteur public, par Région

- **ID:** 7213
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Region" AS "Region", AVG("public"."ESAT - Questionnaire transfo"."Montant du CA total") AS "avg", AVG("public"."ESAT - Questionnaire transfo"."Pourcentage du CA avec secteur public") AS "avg_2" 
FROM "public"."ESAT - Questionnaire transfo" 
WHERE ("public"."ESAT - Questionnaire transfo"."Region" <> 'Martinique') 
OR ("public"."ESAT - Questionnaire transfo"."Region" IS NULL) 
GROUP BY "public"."ESAT - Questionnaire transfo"."Region" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Region" ASC
```

## Budget commercial, filtré sur la région choisie

- **ID:** 7214
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Budget commercial" AS "Budget commercial", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
WHERE ("public"."ESAT - Questionnaire transfo"."Budget commercial" <> 'excédentaires') 
OR ("public"."ESAT - Questionnaire transfo"."Budget commercial" IS NULL) 
GROUP BY "public"."ESAT - Questionnaire transfo"."Budget commercial" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Budget commercial" ASC
```

## Pourcentage adhésion Opco et nombre moyen de travailleurs par ESAT ayant suivi une formation Opco, par Region

- **ID:** 7215
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Region" AS "Region", SUM(CASE WHEN "public"."ESAT - Questionnaire transfo"."OPCO" = 1 THEN 1 ELSE 0.0 END) / COUNT(*) AS "Pourcentage adhésion Opco", AVG("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs ayant suivi une formation OPCO") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Region" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Region" ASC
```

## Nombre de travailleurs en activité Hors les Murs, filtré sur la région choisie

- **ID:** 7216
- **Tables:** ESAT, public

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombres de travailleurs activité hors les murs") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre de travailleurs inscrits à Pôle Emploi, au national

- **ID:** 7217
- **Tables:** ESAT, public

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs inscrits à Pôle Emploi") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre de MAD (mises à disposition), au national

- **ID:** 7218
- **Tables:** ESAT, public

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombre de MAD") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre de travailleurs en activité Hors les Murs, au national

- **ID:** 7219
- **Tables:** ESAT, public

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombres de travailleurs activité hors les murs") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Partenariat Avec Entreprise Adaptée, au national

- **ID:** 7220
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Partenariats avec entreprise adaptée" AS "Partenariats avec entreprise adaptée", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Partenariats avec entreprise adaptée" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Partenariats avec entreprise adaptée" ASC
```

## Convention de partenariat avec un ou plusieurs acteurs du SPE (pole emploi, cap emploi, ML) , filtré sur la région choisie

- **ID:** 7221
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Convention de partenariat" AS "Convention de partenariat", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Convention de partenariat" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Convention de partenariat" ASC
```

## Nombre moyen de salarié(e)s en droit commun

- **ID:** 7222
- **Tables:** ESAT, public

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Nombre de salariés en droit commun") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Moyenne de travailleur(se)s accompagné(e)s par ESAT

- **ID:** 7223
- **Tables:** ESAT, public

```sql
SELECT AVG("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs accompagnés") AS "avg" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre de PMSMP réalisées, filtré sur la région choisie

- **ID:** 7224
- **Tables:** ESAT, public

```sql
SELECT SUM("public"."ESAT - Questionnaire transfo"."Nombres de PMSMP réalisées") AS "sum" 
FROM "public"."ESAT - Questionnaire transfo"
```

## Nombre de travailleurs cumulant ESAT et Entreprise adaptée ou Milieu ordinaire par Région

- **ID:** 7225
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Region" AS "Region", SUM("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs cumul ESAT EA") AS "sum", SUM("public"."ESAT - Questionnaire transfo"."Nombre de travailleurs cumul ESAT milieu ordinaire") AS "sum_2" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Region" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Region" ASC
```

## Mise en place d'une sensibilisation à l'auto-détermination pour les travailleurs

- **ID:** 7226
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Region" AS "Region", SUM(CASE WHEN "public"."ESAT - Questionnaire transfo"."Formation par un ou des professionnels de l’ESAT" = 'Formation par un ou des professionnels de l’ESAT' THEN 1 ELSE 0.0 END) AS "Formation interne", SUM(CASE WHEN "public"."ESAT - Questionnaire transfo"."Formation par un intervenant/organisme extérieur" = 'Formation par un intervenant/organisme extérieur' THEN 1 ELSE 0.0 END) AS "Formation intervenant extérieur", SUM(CASE WHEN "public"."ESAT - Questionnaire transfo"."Pas de formation mise en place" = 'Pas de formation mise en place' THEN 1 ELSE 0.0 END) AS "Pas de formation mise en place" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Region" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Region" ASC
```

## Mise en place d'une formation d'auto-sensibilisation pour les salarié(e)s de l'ESAT, filtré sur la région choisie

- **ID:** 7227
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Mise en place formation auto sensibilisation pour les professio" AS "Mise en place formation auto sensibilisation pour l_2995b879", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Mise en place formation auto sensibilisation pour les professio" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Mise en place formation auto sensibilisation pour les professio" ASC
```

## Budget activité sociale, filtré sur la région choisie

- **ID:** 7228
- **Tables:** ESAT, public

```sql
SELECT "public"."ESAT - Questionnaire transfo"."Budget activité sociale" AS "Budget activité sociale", COUNT(*) AS "count" 
FROM "public"."ESAT - Questionnaire transfo" 
GROUP BY "public"."ESAT - Questionnaire transfo"."Budget activité sociale" 
ORDER BY "public"."ESAT - Questionnaire transfo"."Budget activité sociale" ASC
```
