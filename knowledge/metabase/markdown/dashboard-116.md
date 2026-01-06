# Dashboard : Candidatures - Traitement et résultats des candidatures émises

☝️Attention : les données dans ce tableau de bord proviennent du service des emplois de l'inclusion. Dans le parcours des prescripteurs et des SIAE, **il ne leur est pas demandé de renseigner de manière exhaustives les critères des publics accompagnés**. 
Les prescripteurs n'ont pas l'obligation de renseigner ces informations lors de la validation de l'éligibilité du candidat à l'IAE. 
Les SIAE,  dans le cadre des auto-prescriptionS, sont tenues de renseigner un critère de niveau 1 ou plusieurs critères de niveau 2 mais elles n'ont pas l'obligation de déclarer tous les critères remplis par chaque candidat.
Dans tous les cas, ces données restent des données déclaratives.
Par conséquent, **les données que nous présentons ci-dessous servent à avoir une tendance, mais pas une vision exacte de la réalité**.

- ℹ︎ Par défaut, les données sont filtrées pour l'année précédente et pour les structures de l'IAE. Modifiez le filtre **Date** pour affiner votre besoin.
- ℹ︎ Les filtre EPCI et bassin

**16 cartes**

## [116] Etat des candidatures par domaine professionnel sur les 12 derniers mois - échelle locale

- **ID:** 7090
- **Thème:** candidatures
- **Tables:** fiches_de_poste_par_candidature, public, candidatures_echelle_locale, fiches_de_poste, code_rome_domaine_professionnel

```sql
SELECT "source"."Métier" AS "Métier", count(distinct "source"."id") AS "Nombre de candidatures", CAST(SUM(CASE WHEN "source"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures acceptées", CAST(SUM(CASE WHEN "source"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures refusées" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."état" AS "état", "public"."candidatures_echelle_locale"."reprise_de_stock_ai" AS "reprise_de_stock_ai", "Code Rome Domaine Professionnel"."domaine_professionnel" AS "Métier", "Fiches De Poste Par Candidature"."id_fiche_de_poste" AS "Fiches De Poste Par Candidature__id_fiche_de_poste", "Fiches De Poste Par Candidature"."id_candidature" AS "Fiches De Poste Par Candidature__id_candidature", "Fiches De Poste Par Candidature"."date_mise_à_jour_metabase" AS "Fiches De Poste Par Candidature__date_mise_à_jour_metabase", "Fiches De Poste"."id" AS "Fiches De Poste__id", "Fiches De Poste"."code_rome" AS "Fiches De Poste__code_rome", "Fiches De Poste"."nom_rome" AS "Fiches De Poste__nom_rome", "Fiches De Poste"."recrutement_ouvert" AS "Fiches De Poste__recrutement_ouvert", "Fiches De Poste"."type_contrat" AS "Fiches De Poste__type_contrat", "Fiches De Poste"."id_employeur" AS "Fiches De Poste__id_employeur", "Fiches De Poste"."type_employeur" AS "Fiches De Poste__type_employeur", "Fiches De Poste"."siret_employeur" AS "Fiches De Poste__siret_employeur", "Fiches De Poste"."nom_employeur" AS "Fiches De Poste__nom_employeur", "Fiches De Poste"."mises_a_jour_champs" AS "Fiches De Poste__mises_a_jour_champs", "Fiches De Poste"."département_employeur" AS "Fiches De Poste__département_employeur", "Fiches De Poste"."nom_département_employeur" AS "Fiches De Poste__nom_département_employeur", "Fiches De Poste"."région_employeu
-- ... (truncated)
```

## [116] Evolution des candidatures sur les 12 derniers mois, par état - échelle locale

- **ID:** 7091
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."état" AS "état", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" FROM "public"."candidatures_echelle_locale" WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non' GROUP BY "public"."candidatures_echelle_locale"."état", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) ORDER BY "public"."candidatures_echelle_locale"."état" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## [116]Etat des candidatures par métier sur les 3 derniers mois

- **ID:** 7093
- **Thème:** candidatures
- **Tables:** fiches_de_poste_par_candidature, public, fiches_de_poste, candidatures_echelle_locale, structures

