# Dora

- URL: https://dora.inclusion.beta.gouv.fr
- Matomo site ID: 211
- Tag Manager: yes (container ID: `1y35glgB`)
- GitHub: https://github.com/gip-inclusion/dora

## Related Knowledge

Dora has two knowledge files:

| File | Content |
|------|---------|
| **This file** (`knowledge/sites/dora.md`) | Matomo web analytics: traffic baselines, events, funnels, segments |
| `knowledge/dora/README.md` | Metabase database: structures, services, orientations, search data, SQL queries |

**Use this file** for: visitor counts, bounce rates, event tracking, user journeys, Matomo segments.

**Use `knowledge/dora/`** for: querying the database, understanding the domain model (Structure → Service → Orientation), search analytics by organization, content freshness metrics.

## Backend de recherche

La recherche de services Dora (`/recherche?...`) utilise l'API data·inclusion (`/search/services`) comme backend. Les résultats viennent du datawarehouse data·inclusion (tables `public_marts`). Si un service saisi dans Dora ne remonte pas dans la recherche, utiliser la skill `data_inclusion` pour investiguer le pipeline (staging → intermediate → marts).

## Traffic Baselines (2025)

Data retrieved 2026-03-29 via Matomo API.

### Monthly Visitor Stats

| Month   | Unique Visitors | Visits    | Daily Avg Visitors | Daily Avg Visits |
|---------|-----------------|-----------|--------------------|-----------------:|
| 2025-01 |          49,670 |    64,116 |              1,602 |            2,068 |
| 2025-02 |          45,831 |    59,731 |              1,637 |            2,133 |
| 2025-03 |          47,908 |    62,420 |              1,545 |            2,014 |
| 2025-04 |          44,072 |    57,145 |              1,469 |            1,905 |
| 2025-05 |          40,444 |    52,260 |              1,305 |            1,686 |
| 2025-06 |          43,818 |    56,985 |              1,461 |            1,900 |
| 2025-07 |          44,098 |    57,855 |              1,423 |            1,866 |
| 2025-08 |          35,553 |    45,990 |              1,147 |            1,484 |
| 2025-09 |          49,803 |    64,609 |              1,660 |            2,154 |
| 2025-10 |          53,612 |    71,551 |              1,729 |            2,308 |
| 2025-11 |          52,793 |    68,265 |              1,760 |            2,276 |
| 2025-12 |          49,673 |    64,412 |              1,602 |            2,078 |

**Typical range:** 1,147-1,760 unique visitors/day, 1,484-2,308 visits/day.

### Engagement Metrics

| Month   | Bounce Rate | Actions/Visit | Avg Time on Site |
|---------|-------------|---------------|------------------|
| 2025-01 |         25% |           4.6 |           4m 32s |
| 2025-02 |         24% |           4.8 |           4m 32s |
| 2025-03 |         24% |             5 |           4m 27s |
| 2025-04 |         24% |           5.6 |           4m 45s |
| 2025-05 |         22% |           5.3 |           4m 18s |
| 2025-06 |         22% |           5.6 |           4m 33s |
| 2025-07 |         22% |           5.5 |           4m 32s |
| 2025-08 |         22% |           5.1 |           4m 25s |
| 2025-09 |         21% |           5.3 |           4m 20s |
| 2025-10 |         22% |           5.1 |           4m 33s |
| 2025-11 |         21% |           4.8 |           4m 09s |
| 2025-12 |         21% |           4.9 |           4m 11s |

## Custom Dimensions

No custom dimensions configured for this site.

## Saved Segments

*Retrieved 2026-01-06 via Matomo API.*

