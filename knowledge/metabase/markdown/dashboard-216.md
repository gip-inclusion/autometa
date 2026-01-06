# Dashboard : Publics - Représentation des femmes dans les candidatures vers l'IAE

*Vers quels secteurs et métiers de l'IAE les femmes sont-elles orientées et recrutées ?*

*Comment les femmes candidatent-elles dans l'inclusion ? Par quels prescripteurs sont-elles accompagnées ?*

*Quels sont les départements dans les quels les femmes sont sous-représentées dans les candidatures en IAE  ?*

💡 Les chiffres en légende indiquent la part de candidatures qui concernent les femmes. Plus un département apparaît foncé, plus les hommes sont sur-représentés dans les candidatures émises.

*Quels sont les taux d'acceptations des candidatures sur mon territoire en fonction du genre du candidat ?*

💡 Le taux d'acceptation pour un genre indique la proportion de candidatures acceptées pour ce genre par rapport au nombre total de candidatures pour ce genre.

# 

*Quelle mixité dans les candidatures acceptées en fonction de l'origine de la candidature ?*

*Quelle mixité dans les candidatures émises en fonction de l'origine de la candidature ?*

*Quelle mixité dans les candidatures reç

**URL:** /tableaux-de-bord/femmes-iae/

**33 cartes**

## [216] part de femmes dans les candidatures émises - département

- **ID:** 7075
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" FROM "public"."candidatures_echelle_locale" WHERE (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) AND ("public"."candidatures_echelle_locale"."date_inscription_candidat" > date '2021-11-01') AND (("public"."candidatures_echelle_locale"."genre_candidat" = 'Homme') OR ("public"."candidatures_echelle_locale"."genre_candidat" = 'Femme')) GROUP BY "public"."candidatures_echelle_locale"."département_structure" ORDER BY "public"."candidatures_echelle_locale"."département_structure" ASC
```

## [216] part de femmes dans les candidatures acceptées - département

- **ID:** 7076
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" FROM "public"."candidatures_echelle_locale" WHERE (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) AND ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') AND ("public"."candidatures_echelle_locale"."date_inscription_candidat" > date '2021-11-01') AND (("public"."candidatures_echelle_locale"."genre_candidat" = 'Femme') OR ("public"."candidatures_echelle_locale"."genre_candidat" = 'Homme')) GROUP BY "public"."candidatures_echelle_locale"."département_structure" ORDER BY "public"."candidatures_echelle_locale"."département_structure" ASC
```

## [216] budget genré

- **ID:** 7238
- **Thème:** demographie
- **Tables:** etp_par_salarie, public

```sql
SELECT "public"."etp_par_salarie"."emi_sme_annee" AS "emi_sme_annee", CAST(SUM(CASE WHEN "public"."etp_par_salarie"."genre_salarie" = 'Homme' THEN "public"."etp_par_salarie"."montant_alloue" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."etp_par_salarie"."montant_alloue") AS DOUBLE PRECISION), 0.0) AS "Part du budget alloué aux hommes", CAST(SUM(CASE WHEN "public"."etp_par_salarie"."genre_salarie" = 'Femme' THEN "public"."etp_par_salarie"."montant_alloue" ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM("public"."etp_par_salarie"."montant_alloue") AS DOUBLE PRECISION), 0.0) AS "Part du budget alloué aux femmes" FROM "public"."etp_par_salarie" WHERE ("public"."etp_par_salarie"."genre_salarie" = 'Femme') OR ("public"."etp_par_salarie"."genre_salarie" = 'Homme') GROUP BY "public"."etp_par_salarie"."emi_sme_annee" ORDER BY "public"."etp_par_salarie"."emi_sme_annee" ASC
```

## [216] part de femmes dans candidatures acceptées - national

- **ID:** 7308
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes acceptées" FROM "public"."candidatures_echelle_locale" WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') AND (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) AND ("public"."candidatures_echelle_locale"."date_inscription_candidat" > date '2021-11-01') AND (("public"."candidatures_echelle_locale"."genre_candidat" = 'Homme') OR ("public"."candidatures_echelle_locale"."genre_candidat" = 'Femme'))
```

## [216] répartition des candidatures par origine candidat - tous

- **ID:** 7309
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."origine" AS "origine", COUNT(*) AS "count" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection
-- ... (truncated)
```

## [216] % candidatures hommes

- **ID:** 7310
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% hommes" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_loc
-- ... (truncated)
```

## [216] orientation SIAE - tous

- **ID:** 7311
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."type_structure" AS "type_structure", COUNT(*) AS "count" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai"
-- ... (truncated)
```

## [216] nb de candidatures acceptées

- **ID:** 7312
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT COUNT(*) AS "count" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_eche
-- ... (truncated)
```

## [216] taux acceptation des candidatures (global)

- **ID:** 7313
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "source"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidature
-- ... (truncated)
```

## [216] Part femmes hommes chez les candidats

- **ID:** 7314
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."genre_candidat" AS "genre_candidat", count(distinct "source"."id_candidat") AS "Nb candidats acceptés" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public
-- ... (truncated)
```

## [216] % candidatures femmes

- **ID:** 7315
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "% femmes dans les candidatures" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."ca
-- ... (truncated)
```