```sql
SELECT "source"."Métier" AS "Métier", COUNT(*) AS "count", CAST(SUM(CASE WHEN "source"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures acceptées", CAST(SUM(CASE WHEN "source"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures refusées" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."état" AS "état", "public"."candidatures_echelle_locale"."reprise_de_stock_ai" AS "reprise_de_stock_ai", CONCAT("Fiches De Poste"."code_rome", ' - ', "Fiches De Poste"."nom_rome") AS "Métier", "Fiches De Poste Par Candidature"."id_fiche_de_poste" AS "Fiches De Poste Par Candidature__id_fiche_de_poste", "Fiches De Poste Par Candidature"."id_candidature" AS "Fiches De Poste Par Candidature__id_candidature", "Fiches De Poste Par Candidature"."date_mise_à_jour_metabase" AS "Fiches De Poste Par Candidature__date_mise_à_jour_metabase", "Fiches De Poste"."id" AS "Fiches De Poste__id", "Fiches De Poste"."code_rome" AS "Fiches De Poste__code_rome", "Fiches De Poste"."nom_rome" AS "Fiches De Poste__nom_rome", "Fiches De Poste"."recrutement_ouvert" AS "Fiches De Poste__recrutement_ouvert", "Fiches De Poste"."type_contrat" AS "Fiches De Poste__type_contrat", "Fiches De Poste"."id_employeur" AS "Fiches De Poste__id_employeur", "Fiches De Poste"."type_employeur" AS "Fiches De Poste__type_employeur", "Fiches De Poste"."siret_employeur" AS "Fiches De Poste__siret_employeur", "Fiches De Poste"."nom_employeur" AS "Fiches De Poste__nom_employeur", "Fiches De Poste"."mises_a_jour_champs" AS "Fiches De Poste__mises_a_jour_champs", "Fiches De Poste"."département_employeur" AS "Fiches De Poste__département_employeur", "Fiches De Poste"."nom_département_employeur" AS "Fiches De Poste__nom_départ
-- ... (truncated)
```

## [116] Taux candidatures déclinées

- **ID:** 7094
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures déclinées" FROM "public"."candidatures_echelle_locale" WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non'
```

## [116] Taux candidatures acceptées

- **ID:** 7095
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% Candidatures acceptées" FROM "public"."candidatures_echelle_locale" WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non'
```

## [116] Evolution des candidatures acceptées sur les 12 derniers mois, par type d'employeur - échelle locale

- **ID:** 7096
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) AS "date_embauche", COUNT(*) AS "count" FROM "public"."candidatures_echelle_locale" WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') GROUP BY "public"."candidatures_echelle_locale"."type_structure", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) ORDER BY "count" DESC, "public"."candidatures_echelle_locale"."type_structure" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) ASC
```

## [116] Evolution des candidatures, par type d'orienteur - échelle locale

- **ID:** 7097
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine" AS "origine", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) AS "date_embauche", COUNT(*) AS "count" FROM "public"."candidatures_echelle_locale" WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') GROUP BY "public"."candidatures_echelle_locale"."origine", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) ORDER BY "public"."candidatures_echelle_locale"."origine" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_embauche") AS date) ASC
```

## [116] Taux de refus des structures

- **ID:** 7099
- **Thème:** candidatures
- **Tables:** public, tx_refus_siae

```sql
SELECT "public"."tx_refus_siae"."type_structure" AS "type_structure", CAST(SUM("public"."tx_refus_siae"."nombre_candidatures_refusees") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."tx_refus_siae"."nombre_candidatures") AS DOUBLE PRECISION), 0.0) AS "Taux de refus", SUM("public"."tx_refus_siae"."nombre_candidatures") AS "Nombre de candidatures", SUM("public"."tx_refus_siae"."nombre_fiches_poste_ouvertes") AS "Nombre de postes ouverts", SUM("public"."tx_refus_siae"."nombre_siae") AS "Nombre de SIAE", SUM("public"."tx_refus_siae"."nombre_candidatures") - SUM("public"."tx_refus_siae"."nombre_candidatures_employeurs") AS "Nombre de candidatures hors auto-prescription", CAST(SUM("public"."tx_refus_siae"."nb_candidatures_refusees_non_emises_par_employeur_siae") AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."tx_refus_siae"."nombre_candidatures") - SUM("public"."tx_refus_siae"."nombre_candidatures_employeurs") AS DOUBLE PRECISION), 0.0) AS "Taux de refus hors auto-prescription" FROM "public"."tx_refus_siae" GROUP BY "public"."tx_refus_siae"."type_structure" ORDER BY "public"."tx_refus_siae"."type_structure" ASC
```

## [116]Motifs de refus des candidatures par type de prescripteurs - échelle locale

- **ID:** 7100
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine_détaillée" AS "origine_détaillée", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures acceptées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% de candidatures refusées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Embauche incompatible avec les objectifs du dialogue de gestion' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Embauche incompatible avec les objectifs du dialogu_bc7feb62", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Candidat non joignable' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Candidat non joignable", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Pas de recrutement en cours' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Pas de recrutement en cours", SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS "Nombre de candidatures refusées", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."motif_de_refus" = 'Candidat indisponible (en formation)' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature refusée' THEN 1 ELSE 0.0 END) AS DOUBLE PREC
-- ... (truncated)
```

## [116] Nombre total de candidatures

- **ID:** 7101
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" FROM "public"."candidatures_echelle_locale" WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non'
```

## [116] Evolution des candidatures sur les 12 derniers mois, par origine - échelle locale

- **ID:** 7102
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine" AS "origine", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" FROM "public"."candidatures_echelle_locale" WHERE ("public"."candidatures_echelle_locale"."injection_ai" = 0) AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') GROUP BY "public"."candidatures_echelle_locale"."origine", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) ORDER BY "public"."candidatures_echelle_locale"."origine" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## [116] Pourcentage de candidatures acceptées par type de prescripteur v2

