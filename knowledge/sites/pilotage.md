# Pilotage

- URL: https://pilotage.inclusion.gouv.fr
- Matomo site ID: 146
- GitHub: https://github.com/gip-inclusion/pilotage

## Description

Pilotage de l'inclusion is an internal dashboard platform for inclusion professionals. It provides:
- Public statistics on employment inclusion (tableaux de bord publics)
- Organization-specific private dashboards (tableaux de bord prives)
- Data from Metabase embedded iframes
- Newsletter subscription (Infolettre)

This is a low-traffic internal tool used by professionals in the inclusion ecosystem, not a public-facing website.

## Traffic Baselines (2025)

Data retrieved 2026-01-03 via Matomo API.

### Monthly Visitor Stats

| Month   | Unique Visitors | Visits  | Daily Avg Visitors | Daily Avg Visits |
|---------|-----------------|---------|--------------------|-----------------:|
| 2025-01 | 1,177           | 1,529   | 38                 | 49               |
| 2025-02 | 2,218           | 2,800   | 79                 | 100              |
| 2025-03 | 1,010           | 1,363   | 33                 | 44               |
| 2025-04 | -               | -       | -                  | -                |
| 2025-05 | 288             | 346     | 9                  | 11               |
| 2025-06 | 5,731           | 6,460   | 191                | 215              |
| 2025-07 | 1,239           | 1,572   | 40                 | 51               |
| 2025-08 | 710             | 876     | 23                 | 28               |
| 2025-09 | 3,226           | 3,958   | 108                | 132              |
| 2025-10 | 1,462           | 1,905   | 47                 | 61               |
| 2025-11 | 975             | 1,266   | 33                 | 42               |
| 2025-12 | 668             | 894     | 22                 | 29               |

**Note:** April 2025 shows no data (possibly site migration or tracking issue).

**Typical range:** 20-100 unique visitors/day (excluding anomalous months).

**Traffic patterns:**
- Peak: June 2025 (191 visitors/day) and September 2025 (108 visitors/day)
- Low: May 2025 (9 visitors/day), December 2025 (22 visitors/day)
- High variability suggests usage tied to specific campaigns, webinars, or reporting periods

### Engagement Metrics

| Month   | Bounce Rate | Actions/Visit | Avg Time on Site |
|---------|-------------|---------------|------------------|
| 2025-01 | 45%         | 3.0           | 182s             |
| 2025-02 | 59%         | 2.3           | 145s             |
| 2025-03 | 43%         | 3.0           | 193s             |
| 2025-05 | 46%         | 3.1           | 156s             |
| 2025-06 | 43%         | 2.1           | 129s             |
| 2025-07 | 51%         | 2.5           | 113s             |
| 2025-08 | 53%         | 2.5           | 129s             |
| 2025-09 | 38%         | 2.4           | 129s             |
| 2025-10 | 53%         | 2.8           | 134s             |
| 2025-11 | 52%         | 2.7           | 147s             |
| 2025-12 | 43%         | 3.2           | 334s             |

**Typical engagement:** 2-3 actions per visit, 2-3 minutes on site.

## Custom Dimensions

**No custom dimensions configured** for this site.

The site does not track user types or organization information via Matomo custom dimensions.

## Matomo Events

### Implementation

Pilotage uses **Matomo Tag Manager** (container `czDcW7tH`) for event tracking, not inline code.

The Tag Manager container (version 20251208.04) is loaded via:
```html
<script src="{{ MATOMO_BASE_URL }}/js/container_czDcW7tH.js"></script>
```

### Configuration

Features enabled via Tag Manager:
- Link tracking
- Form analytics
- Media analytics
- JS error tracking
- Heartbeat timer

### Event Categories

Only 2 intentional event categories tracked (as of Dec 2025):

#### Bouton (10 events in 2025)

| Action | Name | Description |
|--------|------|-------------|
| Bouton infolettre | `{PagePath}` | Newsletter button click. Name is dynamic, contains the page path where clicked. |

Trigger: Click on element with text "Infolettre"

#### Navigation (configured but not yet fired in data)

| Action | Name | Description |
|--------|------|-------------|
| Clic Tableaux de bord prives | Clic navigation Tableaux de bord prives | Private dashboard navigation click |

Trigger: Click on element with text "Tableaux de bord prives"

#### JavaScript Errors (automatic)

JS errors are automatically captured by Matomo. In Dec 2025:
- `https://tally.so/widgets/embed.js:0` - Script error from Tally form embed
- Occasional inline script errors on `/tableaux-de-bord/zoom-esat/`

### Codebase Events (not yet active)

The codebase contains `data-matomo-*` attributes for future tracking:

```html
<!-- In home_section_accompagne.html -->
<a href="..." data-matomo-category="statistiques" data-matomo-action="click" data-matomo-option="simplifier">
<a href="..." data-matomo-category="statistiques" data-matomo-action="click" data-matomo-option="enrichir">
<a href="..." data-matomo-category="statistiques" data-matomo-action="click" data-matomo-option="objectiver">
<a href="..." data-matomo-category="statistiques" data-matomo-action="click" data-matomo-option="faciliter">
```

These require a JS handler to fire events, which is not currently implemented. Consider adding a listener for `data-matomo-*` attributes.

### Notes

- Very low event volume (~10 intentional events per year)
- Most tracking relies on pageviews, not events
- The site embeds Metabase iframes which have their own analytics
- Tally form popups are used for feedback collection (shown after 45s, max once per 14 days)
- Cookie consent via tarteaucitron.js

## Technical Stack

- Django templates
- Metabase embedded iframes for dashboards
- Tally.so for feedback forms
- Livestorm for webinar integration
- tarteaucitron.js for cookie consent
- iframe-resizer for responsive embeds
