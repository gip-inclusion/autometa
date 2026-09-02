# Plateforme de l'inclusion

- URL : https://inclusion.gouv.fr
- Matomo site ID : 212
- Tag Manager : oui (container ID : SAGWfnKo)
- GitHub : https://github.com/gip-inclusion/site-institutionnel-2025

## Références de trafic

Les chiffres de trafic de ce site — visites, visiteurs, rebond, durée, répartition par type
d'utilisateur — sont synchronisés chaque nuit dans la base applicative
(`matomo_baselines`) et consultables par le skill `matomo_query`. Ils ne sont pas recopiés
ici : une valeur figée dans un fichier devient fausse sans prévenir.

## Custom Dimensions

Aucune custom dimension configurée pour ce site.

## Segments sauvegardés

*Récupérés le 2026-01-06 via l'API Matomo.*

| Nom | Définition |
|-----|------------|
| ACTION - Clic sur liste des services | `eventName==Clic%2520Liste%2520des%2520Services` |
| ACTION - Formulaire envoyé | `eventAction==Formulaire%2520Envoy%25C3%25A9%2520-%2520Sup...` |
| SORTIE - Les emplois | `exitPageTitle==Emplois%2520de%2520l%27inclusion%2520%25E2...` |
| SOURCE - Linkedin | `referrerName==LinkedIn` |
| VISITS - 2 pages vues minimum | `eventName==Nombre%2520de%2520pages%2520vues;eventValue>=2` |

## Events Matomo

Les events sont trackés via **Matomo Tag Manager** (pas de tracking dans le code).

### Implémentation

- **Container :** SAGWfnKo (version live : 1.3, dernière mise à jour : 2023-07-19)
- **Consentement cookies :** Tarteaucitron (bandeau DSFR)
- **Configuration admin :** Scripts custom injectés via le modèle `CustomScriptsSettings` dans le CMS

### Configuration Tag Manager

| Nom du tag | Catégorie | Action | Nom | Trigger |
|------------|-----------|--------|-----|---------|
| Pageview | - | - | - | Tous les pageviews |
| Changement d'URL | Page Vues | Compte de pages vues | Nombre de pages vues | Changement d'URL dans l'historique |
| Acces au Formulaire de Contact | Formulaire de Contact | Clic | Clic Bouton Nous Contacter | Clic sur "Nous contacter" |
| Contacts - Page Merci Support | Formulaire de Contact | Formulaire Envoye - Support | Visite Page Merci Support | Visite de /merci/ |
| Contacts - Page Merci Partenariat | Formulaire de Contact | Formulaire Envoye - Partenariats | Visite Page Merci Partenariats | Visite de /formulaire-envoye-partenariats/ |
| Contacts - Page Merci Autre | Formulaire de Contact | Formulaire Envoye - Autre | Visite Page Merci Autre | Visite de /formulaire-envoye/ |
| Acces a l'inscription newsletter | Newsletter | Clic | Clic bouton NL | Clic sur "Infolettre" |
| Acces au Menu Deroulant Services | Liste des Services | Clic | Clic Liste des Services | Clic sur #btn-menu-services |
| Clic bouton | Navigation | Clic sur menu services | Clic sur menu services | Clic sur #menu-services |
| Home - Bouton "Acceder a nos services" | Home | Clic | Clic Bouton Acceder Services | Clic sur "Acceder a nos services numeriques" en page d'accueil |
| Acces a un RS - LinkedIn | Reseau Sociaux | Clic | Clic Bouton LinkedIn | Clic sur "linkedin" |
| Acces a un RS - FaceBook | Reseau Sociaux | Clic | Clic Bouton FaceBook | Clic sur "facebook" |
| Acces a un RS - Twitter | Reseau Sociaux | Clic | Clic Bouton Twitter | Clic sur "twitter" |
| (Trigger Instagram existe mais sans tag associé) | - | - | - | Clic sur "instagram" |

### Catégories d'events (Matomo déc. 2025)

| Catégorie | Events | Visites | Description |
|-----------|--------|---------|-------------|
| Page Vues | 28 879 | 14 989 | Page views virtuelles (navigation SPA) |
| Formulaire de Contact | 1 443 | 1 239 | Interactions avec le formulaire de contact |
| Liste des Services | 22 | 18 | Clics sur le menu déroulant Services |
| Reseau Sociaux | 12 | 7 | Clics sur les liens réseaux sociaux |
| Newsletter | 1 | 1 | Clics sur le bouton d'inscription newsletter |

**Source des données :** [Voir dans Matomo](https://matomo.inclusion.beta.gouv.fr/index.php?module=CoreHome&action=index&idSite=212&period=month&date=2025-12-01#?idSite=212&period=month&date=2025-12-01&segment=&category=General_Actions&subcategory=Events_Events) | `Events.getCategory?idSite=212&period=month&date=2025-12-01`

### Notes

- **Pas d'events dans le code :** Contrairement à les-emplois, ce site n'utilise pas de template tags Django pour tracker les events. Tous les events sont configurés dans Tag Manager.
- **Comportement SPA :** Le site tracke les changements d'URL comme des page views virtuelles (catégorie Page Vues), indiquant des patterns de navigation single-page app.
- **Formulaires de contact :** Trois pages de remerciement distinctes trackent les soumissions de formulaire : Support, Partenariats, Autre.
- **Liens sociaux :** LinkedIn, Facebook, Twitter sont trackés. Un trigger Instagram existe mais n'a pas de tag associé.

## Stack technique

- **Framework :** Django + Wagtail CMS
- **Design system :** DSFR (Système de Design de l'État)
- **Version Python :** Voir .python-version dans le repo
- **Fichiers statiques :** CSS, JS, artwork dans /static/
- **Templates :** Templates Django avec composants DSFR

## Saved Segments

*Retrieved 2026-03-29 via Matomo API.*

| Name | Definition |
|------|------------|
| ACTION - Clic sur liste des services | `eventName==Clic%2520Liste%2520des%2520Services` |
| ACTION - Formulaire envoyé | `eventAction==Formulaire%2520Envoy%25C3%25A9%2520-%2520Sup...` |
| SORTIE - Les emplois | `exitPageTitle==Emplois%2520de%2520l%27inclusion%2520%25E2...` |
| SOURCE - Linkedin | `referrerName==LinkedIn` |
| VISITS - 2 pages vues minimum | `eventName==Nombre%2520de%2520pages%2520vues;eventValue>=2` |

## Event Names

*Data from 2026-02, retrieved 2026-03-29 via Matomo API.*

**3 distinct events tracked.**

| Name | Events | Visits |
|------|--------|--------|
| Nombre de pages vues | 32,859 | 16,316 |
| Clic Bouton Nous Contacter | 1,622 | 1,407 |
| Clic Bouton LinkedIn | 11 | 11 |
