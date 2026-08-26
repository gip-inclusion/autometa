# Mon Recap

- URL: https://mon-recap.inclusion.beta.gouv.fr
- Matomo site ID: 217
- Tag Manager: yes
- GitHub: https://github.com/gip-inclusion/mon-recap-sites-faciles
- Funnel bizdev : [glossaire AARRI](../bizdev/glossaire.md) — définitions opérationnelles couche 2 pour ce produit (archétype transactionnel/physique : distribution ≠ déploiement).

## Références de trafic

Les chiffres de trafic de ce site — visites, visiteurs, rebond, durée, répartition par type
d'utilisateur — sont synchronisés chaque nuit dans la base applicative
(`matomo_baselines`) et consultables par le skill `matomo_query`. Ils ne sont pas recopiés
ici : une valeur figée dans un fichier devient fausse sans prévenir.

## Custom Dimensions

No custom dimensions configured for this site.

## Saved Segments

*Retrieved 2026-01-06 via Matomo API.*

| Name | Definition |
|------|------------|
| EVENT - Commande accompagnateur | `eventName==Clic%2520Bouton%2520de%2520commande%2520accomp` |
| EVENT - commande usager | `eventName==Clic%2520Bouton%2520de%2520commande%2520usagers` |
| EXIT - sortie vers le tally | `outlinkUrl=@%252Fr%252FmRMDWl` |
| EXIT - sortie vers le tally usagers | `outlinkUrl=@%252Fr%252FmRMDWl;outlinkUrl=@usagers` |
| SOURCE - QR CODE PAGE ACCOMP | `referrerKeyword==page-accompagnateurs` |

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
