---
source: matomo:136
verifie_le: 2026-11-09
---
# Le Marché de l'inclusion

- URL : https://lemarche.inclusion.gouv.fr (ancienne adresse `lemarche.inclusion.beta.gouv.fr`, encore utilisée comme expéditeur des e-mails)
- Matomo site ID : 136
- Tag Manager : oui (Matomo Tag Manager ; c'est lui qui porte tous les événements)
- GitHub : https://github.com/gip-inclusion/le-marche (branche `main`)
- Funnel bizdev : [glossaire AARRI](../bizdev/glossaire.md) — archétype marketplace.

## Fiches liées

| Fiche | Contenu |
|---|---|
| **Cette fiche** | Matomo : ce que le tracking voit et ne voit pas, dimensions, segments, objectifs, événements, campagnes |
| `knowledge/marche/README.md` | Base applicative (`raw_marche`), modèle besoin → structure, e-mails (Brevo), logs serveur (Datadog), spam, pièges de mesure |

**Pour l'usage métier (besoins, réponses des structures, mises en relation), partir de la base, pas de Matomo.** Matomo sert au trafic, à l'annuaire et aux campagnes.

## Références de trafic

Les chiffres de trafic de ce site — visites, visiteurs, rebond, durée, répartition par type
d'utilisateur — sont synchronisés chaque nuit dans la base applicative
(`matomo_baselines`) et consultables par le skill `matomo_query`. Ils ne sont pas recopiés
ici : une valeur figée dans un fichier devient fausse sans prévenir.

## Ce que Matomo voit — et ne voit pas

- **Les URL sont des motifs de route Django**, pas les URL réelles (`setCustomUrl`) : `/prestataires/<str:slug>/`, `/besoins/<slug>`. Impossible de compter les vues d'une fiche ou d'un besoin précis dans Matomo. Seuls les paramètres `utm_*`, `mtm_*` et `piwik_*` sont conservés.
- **Les pages du CMS Wagtail** (accueil, `/accueil-structure/`, `/ressources/…`) sont toutes regroupées sous un même libellé de motif.
- **Chargement après consentement** (tarteaucitron) : une partie des visiteurs humains manque.
- **Les robots sont invisibles** (ils n'exécutent pas le JavaScript). Les vagues d'inscriptions automatisées ne se voient que dans les logs serveur — voir `knowledge/marche/README.md` § Spam.
- **`userId` = identifiant utilisateur du Marché**, ce qui permet un rapprochement avec `raw_marche.users_user.id`.
- **Environ 3 % des visites sont connectées** : les dimensions ne décrivent qu'une petite minorité.
- **Aucun événement n'est poussé par le code** : tout vient du conteneur Tag Manager, modifiable sans déploiement.

## Custom Dimensions

| ID | Index | Scope | Nom | Valeurs |
|---|---|---|---|---|
| 1 | 1 | visit | User Type | `SIAE`, `BUYER`, `PARTNER`, `INDIVIDUAL`, `ADMIN` (connectés seulement) |
| 2 | 2 | visit | User Type Detail | Type + détail, libellés accentués : « Structure », « Acheteur : Grand groupe », « Acheteur : PME », « Acheteur : Établissement public », « Acheteur : Collectivité », « Partenaire : Facilitateur clauses sociales », « Prescripteur », « Réseaux IAE »… |

Les dimensions sont sensibles à la casse : le segment `dimension1==buyer` (minuscules) ne renvoie rien.

## Saved Segments

| Nom | Définition |
|---|---|
| ACTION - Recherche non loggée | `eventAction=@recherche;dimension1!@A;dimension1!@E` |
| Buyer | `dimension1==buyer` (⚠️ casse : vide) |
| buyer actif | `dimension1==BUYER;pageUrl=@besoins,pageUrl=@login,pageUrl=@p…` |
| BUYERS | `dimension1==BUYER` |
| EXIT - Tally | `outlinkUrl=@tally` |
| PROFILE - Acheteurs + déposer un besoin | `form_name==tender-create-survey-form,dimension1=@BUYER` |
| PROFILE - BUYER | `dimension1==buyer;outlinkUrl!@tally` (⚠️ casse) |
| PROFILE - INDIVIDUAL | `dimension1==INDIVIDUAL` |
| PROFILE - SIAE | `dimension1==SIAE` |
| RETENTION - dernière visite 30j | `daysSinceLastVisit<32;daysSinceLastVisit>=1` |
| RETENTION - dernière visite 30j - Acheteurs | `dimension2=@Acheteur;daysSinceLastVisit<32;…` |
| RETENTION - dernière visite 30j - Structures | `daysSinceLastVisit<32;dimension2=@structure;…` (⚠️ casse : « Structure ») |
| RETENTION NON PRO - dernière visite 30j | `daysSinceLastVisit<32;daysSinceLastVisit>=1;outlinkUrl=@tall…` |

## Goals

Vérifiés par `Goals.getGoals` le 2026-11-09. Aucun objectif ne compte plusieurs conversions par visite.

| ID | Nom | Déclencheur |
|---|---|---|
| 4 | Inscription utilisateur | event_action exact `Inscription` |
| 5 | Publication de besoin | event_action exact `Publier et diffuser le besoin` |
| 8 | Recherche | event_action exact `Clic rechercher - Moteur recherche` |
| 9 | Consultation tableau de bord acheteur | URL exacte `https://lemarche.inclusion.gouv.fr/besoins/` (convertit depuis mars 2026 seulement) |
| 10 | Demander une démo - LP Auditer vos achats | event_name exact `Clic bouton CTA - Demander une démo` |
| 11 | Demander une démo - LP analyse prog achats | event_name exact `Clic bouton CTA - Demander une démo - analyse prog achats` |

Les anciens objectifs 6 (« Afficher les coordonnées ») et 7 (« Télécharger la liste ») n'existent plus.

L'objectif 5 ne compte que les besoins publiés par le formulaire du site : les besoins venus de Tally, de l'API partenaire ou créés par l'équipe n'y sont pas.

## Événements (Tag Manager)

| Catégorie | Contenu |
|---|---|
| All link clicks | Tous les clics de lien, capturés automatiquement. Le **nom** de l'événement est le `href` cliqué (`#`, `/`, `/accounts/login/`, URL externes…) : ce ne sont **pas** des pages vues |
| Clic bouton | Boutons métier, nommés à la main dans le Tag Manager |
| Clic lien | Liens métier, dont `Clic website SIAE - fiche commerciale` |
| Formulaire | Inscription et étapes du dépôt de besoin |

Actions utiles :

| Action | Sens |
|---|---|
| `Clic rechercher - Moteur recherche` | Recherche de prestataires (objectif 8) |
| `Clic recherche SIRET - Moteur recherche` | Recherche par SIRET |
| `Clic website SIAE - fiche commerciale` | Clic vers le site d'une structure depuis sa fiche : signal d'intérêt acheteur dans l'annuaire |
| `Inscription` | Inscription (objectif 4) |
| `Dépôt de besoin - Step 1`, `Step 3`, `Step 4` | Étapes du formulaire de besoin. **Il n'y a pas d'étape 2** |
| `Publier et diffuser le besoin` | Fin du formulaire (objectif 5) |
| `Clic sourcing inversé - Header`, `Clic trouver un facilitateur - Header`, `Clic valoriser vos achats - Header`, `Clic calculer impact social - Header`, `Clic Publier un besoin - Résultats recherche` | Entrées de navigation |

## Pages clés (motifs)

| Motif | Rôle |
|---|---|
| `/prestataires/` | Recherche dans l'annuaire |
| `/prestataires/<str:slug>/` | Fiche d'une structure — l'essentiel des pages vues du site |
| `/besoins/ajouter/` | Formulaire de dépôt de besoin |
| `/besoins/` | Tableau de bord acheteur, liste de ses besoins (objectif 9) |
| `/besoins/<slug>` | Détail d'un besoin (vu par acheteurs et structures) |
| `/besoins/inspirants` | Besoins « inspirants », page apparue en juillet 2026 |
| `/accounts/signup/`, `/accounts/login/` | Inscription, connexion |
| `/profil/` | Tableau de bord utilisateur |

Il n'existe pas d'URL `/recherche…`.

## Campagnes et e-mails

- Les e-mails portent `mtm_campaign` (ou `utm_campaign`) : on lit les campagnes par leur **nom** (`relance-esi-contactees`, `relance-esi-interessees`, `onboarding-acheteurs-*`, `socialProofTender`, `newsletter-*`…). Source et medium ne remontent pas (plugin MarketingCampaignsReporting absent).
- Referrers de passerelles de messagerie : `*.sendibm*.com` (redirections Brevo), mailinblack, vadesecure.
- `utm_source=chatgpt.com` apparaît comme une campagne : ce n'est pas un e-mail. La catégorie de referrer « AI Assistants » existe depuis février 2026.
- Pour remis / ouvert / cliqué, la source est Brevo, pas Matomo : voir `knowledge/marche/README.md` § E-mails.

## Pièges

- Rafales de robots ponctuelles dans le trafic humain apparent (ex. : semaine du 15 au 21 juin 2026, visites depuis Singapour, ~98 % de rebond) : regarder pays et rebond avant d'interpréter un pic.
- Les inscriptions Matomo (objectif 4) sont le meilleur proxy des **inscriptions humaines** ; le serveur et la base comptent aussi les robots.
