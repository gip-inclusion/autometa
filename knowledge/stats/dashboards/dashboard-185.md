# Dashboard : SIAE - Analyse des candidatures reçues et de leur traitement

## Quel est le traitement des candidatures pour chaque prescripteur habilité partenaire ?

Utilisez les filtres **origine détaillée de la candidature** et **nom de l'orienteur** pour une analyse affinée par partenaire prescripteur.

Avec le filtre **Origine détaillée de la candidature**, vous pouvez obtenir le volume des candidatures reçues d'un prescripteur type, suivre leur traitement et analyser les résultats. Voici quelques exemples :
- Pour les résultats des **acteurs AHI** : cochez CHRS, CHU, les opérateurs d'intermédiation locative, les résidences sociales/foyers de jeunes travailleurs.
- Sélectionnez le **service social du conseil départemental** et l'**organisation délégataire d'un conseil départemental** pour obtenir les prescriptions des acteurs accompagnant les **publics allocataires du RSA**.
- Pour votre partenariat avec le SPE (Service Public de l’Emploi), choisissez France Travail, Mission locale et Cap emploi.

#### *Combien de candidatures avez-vous reçu par état, cha

**1 cartes**

## [185] Repartition des motifs de refus

- **ID:** 7098
- **Thème:** candidatures
- **Tables:** public, candidatures_echelle_locale

```sql
SELECT "public"."candidatures_echelle_locale"."motif_de_refus" AS "motif_de_refus", COUNT(*) AS "count" 
FROM "public"."candidatures_echelle_locale" 
WHERE ("public"."candidatures_echelle_locale"."état" = 'Candidature refusée') 
AND ("public"."candidatures_echelle_locale"."reprise_de_stock_ai" = 'Non') 
AND ("public"."candidatures_echelle_locale"."motif_de_refus" IS NOT NULL) 
AND (("public"."candidatures_echelle_locale"."motif_de_refus" <> '') 
OR ("public"."candidatures_echelle_locale"."motif_de_refus" IS NULL)) 
GROUP BY "public"."candidatures_echelle_locale"."motif_de_refus" 
ORDER BY "count" DESC, "public"."candidatures_echelle_locale"."motif_de_refus" ASC
```
