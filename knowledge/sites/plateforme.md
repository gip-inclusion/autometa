# Plateforme de l'inclusion

- URL: https://inclusion.gouv.fr
- Matomo site ID: 212
- Tag Manager: yes (container ID: SAGWfnKo)
- GitHub: https://github.com/gip-inclusion/site-institutionnel-2025

## Traffic Baselines (2025)

Data retrieved 2026-01-06 via Matomo API.

### Monthly Visitor Stats

| Month   | Unique Visitors | Visits    | Daily Avg Visitors | Daily Avg Visits |
|---------|-----------------|-----------|--------------------|-----------------:|
| 2025-01 |          21,052 |    35,104 |                679 |            1,132 |
| 2025-02 |          19,196 |    31,698 |                686 |            1,132 |
| 2025-03 |          19,690 |    32,771 |                635 |            1,057 |
| 2025-04 |          18,662 |    30,932 |                622 |            1,031 |
| 2025-05 |          16,693 |    26,930 |                538 |              869 |
| 2025-06 |          17,420 |    28,636 |                581 |              955 |
| 2025-07 |          16,529 |    27,775 |                533 |              896 |
| 2025-08 |          12,531 |    19,826 |                404 |              640 |
| 2025-09 |          19,482 |    31,833 |                649 |            1,061 |
| 2025-10 |          19,864 |    32,841 |                641 |            1,059 |
| 2025-11 |          12,078 |    17,876 |                403 |              596 |
| 2025-12 |          10,288 |    15,476 |                332 |              499 |

**Typical range:** 332-686 unique visitors/day, 499-1,132 visits/day.

### Engagement Metrics

| Month   | Bounce Rate | Actions/Visit | Avg Time on Site |
|---------|-------------|---------------|------------------|
| 2025-01 |          2% |           5.1 |           2m 14s |
| 2025-02 |          2% |             5 |           2m 05s |
| 2025-03 |          2% |           4.9 |           2m 04s |
| 2025-04 |          2% |           4.9 |           2m 05s |
| 2025-05 |          3% |           4.9 |           2m 06s |
| 2025-06 |          2% |           4.8 |           2m 01s |
| 2025-07 |          3% |           4.7 |           1m 56s |
| 2025-08 |          2% |           4.7 |           1m 47s |
| 2025-09 |          2% |           4.8 |           1m 50s |
| 2025-10 |          2% |           4.7 |           1m 50s |
| 2025-11 |          2% |           4.8 |           1m 37s |
| 2025-12 |          1% |           4.4 |           1m 30s |

## Custom Dimensions

No custom dimensions configured for this site.

## Saved Segments

*Retrieved 2026-01-06 via Matomo API.*

| Name | Definition |
|------|------------|
| ACTION - Clic sur liste des services | `eventName==Clic%2520Liste%2520des%2520Services` |
| ACTION - Formulaire envoyé | `eventAction==Formulaire%2520Envoy%25C3%25A9%2520-%2520Sup...` |
| SORTIE - Les emplois | `exitPageTitle==Emplois%2520de%2520l%27inclusion%2520%25E2...` |
| SOURCE - Linkedin | `referrerName==LinkedIn` |
| VISITS - 2 pages vues minimum | `eventName==Nombre%2520de%2520pages%2520vues;eventValue>=2` |

## Matomo Events

Events are tracked via **Matomo Tag Manager** (not in-code tracking).

### Implementation

- **Container:** SAGWfnKo (live version: 1.3, last updated 2023-07-19)
- **Cookie consent:** Tarteaucitron (DSFR-style cookie banner)
- **Admin configuration:** Custom scripts injected via `CustomScriptsSettings` model in CMS

### Tag Manager Configuration

| Tag Name | Category | Action | Name | Trigger |
|----------|----------|--------|------|---------|
| Pageview | - | - | - | All pageviews |
| Changement d'URL | Page Vues | Compte de pages vues | Nombre de pages vues | URL history change |
| Acces au Formulaire de Contact | Formulaire de Contact | Clic | Clic Bouton Nous Contacter | Click "Nous contacter" |
| Contacts - Page Merci Support | Formulaire de Contact | Formulaire Envoye - Support | Visite Page Merci Support | Visit /merci/ |
| Contacts - Page Merci Partenariat | Formulaire de Contact | Formulaire Envoye - Partenariats | Visite Page Merci Partenariats | Visit /formulaire-envoye-partenariats/ |
| Contacts - Page Merci Autre | Formulaire de Contact | Formulaire Envoye - Autre | Visite Page Merci Autre | Visit /formulaire-envoye/ |
| Acces a l'inscription newsletter | Newsletter | Clic | Clic bouton NL | Click "Infolettre" |
| Acces au Menu Deroulant Services | Liste des Services | Clic | Clic Liste des Services | Click #btn-menu-services |
| Clic bouton | Navigation | Clic sur menu services | Clic sur menu services | Click #menu-services |
| Home - Bouton "Acceder a nos services" | Home | Clic | Clic Bouton Acceder Services | Click "Acceder a nos services numeriques" on homepage |
| Acces a un RS - LinkedIn | Reseau Sociaux | Clic | Clic Bouton LinkedIn | Click "linkedin" |
| Acces a un RS - FaceBook | Reseau Sociaux | Clic | Clic Bouton FaceBook | Click "facebook" |
| Acces a un RS - Twitter | Reseau Sociaux | Clic | Clic Bouton Twitter | Click "twitter" |
| (Instagram trigger exists but no matching tag) | - | - | - | Click "instagram" |

### Event Categories (from Matomo Dec 2025)

| Category | Events | Visits | Description |
|----------|--------|--------|-------------|
| Page Vues | 28,879 | 14,989 | Virtual page views (SPA-style navigation) |
| Formulaire de Contact | 1,443 | 1,239 | Contact form interactions |
| Liste des Services | 22 | 18 | Services dropdown menu clicks |
| Reseau Sociaux | 12 | 7 | Social media link clicks |
| Newsletter | 1 | 1 | Newsletter signup button clicks |

**Data source:** [View in Matomo](https://matomo.inclusion.beta.gouv.fr/index.php?module=CoreHome&action=index&idSite=212&period=month&date=2025-12-01#?idSite=212&period=month&date=2025-12-01&segment=&category=General_Actions&subcategory=Events_Events) | `Events.getCategory?idSite=212&period=month&date=2025-12-01`

### Notes

- **No in-code events:** Unlike les-emplois, this site does not use Django template tags for event tracking. All events are configured in Tag Manager.
- **SPA behavior:** The site tracks URL changes as virtual page views (Page Vues category), indicating single-page app navigation patterns.
- **Contact forms:** Three separate thank-you pages track form completions: Support, Partenariats, Autre.
- **Social links:** LinkedIn, Facebook, Twitter are tracked. Instagram trigger exists but has no associated tag.

## Technical Stack

- **Framework:** Django + Wagtail CMS
- **Design system:** DSFR (Systeme de Design de l'Etat)
- **Python version:** See .python-version in repo
- **Static files:** CSS, JS, artwork in /static/
- **Templates:** Django templates with DSFR components
