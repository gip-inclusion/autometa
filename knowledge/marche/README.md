---
source: [autometa_tables_db, metabase:stats, datadog_logs]
verifie_le: 2026-11-09
---
# Le Marché de l'inclusion — base, e-mails et logs

Fiche compagne de `knowledge/sites/marche.md` (Matomo). Elle couvre ce que Matomo ne voit pas : les besoins d'achat, leur diffusion aux structures, les réponses, les e-mails et le spam.

## Qu'est-ce que le Marché ?

Une place de marché entre **acheteurs** (grands groupes, établissements publics, collectivités, PME) et **fournisseurs inclusifs** (SIAE, ESAT, EA…). Deux usages principaux :

1. **L'annuaire** : un acheteur cherche un prestataire inclusif, consulte sa fiche, le contacte.
2. **Le dépôt de besoin** : un acheteur décrit un achat, l'équipe le valide, le Marché le diffuse par e-mail aux structures pertinentes, qui se déclarent intéressées ou non.

Types de comptes (`users_user.kind`) : `BUYER`, `SIAE`, `PARTNER` (facilitateurs, réseaux, partenaires API), `INDIVIDUAL`, `ADMIN`.

## Route de requête

| Ordre | Source | Usage |
|---|---|---|
| 1 | `autometa_tables_db`, schéma `raw_marche` | Copie brute de la base applicative, synchronisée chaque nuit (~160 tables). **Schéma brut : suivre le skill `autometa_tables_db`, qui exige l'accord de l'utilisateur.** Il n'existe pas de table Marché nettoyée dans `reporting` ou `public` |
| — | `intermediate.int_marche__*`, `staging.stg_marche__*` | Existent (dont `int_marche__actes_metier` et `int_marche__tous_les_pros`) mais hors périmètre du skill |
| 2 | Metabase, instance `stats`, base 6 | Mêmes tables ; dernier repli, déjà utilisé par les TDB d'actes métiers |
| — | Brevo (API) | Seule source des e-mails remis / ouverts / cliqués / rebonds. Aucun accès permanent configuré dans Autometa à ce jour |
| — | Datadog, service `le-marche-prod` | Requêtes HTTP (URL complète, vue Django, code, IP, pays, `@usr.id`) et logs des tâches. **30 jours de rétention** |

## Tables principales (`raw_marche`)

| Table | Contenu |
|---|---|
| `tenders_tender` | Besoins d'achat |
| `tenders_tendersiae` | Une ligne par couple besoin × structure ciblée : l'entonnoir de diffusion |
| `tenders_tender_perimeters`, `perimeters_perimeter` | Périmètres ciblés par chaque besoin ; lieux (`kind` : `CITY`, `DEPARTMENT`, `REGION` ; `insee_code`, `department_code`, `region_code`) |
| `tenders_tenderquestion`, `tenders_questionanswer` | Questions de l'acheteur, réponses des structures |
| `tenders_tenderstepsdata` | Parcours du formulaire en étapes **abandonnés** (la ligne est supprimée quand le dépôt aboutit ; aucun lien vers `tenders_tender`) |
| `tenders_partnersharetender` | Partenaires destinataires des besoins |
| `conversations_conversation` | Contacts envoyés à une structure depuis sa fiche, avec validation par l'équipe |
| `conversations_templatetransactional`, `conversations_templatetransactionalsendlog` | Modèles d'e-mails et journal des envois |
| `users_user`, `account_emailaddress` | Comptes, vérification de l'e-mail |
| `siaes_siae`, `siaes_siaeuser`, `siaes_siaeuserrequest`, `siaes_siaeoffer` | Structures, rattachements, prestations |
| `companies_company` | Entreprises acheteuses (regroupe les comptes par organisation) |
| `favorites_favoritelist`, `favorites_favoriteitem`, `notes_note`, `purchases_purchase` | Favoris, notes de l'équipe, achats importés |
| `django_admin_log` | Actions de l'équipe dans l'admin (modération, suppressions) |

## Cycle de vie d'un besoin (`tenders_tender`)