## [216] Répartition du genre chez les candidats

- **ID:** 7316
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."genre_candidat" AS "genre_candidat", count(distinct "source"."id_candidat") AS "Nombre de candidats" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public".
-- ... (truncated)
```

## [216] Part femmes hommes chez les candidats acceptés

- **ID:** 7317
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."genre_candidat" AS "genre_candidat", count(distinct "source"."id_candidat") AS "Nb candidats acceptés" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public
-- ... (truncated)
```

## [216] part femme homme acceptés par SIAE

- **ID:** 7318
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."type_structure" AS "type_structure", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur"
-- ... (truncated)
```

## [216] Part d'hommes et de femmes dans les candidatures acceptées en fonction de l'origine de la candidature

- **ID:** 7319
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."origine" AS "origine", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."ca
-- ... (truncated)
```

## [216] orientation SIAE selon genre

- **ID:** 7320
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."type_structure" AS "type_structure", "source"."genre_candidat" AS "genre_candidat", COUNT(*) AS "count" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "publi
-- ... (truncated)
```

## [216] Taux acceptation femmes

- **ID:** 7321
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN ("source"."genre_candidat" = 'Femme') AND ("source"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation femme" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", 
-- ... (truncated)
```

## [216] part de femmes dans les candidatures acceptées - département

- **ID:** 7322
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."département_structure" AS "département_structure", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur"
-- ... (truncated)
```

## [216] part femme homme par SIAE

- **ID:** 7323
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."type_structure" AS "type_structure", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur"
-- ... (truncated)
```

## [216] part d'hommes et de femmes dans les candidatures en fonction de l'origine détaillée

- **ID:** 7324
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."origine_détaillée" AS "origine_détaillée", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescri
-- ... (truncated)
```

## [216] Taux acceptation par genre par département

- **ID:** 7325
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."nom_département_structure" AS "nom_département_structure", CAST(SUM(CASE WHEN ("source"."genre_candidat" = 'Femme') AND ("source"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation femme", CAST(SUM(CASE WHEN ("source"."genre_candidat" = 'Homme') AND ("source"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation homme", CAST(SUM(CASE WHEN "source"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation global" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "p
-- ... (truncated)
```

## [216] candidatures par domaine

- **ID:** 7326
- **Thème:** demographie
- **Tables:** metier_candidatures, public

```sql
SELECT "public"."metier_candidatures"."metier" AS "metier", CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de candidatures femmes émises", CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de candidatures hommes émises", CAST(SUM(CASE WHEN ("public"."metier_candidatures"."genre_candidat" = 'Femme') AND ("public"."metier_candidatures"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation des femmes", CAST(SUM(CASE WHEN ("public"."metier_candidatures"."genre_candidat" = 'Homme') AND ("public"."metier_candidatures"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation des hommes", COUNT(*) AS "Nombre de candidatures émises", SUM(CASE WHEN "public"."metier_candidatures"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS "Nombre de candidatures acceptées" FROM "public"."metier_candidatures" WHERE (("public"."metier_candidatures"."type_structure" = 'ACI') OR ("public"."metier_candidatures"."type_structure" = 'AI') OR ("public"."metier_candidatures"."type_structure" = 'EI') OR ("public"."metier_candidatures"."type_structure" = 'EITI') OR ("public"."metier_candidatures"."type_structure" = 'ETTI')) AND ("public"."metier_candidatures"."date_inscription_candidat" > date '2021-11-01') AND (("public"."metier_candidatures"."genre_candidat" = 'Femme') OR ("public"."metier_candidatures"."genre_candidat" = 'Homme')) GROUP BY "public"."metier_candidatures"."metier" ORDER BY "publ
-- ... (truncated)
```

## [216] part d'hommes et de femmes dans les candidatures acceptées en fonction de l'origine détaillée

- **ID:** 7327
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."origine_détaillée" AS "origine_détaillée", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescri
-- ... (truncated)
```

## [216] Répartition du genre dans les candidatures

- **ID:** 7328
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."genre_candidat" AS "genre_candidat", COUNT(*) AS "count" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai"
-- ... (truncated)
```

## [216] Nombre de candidats acceptés

- **ID:** 7329
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT count(distinct "source"."id_candidat") AS "Nb candidats acceptés" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" 
-- ... (truncated)
```

## [216] Part d'hommes et de femmes dans les candidatures en fonction de l'origine de la candidature

- **ID:** 7330
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."origine" AS "origine", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."ca
-- ... (truncated)
```

## [216] Nombre de candidats

- **ID:** 7331
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT count(distinct "source"."id_candidat") AS "Nb candidats acceptés" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" 
-- ... (truncated)
```

## [216] part de femmes dans les candidatures - département

- **ID:** 7332
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."département_structure" AS "département_structure", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de femmes", CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) * 100 AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur"
-- ... (truncated)
```

## [216] nb candidatures

