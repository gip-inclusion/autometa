# Dora

- URL: https://dora.inclusion.beta.gouv.fr
- Matomo site ID: 211
- Tag Manager: yes (container ID: `1y35glgB`)
- GitHub: https://github.com/gip-inclusion/dora

## Traffic Baselines (2025)

Data retrieved 2026-01-03 via Matomo API.

### Monthly Visitor Stats

| Month   | Unique Visitors | Visits  | Daily Avg Visitors | Daily Avg Visits |
|---------|-----------------|---------|--------------------|-----------------:|
| 2025-01 | 49,670          | 64,116  | 1,602              | 2,068            |
| 2025-02 | 45,831          | 59,731  | 1,637              | 2,133            |
| 2025-03 | 47,908          | 62,420  | 1,546              | 2,014            |
| 2025-04 | 44,072          | 57,145  | 1,469              | 1,905            |
| 2025-05 | 40,444          | 52,260  | 1,305              | 1,686            |
| 2025-06 | 43,818          | 56,985  | 1,461              | 1,900            |
| 2025-07 | 44,098          | 57,855  | 1,423              | 1,866            |
| 2025-08 | 35,553          | 45,990  | 1,147              | 1,484            |
| 2025-09 | 49,803          | 64,609  | 1,660              | 2,154            |
| 2025-10 | 53,612          | 71,551  | 1,730              | 2,308            |
| 2025-11 | 52,793          | 68,265  | 1,760              | 2,276            |
| 2025-12 | 48,594          | 62,987  | 1,568              | 2,032            |

**Typical range:** 1,300-1,800 unique visitors/day, 1,500-2,300 visits/day.

**Seasonal patterns:**
- Peak: October-November (autumn activity)
- Low: August (summer holidays), May (bridge holidays)

### Engagement Metrics

| Month   | Bounce Rate | Actions/Visit | Avg Time (sec) |
|---------|-------------|---------------|----------------|
| 2025-01 | 25%         | 4.6           | 272            |
| 2025-02 | 24%         | 4.8           | 272            |
| 2025-03 | 24%         | 5.0           | 267            |
| 2025-04 | 24%         | 5.6           | 285            |
| 2025-05 | 22%         | 5.3           | 258            |
| 2025-06 | 22%         | 5.6           | 273            |
| 2025-07 | 22%         | 5.5           | 272            |
| 2025-08 | 22%         | 5.1           | 265            |
| 2025-09 | 21%         | 5.3           | 260            |
| 2025-10 | 22%         | 5.1           | 273            |
| 2025-11 | 21%         | 4.8           | 249            |
| 2025-12 | 21%         | 4.9           | 252            |

**Baseline engagement:** Bounce rate ~22%, 5 actions/visit, 4.5 min average session.

## Custom Dimensions

No custom dimensions configured for this site.

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