- **ID:** 7103
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine_détaillée" AS "origine_détaillée", COUNT(*) AS "count", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% candidatures acceptées" FROM "public"."candidatures_echelle_locale" WHERE "public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non' GROUP BY "public"."candidatures_echelle_locale"."origine_détaillée" ORDER BY "count" DESC, "public"."candidatures_echelle_locale"."origine_détaillée" ASC
```

## [116] Motifs de refus actualisés (mensuel)

- **ID:** 7104
- **Thème:** candidatures
- **Tables:** structures, public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."motif_de_refus" AS "motif_de_refus", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" FROM "public"."candidatures_echelle_locale" LEFT JOIN "public"."structures" AS "Structures" ON "public"."candidatures_echelle_locale"."id_structure" = "Structures"."id" WHERE (("public"."candidatures_echelle_locale"."origine" = 'Orienteur') OR ("public"."candidatures_echelle_locale"."origine" = 'Prescripteur habilité')) AND ("public"."candidatures_echelle_locale"."état" = 'Candidature refusée') AND ("public"."candidatures_echelle_locale"."motif_de_refus" IS NOT NULL) AND (("public"."candidatures_echelle_locale"."motif_de_refus" <> '') OR ("public"."candidatures_echelle_locale"."motif_de_refus" IS NULL)) AND ("public"."candidatures_echelle_locale"."injection_ai" = 0) AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') GROUP BY "public"."candidatures_echelle_locale"."motif_de_refus", CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) ORDER BY "count" DESC, "public"."candidatures_echelle_locale"."motif_de_refus" ASC, CAST(DATE_TRUNC('month', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## [116]Profil des candidats embauchés

- **ID:** 7105
- **Thème:** candidatures
- **Tables:** candidats, public

```sql
SELECT CAST(DATE_TRUNC('month', "source"."date_diagnostic") AS date) AS "date_diagnostic", "source"."pivot-grouping" AS "pivot-grouping", CAST(SUM(CASE WHEN "source"."critère_n1_bénéficiaire_du_rsa" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression", CAST(SUM(CASE WHEN "source"."critère_n1_detld_plus_de_24_mois" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression_2", CAST(SUM(CASE WHEN "source"."critère_n2_deld_12_à_24_mois" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression_3", CAST(SUM(CASE WHEN "source"."critère_n2_jeune_moins_de_26_ans" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression_4", CAST(SUM(CASE WHEN "source"."critère_n2_résident_qpv" = 1 THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "expression_5" FROM (SELECT "public"."candidats"."total_embauches" AS "total_embauches", "public"."candidats"."date_diagnostic" AS "date_diagnostic", "public"."candidats"."type_structure_dernière_embauche" AS "type_structure_dernière_embauche", "public"."candidats"."critère_n1_bénéficiaire_du_rsa" AS "critère_n1_bénéficiaire_du_rsa", "public"."candidats"."critère_n1_detld_plus_de_24_mois" AS "critère_n1_detld_plus_de_24_mois", "public"."candidats"."critère_n2_jeune_moins_de_26_ans" AS "critère_n2_jeune_moins_de_26_ans", "public"."candidats"."critère_n2_deld_12_à_24_mois" AS "critère_n2_deld_12_à_24_mois", "public"."candidats"."critère_n2_résident_qpv" AS "critère_n2_résident_qpv", ABS(0) AS "pivot-grouping" FROM "public"."candidats" WHERE (("public"."candidats"."total_embauches" <> 0) OR ("public"."candidats"."total_embauches" IS NULL)) AND (("public"."candidats"."type_structure_dernière_embauche" = 'ACI') OR ("public"."candidats"."type_structure_dernière_embauche" = 'AI') OR ("public"."can
-- ... (truncated)
```

## [116] Evolution annuelle des candidatures, par origine

- **ID:** 7106
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."origine" AS "origine", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) AS "date_candidature", COUNT(*) AS "count" FROM "public"."candidatures_echelle_locale" WHERE ("public"."candidatures_echelle_locale"."date_candidature" > date '2021-01-01') AND ("public"."candidatures_echelle_locale"."injection_ai" = 0) AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') GROUP BY "public"."candidatures_echelle_locale"."origine", CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ORDER BY "public"."candidatures_echelle_locale"."origine" ASC, CAST(DATE_TRUNC('year', "public"."candidatures_echelle_locale"."date_candidature") AS date) ASC
```

## [116] Nombre total de candidatures en cours

- **ID:** 7107
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT count(distinct "public"."candidatures_echelle_locale"."id") AS "count" FROM "public"."candidatures_echelle_locale" WHERE (("public"."candidatures_echelle_locale"."état" = 'Candidature à l''étude') OR ("public"."candidatures_echelle_locale"."état" = 'Candidature en attente') OR ("public"."candidatures_echelle_locale"."état" = 'Nouvelle candidature')) AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non')
```