| Name | Definition |
|------|------------|
| ACQUISITION - jour de l'événement | `visitorFirstVisitTime>2024-02-01%252000%253A00%253A01;vis...` |
| CONTENT - HP | `pageUrl==https%253A%252F%252Fdora.inclusion.beta.gouv.fr%...` |
| CONTENT - Page Services | `pageUrl=@https%253A%252F%252Fdora.inclusion.beta.gouv.fr%...` |
| CONTENT - Visite page recherche | `eventName==Visite%2520de%2520la%2520page%2520recherche` |
| CONTENT - Visite page recherche EXL page service seule | `eventAction==Visite%2520de%2520la%2520page%2520recherche;...` |
| CONTENT - Visite page recherche sans page service | `eventName==Visite%2520de%2520la%2520page%2520recherche;pa...` |
| EVENT - Retour IC | `eventName==Retour%2520inclusion%2520Connect%2509` |
| EVENTS - Clic sur infos de contact | `eventName==Page%2520Services%2520-%2520Clic%2520infos%252...` |
| FILE ACTIVE - clic sur mes aides | `eventCategory==XP;eventAction=@aides` |
| GOAL - Envoi d'une demande d'orientation | `eventName==Page%2520vue%2520orienter%252Fmerci` |
| PROFILE - Connecté | `eventName==Utilisateur%2520connect%25C3%25A9` |
| PROFILE - Intention d'orientation | `eventAction==Fiche%2520structure%2520-%2520Afficher%2520l...` |
| PROFILE ENGAGE - test 1 : clic bouton orienter | `eventAction==Clic%2520bouton%2520orienter%2520votre%2520b...` |
| PROFILE ENGAGE - test 2 : clic voir sur la carte | `eventAction==Clic%2520Voir%2520sur%2520la%2520carte%2520-...` |
| PROFILE ENGAGE - test 3 : clic etape suivante | `eventAction==Clic%2520bouton%2520Etape%2520Suivante` |
| Page View - Retour IC | `pageUrl=@ic-callback` |
| RECH TXT - Clic sur la home | `eventName==HP%2520-%2520Clic%2520bouton%2520recherche%252...` |
| RECH TXT - Clic sur un resultat | `eventName==Recherche%2520textuelle%2520-%2520Clic%2520sur...` |
| RECH TXT - Vue page résultat | `eventName==Recherche%2520textuelle%2520-%2520Vue%2520d%27...` |
| RECH TXT - clic dans un champs de recherche | `eventName==Recherche%2520textuelle%2520-%2520Clic%2520cha...` |
| RECH TXT - visites avec un clic | `visitEndServerDate=@2025-04;eventName==Recherche%2520text...` |
| RETENTION - dernière visite 30j | `daysSinceLastVisit>=1;daysSinceLastVisit<30` |
| RETENTION - dernière visite 30j - avec IO | `daysSinceLastVisit>=1;eventAction==Fiche%2520structure%25...` |
| RETENTION - dernière visite 30j - connectés | `daysSinceLastVisit>=1;eventAction==Utilisateur%2520connec...` |
| SOURCE - Les emplois - liens | `referrerKeyword==cardservicefichedeposte,referrerKeyword=...` |
| SOURCE - les emplois - anciens liens | `referrerKeyword==dashboard,referrerKeyword==dashboard%252F` |
| VISIT - Bénéficiaire clic sur voir structures | `referrerKeyword==voir_structures` |
| VISIT - Vue de la recherche textuelle | `pageUrl=@recherche-textuelle` |
| VISITS - première visite | `visitCount==1` |

## Matomo Events

Events are tracked via Matomo Tag Manager, not via code-based tracking.
Data from December 2025.

### Implementation

- **Tracking method:** Matomo Tag Manager (MTM)
- **Container:** `1y35glgB` (Dora Prod)
- **Frontend stack:** SvelteKit
- **Code events:** Only `orienter/merci` event is pushed directly via `_mtm.push({ event: "orienter/merci" })` on successful orientation completion

### Event Categories

#### Page Service (32,994 visits, 41,740 events)
Service page viewing and interactions.

| Action | Description | Events |
|--------|-------------|--------|
| Vue page services hors page orienter | Service page viewed (not orientation flow) | 41,740 |
| Clic bouton Orienter | Clicks on "Orienter" button | 4,613 |
| Clic Bouton Partager cette Fiche | Share service button clicks | 1,282 |
| Clic Bouton Envoyer la Fiche | Send service card button clicks | 604 |
| Clic sur afficher les contacts | Show contacts clicks | 431 |
| Clic Bouton Profil Professionnel | Professional profile button clicks | 197 |

#### Page Recherche (10,591 visits)
Search page interactions.

| Action | Description | Events |
|--------|-------------|--------|
| Ajout d'un filtre | Filter added to search | 11,675 |
| Clic sur un des champs | Search field clicked | 28,472 |
| Clic Bouton Actualiser la recherche | Refresh search button clicks | 1,529 |