- **Types** (`kind`) : `TENDER` (appel d'offres), `QUOTE` (demande de devis), `PROJ` (sourcing inversé).
- **Origines** (`source`) : `FORM` (site), `TALLY`, `API` (partenaire), `STAFF_C4_CREATED` (créé par l'équipe).
- **Statuts** : `DRAFT` → `SUBMITTED` → `VALIDATED` → `SENT`, ou `REJECTED`. La validation est **humaine** (admin). Une demande de modification sans réponse sous 10 jours entraîne un rejet automatique.
- **Diffusion** : par lots, en semaine en journée, quelques minutes après la validation.
- **Dates** : `published_at` et `validated_at` sont **écrasés** à chaque nouvelle soumission ou validation. L'historique fiable des transitions est le champ JSON `logs` (actions `validate`, `send`, `reject`, demandes de modification, relances).
- **Compteurs** `siae_*_count` : recalculés seulement jusqu'à un mois après l'échéance, puis figés. Recompter depuis `tenders_tendersiae`.

## Ciblage géographique d'un besoin

Le Marché choisit les structures destinataires selon le premier cas qui s'applique :

| Cas | Champs de `tenders_tender` | Structures ciblées | Besoins diffusés en 2026 |
|---|---|---|---|
| 1. France entière | `is_country_area` | Seulement celles dont la zone d'intervention est la France entière | 12 |
| 2. Rayon | `location_id` est une ville et `distance_location` > 0 (en km) | Celles dont l'adresse est dans le rayon ; **les périmètres sont ignorés** | 20 (rayon médian : 60 km) |
| 3. Périmètres | au moins une ligne dans `tenders_tender_perimeters` | Celles dont la zone d'intervention couvre un des périmètres (ou son département, sa région), ou dont l'adresse s'y trouve ; sans les structures « France entière » | 242 |
| 4. Aucun ciblage | rien de ce qui précède | **Aucun filtre géographique** : tout le pays | 46 |

`include_country_area` ajoute les structures « France entière » aux cas 2 et 3 ; seul, il ne cible qu'elles (5 besoins en 2026).

Volumes : besoins `SENT` hors API créés en 2026, base du Marché au 11/11/2026.

- **Un besoin sans périmètre n'est pas « national »** : il peut viser un rayon autour d'une ville (cas 2) ou n'avoir aucun filtre (cas 4, structures de 61 départements en médiane). « France entière » (cas 1) est plus étroit que l'absence de filtre.
- **Le lieu d'intervention (`location_id`) ne sert au ciblage qu'avec une distance.** Au dépôt, il est recopié dans les périmètres ; l'équipe peut ensuite modifier l'un sans l'autre.
- **Un rayon déborde** sur les départements voisins : un besoin ciblé dans un rayon autour d'une ville n'est pas réservé au département de cette ville.
- **La géographie d'un besoin n'est pas celle des structures touchées** : un besoin ciblé par périmètres atteint des structures de 7 départements en médiane, dont la zone d'intervention couvre le périmètre. Pour savoir où un besoin a réellement été diffusé, passer par `tenders_tendersiae` → `siaes_siae`.

## Localisation des acheteurs

Les comptes acheteurs n'ont **aucune localisation** : ni adresse, ni code postal, ni département dans `users_user` ou `companies_company`, et le SIRET des entreprises n'est jamais renseigné (0 sur 1 493 au 11/11/2026). Seule approximation en base : le lieu des besoins que l'acheteur a déposés, connu pour 506 des 8 460 comptes acheteurs actifs. Une liste d'acheteurs par territoire ne peut donc pas sortir de la base : le dire, et proposer le nom de l'organisation (`companies_company.name`, `users_user.company_name`) comme indice à vérifier hors base.

## Entonnoir côté structures (`tenders_tendersiae`)

Chaque date n'est posée qu'au premier événement.

| Champ | Sens | Fiabilité |
|---|---|---|
| `email_send_date` | E-mail de présentation envoyé | Posée avant l'envoi Brevo, même si l'utilisateur est désabonné |
| `email_link_click_date` | Clic sur le lien de l'e-mail | **Gonflé** : le lien « pas intéressé » le déclenche, et les antivirus de messagerie probablement aussi (~1 couple sur 6 ne fait que cliquer) |
| `detail_display_date` | Besoin consulté par une structure **connectée** | Bonne, mais rate les non-connectés |
| `detail_contact_click_date` | « Intéressé » : coordonnées transmises à l'acheteur | **Acte clé.** Possible sans connexion, donc peut dépasser les consultations |
| `detail_not_interested_click_date` + `_feedback` | « Pas intéressé » + motif libre | Bonne |
| `detail_groupement_click_date` | Réponse en groupement | Depuis mai 2026 |
| `found_with_ai`, `source` | Structure trouvée par l'IA ; origine de la ligne (`EMAIL`, `DASHBOARD`, `LINK`, `AI`) | Plus d'usage de l'IA depuis février 2024 |

## Exclusions obligatoires

- **Besoins de source `API`** : en 2026, l'essentiel des lignes de `tenders_tender` (ordre de grandeur : ~9 besoins créés sur 10) vient d'un seul compte partenaire, APProch. Ces projets d'achat importés restent `SUBMITTED` et ne sont jamais diffusés. **Les exclure de tout comptage de dépôts.**
- **Comptes spam** : voir § Spam.
- **Comptes de l'équipe** (`kind='ADMIN'`, `is_staff`) pour les indicateurs d'usage.
- **Imports en masse** : créations groupées de comptes (ex. : acheteurs SNCF en décembre 2025) ou d'achats (`purchases_purchase`, import de février 2026) — à isoler avant de lire une tendance.

## Purges et rétention

Le Marché efface lui-même des données chaque nuit :

- besoins publiés dont l'auteur est inactif depuis 12 mois, **avec** leurs lignes `tendersiae`, leurs réponses et leurs journaux d'envoi ;
- brouillons non modifiés depuis 12 mois ;
- conversations anonymisées après 6 mois (les lignes restent) ;
- historique des fiches structure : 180 jours ;
- depuis le 7/11/2026, comptes SIAE spam (voir ci-dessous).

**Conséquence : un comptage historique ne voit que les survivants.** Les mois anciens sont sous-estimés ; pour une série longue, il faut des instantanés réguliers.

## E-mails

- **Fournisseur** : Brevo. Expéditeurs : `ne-pas-repondre@`, `commercial@`, `lemarche@` sur `lemarche.inclusion.beta.gouv.fr`.
- **Envoyés** : `conversations_templatetransactionalsendlog`, une ligne par envoi et par destinataire, rattachée au modèle (`templatetransactional.code`) et à l'objet (souvent le couple besoin × structure). La ligne est écrite **avant** l'appel à Brevo ; ni la réponse de Brevo ni l'identifiant du message ne sont conservés. Les e-mails d'inscription et de confirmation d'adresse n'y figurent pas.
- **Remis, ouverts, cliqués, rebonds, bloqués** : **uniquement dans Brevo**. Le Marché ne reçoit aucun retour d'événement de Brevo (le seul webhook traite les réponses entrantes, rattachées aux conversations).
- **Le compte Brevo est partagé** avec la PDI (webinaires) et Les Traiteurs Engagés : filtrer par expéditeur ou par modèle.
- **Ouvertures** : exclure l'événement `loadedByProxy` (pré-chargement d'Apple Mail).
- **Brevo bloque d'office** les adresses désinscrites ou en échec définitif ; le Marché continue de leur écrire, ce qui gonfle les envois côté base.
- **Rétention Brevo** : détail des événements disponible au moins depuis février 2026 au 9/11/2026 ; agrégats limités à 90 jours par appel, rapports quotidiens à 30 jours.

## Spam

**Signature** : des robots créent des comptes `SIAE` en masse. Ils n'exécutent pas le JavaScript (Matomo ne les voit pas) mais déclenchent l'e-mail « Confirmez votre adresse e-mail » vers de vraies adresses de tiers (gmail, icloud…, souvent suffixées `+xx`), ainsi qu'une notification interne par inscription.

| Indice | Où |
|---|---|
| POST d'inscription en rafale, mêmes IP ou opérateurs (Russie, Canada) | Datadog, vue `auth:account_signup` |
| Volume d'e-mails de confirmation (1 000 à 3 000 par mois de février à octobre 2026) sans rapport avec l'objectif Matomo « Inscription » (~150 par mois) | Brevo vs Matomo |
| Noms contenant « blogspot », ou prénom = nom = entreprise suivi de deux majuscules ; nom d'entreprise rempli sans rattachement à une structure ; e-mail non vérifié | `users_user` |

- La règle historique « prénom de plus de 15 caractères contenant "nz" » (`int_marche__tous_les_pros`) ne détecte plus les vagues récentes.
- **Correctifs** : depuis le 7/11/2026, une tâche quotidienne supprime **physiquement** les comptes SIAE de plus de 7 jours, non vérifiés et sans activité (15 378 supprimés à la première exécution, le 8/11) ; depuis le 8/11, la vérification de l'e-mail est obligatoire pour se connecter. Les robots continuent pourtant à créer des comptes.
- **Rupture de série** : tout comptage de comptes créés avant le 8/11/2026 change rétroactivement.
- Besoins : `status='REJECTED'` mêle spam et rejets sur le fond ; aucun spam robot constaté sur le dépôt de besoin.
- Contacts depuis une fiche : la plupart ne sont jamais validés, mais il s'agit surtout de demandeurs d'emploi qui écrivent aux structures, pas de robots.
- Aucun captcha ni limitation de débit sur l'inscription et le dépôt de besoin à cette date.

## Datadog (`le-marche-prod`)

- Facettes utiles : `@http.url_details.view_name`, `@http.method`, `@http.status_code`, `@network.client.ip` et sa géolocalisation, `@usr.id` (rapprochable de `users_user.id`), `commitId`.
- Compter les requêtes sur `@logger.name:django_datadog_logger.middleware.request_log` : sinon une même requête est comptée plusieurs fois (logs applicatifs associés, ex. appels Brevo).
- Les logs contiennent des adresses e-mail en clair : ne pas les recopier sans besoin.
- 30 jours de rétention : tout indicateur Datadog doit être capté au fil de l'eau.

## Actes métiers

L'acte « Diffusion d'offre inclusive » de `knowledge/stats/actes-metier.md` compte les besoins `SUBMITTED` ou `SENT`, besoins API compris ; sa North Star (besoin reçu par au moins une structure) les écarte de fait.
