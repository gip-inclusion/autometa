# Dashboard : Candidatures - Bilan annuel des candidatures émises vers les SIAE

⚠️​  Le taux d'acceptation et de refus ne représente pas 100% car il y a d'autres catégories telles que "nouvelle candidature", "en attente" et "à l'étude" qui ne sont pas incluses dans le graphique.  Ces 3 dernières catégories sont considérées comme toujours en cours de traitement.

⚠️​ L'évolution des données de candidature s'étend sur plusieurs mois, car une candidature reste active jusqu'à sa clôture ou son archivage automatique ou manuel par la SIAE. 

​





#### 💡 Types de prescripteurs et de SIAE
- **Nouveaux prescripteurs** : se sont [Les nouveaux prescripteurs habilités au national depuis 2021](https://aide.emplois.inclusion.beta.gouv.fr/hc/fr/articles/14733442624657--Liste-des-prescripteurs-habilit%C3%A9s-au-national) Ces professionnels proposent les candidatures des publics qu'ils accompagnent et sont autorisés à valider l'éligibilité à un parcours IAE d'un candidat.
- **Autre** : se sont les prescripteurs habilités par arrêté préfectoral.
- **SPE** : Service Public de l'Em

**URL:** /tableaux-de-bord/etat-suivi-candidatures/

**5 cartes**

## [337] Nombre de structures antenne

- **ID:** 7028
- **Thème:** employeurs
- **Tables:** public, structures

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."structures" 
WHERE ("public"."structures"."date_inscription" IS NOT NULL) 
AND ("public"."structures"."source" = 'Utilisateur (Antenne)') 
AND (("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI')) 
AND (("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI'))
```

## [337] Nombre de structures mère

- **ID:** 7048
- **Thème:** employeurs
- **Tables:** public, structures

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."structures" 
WHERE ("public"."structures"."date_inscription" IS NOT NULL) 
AND (("public"."structures"."source" = 'Export ASP') 
OR ("public"."structures"."source" = 'Staff Itou')) 
AND (("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI'))
```

## [337] Nombre total (mère + antenne) de structures sur les emplois

- **ID:** 7057
- **Thème:** employeurs
- **Tables:** public, structures

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."structures" 
WHERE ("public"."structures"."date_inscription" IS NOT NULL) 
AND (("public"."structures"."source" = 'Utilisateur (Antenne)') 
OR ("public"."structures"."source" = 'Export ASP') 
OR ("public"."structures"."source" = 'Staff Itou')) 
AND (("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI')) 
AND (("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI'))
```

## [337] Nombre de structures antenne

- **ID:** 7235
- **Thème:** employeurs
- **Tables:** public, structures

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."structures" 
WHERE ("public"."structures"."date_inscription" IS NOT NULL) 
AND ("public"."structures"."source" = 'Utilisateur (Antenne)') 
AND (("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI')) 
AND (("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI'))
```

## [337] Nombre de structures mère

- **ID:** 7236
- **Thème:** employeurs
- **Tables:** public, structures

```sql
SELECT COUNT(*) AS "count" 
FROM "public"."structures" 
WHERE ("public"."structures"."date_inscription" IS NOT NULL) 
AND (("public"."structures"."source" = 'Export ASP') 
OR ("public"."structures"."source" = 'Staff Itou')) 
AND (("public"."structures"."type" = 'ACI') 
OR ("public"."structures"."type" = 'AI') 
OR ("public"."structures"."type" = 'EI') 
OR ("public"."structures"."type" = 'EITI') 
OR ("public"."structures"."type" = 'ETTI'))
```