#### Page Recherche - Visite (10,299 visits)
Search page visits.

| Action | Description | Events |
|--------|-------------|--------|
| Visite de la page recherche | Search page visit | 71,038 |

#### Home Page (9,215 visits)
Homepage interactions.

| Action | Description | Events |
|--------|-------------|--------|
| Clic Bouton Recherche | Search button clicks | 12,456 |
| Clic Bouton | Generic button clicks | 14 |

#### Home (2,426 visits)
Alternative homepage tracking.

| Action | Description | Events |
|--------|-------------|--------|
| Clic Recherche par mots cles | Keyword search clicks | 3,120 |

#### Fiche structures (2,606 visits)
Structure/organization page interactions.

| Action | Description | Events |
|--------|-------------|--------|
| Fiche structure - Afficher les contacts | Show structure contacts | 3,082 |

#### Utilisateur connecte (1,874 visits)
Logged-in user tracking.

| Action | Description | Events |
|--------|-------------|--------|
| Utilisateur connecte | User logged in | 1,877 |

#### Recherche textuelle (1,627 visits)
Text-based search funnel (added Feb 2025).

| Action | Description | Events |
|--------|-------------|--------|
| Clic champs de recherche | Search field clicks | 3,236 |
| Vue d'une page de resultats | Results page viewed | 2,025 |
| Vue d'une page service | Service page viewed (from search) | 1,704 |
| Lancer une recherche | Search executed | 1,439 |
| Clic sur un resultat | Result clicked | 1,186 |
| Clic sur une tab dans les resultats | Tab clicked in results | 483 |

#### Page Rattachement (950 visits)
Structure membership/joining.

| Action | Description | Events |
|--------|-------------|--------|
| Clic Bouton Rejoindre la structure | Join structure button clicks | 1,037 |

#### Orienter (969 visits)
Orientation wizard flow.

| Action | Description | Events |
|--------|-------------|--------|
| Clic bouton Etape Suivante | Next step button clicks | 1,487 |

#### Orientation (669 visits)
Orientation submission.

| Action | Description | Events |
|--------|-------------|--------|
| Bouton Envoyer | Send button clicks | 1,454 |

#### Page Invitation (335 visits)
Invitation page interactions.

| Action | Description | Events |
|--------|-------------|--------|
| Clic Bouton Adherer a la structure | Join structure invitation clicks | 406 |

#### Page de resultats (264 visits)
Results page actions.

| Action | Description | Events |
|--------|-------------|--------|
| Clic Bouton Creer une Alerte | Create alert button clicks | 284 |
| Clic Voir sur la carte - Page de resultat | View on map clicks | 354 |

#### JavaScript Errors (259 visits)
Error tracking (technical/debug).

| Action | Description | Events |
|--------|-------------|--------|
| :0 | Generic JS errors | 324 |
| Various JS file errors | Specific file/line errors | various |

#### XP (4 visits)
Experimental tracking.

| Action | Description | Events |
|--------|-------------|--------|
| Clic Bloc Mes Aides Page de Resultat | "Mes Aides" block clicks | 4 |

### Dynamic Event Categories

The following categories are generated dynamically based on service URLs:

#### `https://dora.../services/.../orienter/merci`
Orientation completion events. Each successful orientation generates a category based on the service URL with action `Page vue orienter/merci`.

**December 2025 top services by orientations:**
- La Cravate Solidaire - Atelier coup de pouce: 17 events
- Regie de territoire - Cite mobile: 16 events
- Reussir Provence PLI PLIE: 17 events
- Departement de la Drome - Adie: 14 events

### Key Funnels

#### Search Funnel
1. Homepage Search button click (12,456)
2. Search page visit (71,038)
3. Filter/field interaction (28,472 field clicks + 11,675 filter adds)
4. Results page view (2,025)
5. Result click (1,186)
6. Service page view (41,740)

#### Orientation Funnel
1. Service page view (41,740)
2. Orienter button click (4,613)
3. Next step clicks (1,487)
4. Send button click (1,454)
5. Orientation success (~778 "Page vue orienter/merci" events)

**Conversion rate:** ~17% from orienter click to completion (4,613 to 778)

### Notes