- **ID:** 7333
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT COUNT(*) AS "count" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatures_echelle_locale"."injection_ai" AS "injection_ai", "public"."candidatures_eche
-- ... (truncated)
```

## [216] part d'hommes dans candidatures acceptées - national

- **ID:** 7334
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN "public"."candidatures_echelle_locale"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part d'hommes acceptés" FROM "public"."candidatures_echelle_locale" WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature acceptée') AND (("public"."candidatures_echelle_locale"."type_structure" = 'ACI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'AI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'EITI') OR ("public"."candidatures_echelle_locale"."type_structure" = 'ETTI')) AND ("public"."candidatures_echelle_locale"."date_inscription_candidat" > date '2021-11-01') AND (("public"."candidatures_echelle_locale"."genre_candidat" = 'Femme') OR ("public"."candidatures_echelle_locale"."genre_candidat" = 'Homme'))
```

## [216] répartition des candidatures par origine candidat et par genre

- **ID:** 7335
- **Thème:** demographie
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "source"."origine" AS "origine", "source"."genre_candidat" AS "genre_candidat", COUNT(*) AS "count" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", "public"."candidatures_echelle_locale"."nom_prénom_conseiller" AS "nom_prénom_conseiller", "public"."candidatures_echelle_locale"."date_embauche" AS "date_embauche", "public"."candidatur
-- ... (truncated)
```

## [216] candidatures par métier

- **ID:** 7336
- **Thème:** demographie
- **Tables:** metier_candidatures, public

```sql
SELECT "public"."metier_candidatures"."nom_rome" AS "nom_rome", CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de candidatures femmes émises", CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(COUNT(*) AS DOUBLE PRECISION), 0.0) AS "Part de candidatures hommes émises", CAST(SUM(CASE WHEN ("public"."metier_candidatures"."genre_candidat" = 'Femme') AND ("public"."metier_candidatures"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Femme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation des femmes", CAST(SUM(CASE WHEN ("public"."metier_candidatures"."genre_candidat" = 'Homme') AND ("public"."metier_candidatures"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "public"."metier_candidatures"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation des hommes", COUNT(*) AS "Nombre de candidatures émises", SUM(CASE WHEN "public"."metier_candidatures"."état" = 'Candidature acceptée' THEN 1 ELSE 0.0 END) AS "Nombre de candidatures acceptées" FROM "public"."metier_candidatures" WHERE (("public"."metier_candidatures"."type_structure" = 'ACI') OR ("public"."metier_candidatures"."type_structure" = 'AI') OR ("public"."metier_candidatures"."type_structure" = 'EI') OR ("public"."metier_candidatures"."type_structure" = 'EITI') OR ("public"."metier_candidatures"."type_structure" = 'ETTI')) AND ("public"."metier_candidatures"."date_inscription_candidat" > date '2021-11-01') AND ("public"."metier_candidatures"."genre_candidat" IS NOT NULL) AND (("public"."metier_candidatures"."genre_candidat" <> '') OR ("public"."metier_candidatures"."genre_candidat" IS NULL))
-- ... (truncated)
```

## [216] Taux acceptation hommes

- **ID:** 7337
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT CAST(SUM(CASE WHEN ("source"."genre_candidat" = 'Homme') AND ("source"."état" = 'Candidature acceptée') THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION) / NULLIF(CAST(SUM(CASE WHEN "source"."genre_candidat" = 'Homme' THEN 1 ELSE 0.0 END) AS DOUBLE PRECISION), 0.0) AS "Taux acceptation homme" FROM (SELECT "public"."candidatures_echelle_locale"."id" AS "id", "public"."candidatures_echelle_locale"."candidature_refusée_automatiquement" AS "candidature_refusée_automatiquement", "public"."candidatures_echelle_locale"."date_candidature" AS "date_candidature", "public"."candidatures_echelle_locale"."date_début_contrat" AS "date_début_contrat", "public"."candidatures_echelle_locale"."date_traitement" AS "date_traitement", "public"."candidatures_echelle_locale"."origine_id_structure" AS "origine_id_structure", "public"."candidatures_echelle_locale"."parcours_de_création" AS "parcours_de_création", "public"."candidatures_echelle_locale"."délai_prise_en_compte" AS "délai_prise_en_compte", "public"."candidatures_echelle_locale"."délai_de_réponse" AS "délai_de_réponse", "public"."candidatures_echelle_locale"."id_candidat" AS "id_candidat", "public"."candidatures_echelle_locale"."id_structure" AS "id_structure", "public"."candidatures_echelle_locale"."type_structure" AS "type_structure", "public"."candidatures_echelle_locale"."nom_structure" AS "nom_structure", "public"."candidatures_echelle_locale"."nom_complet_structure" AS "nom_complet_structure", "public"."candidatures_echelle_locale"."département_structure" AS "département_structure", "public"."candidatures_echelle_locale"."nom_département_structure" AS "nom_département_structure", "public"."candidatures_echelle_locale"."région_structure" AS "région_structure", "public"."candidatures_echelle_locale"."id_org_prescripteur" AS "id_org_prescripteur", "public"."candidatures_echelle_locale"."nom_org_prescripteur" AS "nom_org_prescripteur", "public"."candidatures_echelle_locale"."safir_org_prescripteur" AS "safir_org_prescripteur", 
-- ... (truncated)
```
