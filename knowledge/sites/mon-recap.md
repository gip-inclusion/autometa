# Mon Recap

- URL: https://mon-recap.inclusion.beta.gouv.fr
- Matomo site ID: 217
- Tag Manager: yes
- GitHub: https://github.com/gip-inclusion/mon-recap-sites-faciles

## Traffic Baselines (2025)

Data retrieved 2026-01-03 via Matomo API.

### Monthly Visitor Stats

| Month   | Unique Visitors | Visits | Daily Avg Visitors | Daily Avg Visits |
|---------|-----------------|--------|--------------------|-----------------:|
| 2025-01 | 493             | 673    | 16                 | 22               |
| 2025-02 | 937             | 1,251  | 33                 | 45               |
| 2025-03 | 1,051           | 1,433  | 34                 | 46               |
| 2025-04 | 1,480           | 1,842  | 49                 | 61               |
| 2025-05 | 1,516           | 2,092  | 49                 | 67               |
| 2025-06 | 1,488           | 1,878  | 50                 | 63               |
| 2025-07 | 1,387           | 1,745  | 45                 | 56               |
| 2025-08 | 1,147           | 1,486  | 37                 | 48               |
| 2025-09 | 1,757           | 2,208  | 59                 | 74               |
| 2025-10 | 2,513           | 3,117  | 81                 | 101              |
| 2025-11 | 4,274           | 5,007  | 142                | 167              |
| 2025-12 | 2,314           | 2,958  | 75                 | 95               |

**Typical range:** 40-150 unique visitors/day, 50-170 visits/day.

**Growth pattern:** Traffic grew significantly throughout 2025, from ~500 unique visitors in January to ~4,300 in November (peak). This reflects a product in active growth phase.

**Seasonal patterns:**
- Peak: November 2025 (highest traffic)
- Low: January (product launch), August (summer holidays)
- Strong growth from September onwards

### Key Metrics (2025 Averages)

| Metric                | Value |
|-----------------------|-------|
| Bounce Rate           | 45%   |
| Pages per Visit       | 2.6   |
| Avg Time on Site      | 2min 15s |

## Custom Dimensions

No custom dimensions configured for this site.

## Conversion Goals

Three goals are configured to track the order funnel:

| ID | Name | Type | Pattern |
|----|------|------|---------|
| 2  | Visiteurs qui vont sur le formulaire | URL contains | formulaire-commande-carnets |
| 3  | Clic commande | External website | tally (form service) |
| 4  | Commandes depuis la page Nos offres | URL contains | formulaire-commande-carnets |

**December 2025 Performance:**
- Total conversions: 970
- Visits converted: 486 (16.4% conversion rate)
- New visitor conversion rate: 12.9%
- Returning visitor conversion rate: 16.1%

## Matomo Events

Events are tracked via Matomo Tag Manager. Minimal custom event tracking implemented.

### Event Categories

| Category | Action | Name | 2025 Events | Description |
|----------|--------|------|-------------|-------------|
| Commande | Bouton de commande | Clic Bouton de commande accomp | 595 | Order button click (accompaniment version) |
| Commande | Bouton de commande | Clic Bouton de commande usagers | 59 | Order button click (users version) |
| Commande | Bouton de commande | Clic Bouton de commande | 3 | Generic order button click |

**Total events in 2025:** 657

### Implementation

- **Tracking method:** Matomo Tag Manager (not custom code)
- **Custom scripts:** Injected via `CustomScriptsSettings` in Django admin (head_scripts/body_scripts fields)
- **No hardcoded Matomo code** in the repository templates

## Site Structure

Based on page analytics, the main site sections are:

### Main Pages (Dec 2025 traffic)

| Page | Visits | Bounce Rate | Description |
|------|--------|-------------|-------------|
| / (homepage) | 1,371 | 37% | Landing page for professionals |
| /formulaire-commande-carnets | 910 | 74% | Order form (Tally embedded) |
| /tarifs-carnet-recap-... | 409 | 75% | Pricing page for groups |
| /ressource | 310 | 41% | Resources section |
| /commander | 309 | 23% | Order information page |
| /confirmations | 248 | 84% | Order confirmation pages |
| /impact-carnet-recap-... | 71 | 74% | Impact page |
| /statistiques | 28 | 79% | Statistics page |

### Traffic Sources

Main marketing campaigns tracked via UTM parameters:
- `mtm_source=insertion_pro&mtm_medium=campagne_email_(marketing)` - 415 visits in Dec 2025
- `utm_id=338` - 97 visits in Dec 2025

## Product Context

Mon Recap is a physical notebook ("carnet") product designed to help social workers and inclusion professionals track their work with beneficiaries. The site is primarily:

1. **Informational** - explaining the product and its impact
2. **Transactional** - processing orders for notebooks via Tally forms

Key user journeys:
1. Homepage -> Pricing -> Order form -> Confirmation
2. Direct link to order form (from email campaigns)
3. Resources/Impact pages for decision makers

The product targets:
- IAE structures (insertion par l'activite economique)
- Conseils departementaux
- Social workers and socio-professional accompaniment staff