- Events use French labels throughout
- Tag Manager container is actively maintained (rev 152 as of Dec 2025)
- "Recherche textuelle" funnel added Feb 2025 for text search analysis
- JS Error tracking captures frontend errors (noisy, mostly third-party related)
- Many service-specific categories from dynamic URL-based orientation tracking

## Event Names

*Data from 2026-02, retrieved 2026-03-29 via Matomo API.*

**200 distinct events tracked.**

| Name | Events | Visits |
|------|--------|--------|
| Visite de la page recherche | 78,492 | 11,463 |
| Vue page services hors page orienter | 60,837 | 47,886 |
| Recherche classique - Clic sur un des champs de recherche | 35,357 | 12,045 |
| HP - Lancer Recherche | 13,714 | 10,185 |
| Page Service - Clic bouton Orienter | 6,579 | 4,417 |
| Recherche textuelle - Clic champs de recherche | 4,849 | 2,287 |
| Fiche structure - Afficher les contacts | 4,402 | 3,668 |
| Clic Recherche par mots clés | 3,840 | 2,963 |
| Recherche textuelle - Vue d'une page de résultats | 3,087 | 2,251 |
| Recherche textuelle - Vue d'une page service | 2,951 | 1,582 |
| Orienter - Etape Suivante | 1,896 | 1,237 |
| Recherche textuelle - Clic sur un résultat | 1,883 | 1,096 |
| Clic Bouton Envoyer l'Orientation | 1,677 | 811 |
| Event Name not defined | 1,491 | 1,296 |
| Rattachement - Rejoindre la Structure | 1,334 | 1,267 |
| Page vue orienter/merci | 875 | 811 |
| Page service - Clic sur afficher les contacts | 854 | 520 |
| Orientations envoyées | 827 | 626 |
| Recherche - Actualiser la Recherche | 587 | 393 |
| Orientations reçues | 586 | 404 |
| Recherche textuelle - Lancer une recherche | 542 | 360 |
| Clic Voir sur la carte - Page de résultat | 454 | 351 |
| Recherche textuelle - Clic sur Structures | 366 | 272 |
| Recherche textuelle - Clic sur Services | 341 | 252 |
|  (75)&l=Paris (75)&locs=en-presentiel | 313 | 292 |
| Script error. | 308 | 242 |
| Recherche - Créer une Alerte | 307 | 281 |
|  (31)&l=Toulouse (31)&locs=en-presentiel | 204 | 186 |
| ResizeObserver loop completed with undelivered notifications. | 201 | 181 |
|  (80)&l=Amiens (80)&locs=en-presentiel | 189 | 168 |
|  (13)&l=Marseille (13)&locs=en-presentiel | 185 | 175 |
|  (59)&l=Lille (59)&locs=en-presentiel | 171 | 157 |
| Invitation - Adhérer à la Structure | 163 | 146 |
|  (26)&l=Valence (26)&locs=en-presentiel | 159 | 141 |
| Utilisateur connecté | 155 | 155 |
|  (34)&l=Montpellier (34)&locs=en-presentiel | 137 | 130 |
|  (35)&l=Rennes (35)&locs=en-presentiel | 126 | 118 |
|  (69)&l=Lyon (69)&locs=en-presentiel | 117 | 112 |
|  (30)&l=Nîmes (30)&locs=en-presentiel | 114 | 104 |
|  (44)&l=Nantes (44)&locs=en-presentiel | 113 | 103 |
|  (68)&l=Mulhouse (68)&locs=en-presentiel | 90 | 83 |
|  (974)&l=Saint-Denis (974)&locs=en-presentiel | 89 | 85 |
|  (67)&l=Strasbourg (67)&locs=en-presentiel | 81 | 75 |
|  (34)&l=Béziers (34)&locs=en-presentiel | 73 | 63 |
|  (42)&l=Saint-Étienne (42)&locs=en-presentiel | 73 | 62 |
|  (65)&l=Tarbes (65)&locs=en-presentiel | 69 | 57 |
|  (63)&l=Clermont-Ferrand (63)&locs=en-presentiel | 66 | 60 |
|  (86)&l=Poitiers (86)&locs=en-presentiel | 65 | 61 |
|  (26)&l=Romans-sur-Isère (26)&locs=en-presentiel | 65 | 59 |
|  (58)&l=Nevers (58)&locs=en-presentiel | 63 | 51 |

*... and 150 more events.*
