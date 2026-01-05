# Communaute

- URL: https://communaute.inclusion.gouv.fr
- Matomo site ID: 206
- GitHub: https://github.com/gip-inclusion/la-communaute

## Traffic Baselines (2025)

Data retrieved 2026-01-03 via Matomo API.

### Monthly Visitor Stats

| Month   | Unique Visitors | Visits  | Daily Avg Visitors | Daily Avg Visits |
|---------|-----------------|---------|--------------------|-----------------:|
| 2025-01 | 30,643          | 41,836  | 988                | 1,350            |
| 2025-02 | 25,553          | 34,110  | 913                | 1,218            |
| 2025-03 | 27,469          | 36,687  | 886                | 1,183            |
| 2025-04 | 27,557          | 36,246  | 919                | 1,208            |
| 2025-05 | 25,716          | 33,818  | 829                | 1,091            |
| 2025-06 | 24,370          | 32,152  | 812                | 1,072            |
| 2025-07 | 22,334          | 28,912  | 720                | 933              |
| 2025-08 | 17,051          | 21,623  | 550                | 698              |
| 2025-09 | 27,707          | 34,910  | 924                | 1,164            |
| 2025-10 | 33,324          | 44,914  | 1,075              | 1,449            |
| 2025-11 | 25,444          | 32,056  | 848                | 1,069            |
| 2025-12 | 21,321          | 26,671  | 688                | 860              |

**Typical range:** 700-1,100 unique visitors/day, 900-1,500 visits/day.

**Seasonal patterns:**
- Peak: October (rentrée effet)
- Low: August (summer holidays), December (year-end)

### Engagement Metrics

| Month   | Bounce Rate | Actions/Visit | Avg Time on Site |
|---------|-------------|---------------|------------------|
| 2025-01 | 62%         | 3.3           | 2m 40s           |
| 2025-02 | 62%         | 3.3           | 2m 44s           |
| 2025-03 | 62%         | 3.3           | 2m 43s           |
| 2025-04 | 61%         | 3.1           | 2m 44s           |
| 2025-05 | 60%         | 3.2           | 2m 30s           |
| 2025-06 | 61%         | 3.0           | 2m 28s           |
| 2025-07 | 59%         | 3.0           | 2m 21s           |
| 2025-08 | 62%         | 2.9           | 2m 14s           |
| 2025-09 | 64%         | 2.7           | 2m 04s           |
| 2025-10 | 67%         | 2.6           | 1m 59s           |
| 2025-11 | 67%         | 2.4           | 2m 02s           |
| 2025-12 | 67%         | 2.5           | 2m 09s           |

**Trend:** Bounce rate increased from 60% to 67% over 2025; actions per visit decreased from 3.3 to 2.5.

## Custom Dimensions

No custom dimensions are configured for this site.

## Matomo Events

Scraped from codebase and Matomo API 2026-01-03. ~60 distinct events tracked.

### Implementation

- **HTML pattern:** Elements with `class="matomo-event"` and `data-matomo-*` attributes
- **JS handler:** `/lacommunaute/static/javascripts/matomo.js` - captures clicks on `.matomo-event` elements
- **Consent:** Uses Tarteaucitron for GDPR consent management
- **Custom URL:** Server-side `matomo_custom_url` variable for page tracking

### Event Categories

All events use the pattern: `category` / `action` / `name` (stored in `data-matomo-option`)

#### engagement (main category, ~11k events/month)

Primary user engagement tracking. Top events by volume (Dec 2025):

| Action | Name | Events | Description |
|--------|------|--------|-------------|
| view | fiches_techniques | 2,132 | Views documentation sheets |
| showmore | topic | 1,231 | Expands topic content |
| showmore | post | 1,276 | Expands post content |
| view | documentation_header | 682 | Clicks docs in header nav |
| view | topic | 668 | Views topic detail |
| search | submit_query_header | 535 | Header search submission |
| search | submit_query | 693 | Search form submission |
| view | forum | 447 | Views forum list |
| view | dsp | 307 | Views DSP diagnostic |
| view | topics | 320 | Views topic list |
| filter | forum | 271 | Filters forum |
| view | events | 240 | Views events list |
| view | documentation_breadcrumb | 226 | Breadcrumb nav to docs |
| view | member | 162 | Views member profile |
| rate | post | 117 | Rates a post |
| filter | topics | 126 | Filters topics |
| view | topics_breadcrumb | 81 | Breadcrumb nav to topics |
| contribute | new_topic | 69 | Creates new topic |
| loadmore | topic | 64 | Loads more topics |
| contribute | post | 359 | Creates forum post |
| view | event | 36 | Views single event |
| contribute | new_topic_on_docs | 36 | Creates topic from docs page |
| view | upvotes | 26 | Views upvotes page |
| view | documentation | 23 | Views documentation section |
| contribute | new_topic_after_search | 22 | Creates topic after searching |
| upvote | post | 6 | Upvotes a post |
| show | fichestechniques | 1,105 | Shows technical sheets list |
| emplois | search-prescriber | 132 | Links to Emplois prescriber search |
| emplois | search-company-header | 43 | Links to Emplois company search |
| emplois | search-company | 21 | Links to Emplois company search |
| emplois | search-prescriber-header | 13 | Links to Emplois prescriber search |
| topic-create-check | itou-jobseeker | 12 | Job seeker topic validation |
| landing | devenircip | 18 | Landing page CIP |

#### support (22 events/month)

External resource links.

| Action | Name | Description |
|--------|------|-------------|
| site_emplois | footer | Footer link to Emplois support |

#### promotion-partenaires (14 events/month)

Partner promotion clicks.

| Action | Name | Description |
|--------|------|-------------|
| clic | inclusion-demain | Partner link: inclusion-demain.fr |

#### landing (26 events/month)

Landing page navigation.

| Action | Name | Description |
|--------|------|-------------|
| glossaire | footer | Footer link to glossary |
| devenircip | (from engagement) | CIP landing page |

### DSP Diagnostic Events

The DSP (Diagnostic Socio-Professionnel) feature generates dynamic events based on diagnostic results.

| Action | Name Pattern | Description |
|--------|--------------|-------------|
| dsp | submit-dsp | Submits diagnostic (341 events) |
| dsp | submit-an-other-dsp | Submits another diagnostic (15 events) |
| dsp | visit-{theme}--{subtheme} | Clicks to view resources for specific needs |

**DSP visit themes observed (Dec 2025):**
- `visit-trouver-un-emploi` (18)
- `visit-apprendre-francais--accompagnement-insertion-pro` (15)
- `visit-apprendre-francais--communiquer-vie-tous-les-jours` (8)
- `visit-handicap--adaptation-au-poste-de-travail` (7)
- `visit-logement-hebergement` (7)
- `visit-acces-aux-droits-et-citoyennete--connaitre-ses-droits` (6)
- `visit-mobilite` (6)
- Plus 10+ additional theme/subtheme combinations

### Top Events Summary (Dec 2025)

| Rank | Category | Action | Name | Events |
|------|----------|--------|------|--------|
| 1 | engagement | view | fiches_techniques | 2,132 |
| 2 | engagement | showmore | post | 1,276 |
| 3 | engagement | showmore | topic | 1,231 |
| 4 | engagement | show | fichestechniques | 1,105 |
| 5 | engagement | search | submit_query | 693 |
| 6 | engagement | view | documentation_header | 682 |
| 7 | engagement | view | topic | 668 |
| 8 | engagement | search | submit_query_header | 535 |

### Implementation Notes

**Codebase locations with tracking:**
- `lacommunaute/templates/layouts/base.html` - Matomo initialization
- `lacommunaute/templates/pages/home.html` - Home page engagement
- `lacommunaute/templates/forum/index.html` - Forum navigation
- `lacommunaute/templates/forum/forum_detail.html` - Forum detail views
- `lacommunaute/templates/forum_conversation/topic_list.html` - Topic list interactions
- `lacommunaute/templates/forum/partials/rating.html` - Post rating
- `lacommunaute/templates/surveys/dsp_form.html` - DSP submission
- `lacommunaute/templates/surveys/dsp_detail.html` - DSP result actions
- `lacommunaute/templates/partials/header.html` - Header navigation
- `lacommunaute/templates/partials/footer.html` - Footer links
- `lacommunaute/templates/partials/upvotes.html` - Upvote tracking
- `lacommunaute/templates/search/search_form.html` - Search tracking
- `lacommunaute/templates/forum_conversation/partials/topic_filter.html` - Filter tracking

**Data collection scripts:**
- `lacommunaute/utils/matomo.py` - Matomo API utilities
- `lacommunaute/stats/management/commands/collect_matomo_stats.py` - Visit stats collection
- `lacommunaute/stats/management/commands/collect_matomo_forum_stats.py` - Forum stats collection

## Site Context

La Communaute is a Django-based community forum for professionals in the French social inclusion sector.

**Key features:**
- Forum discussions (topics, posts)
- Documentation/technical sheets (fiches techniques)
- DSP diagnostic tool (Diagnostic Socio-Professionnel)
- Events calendar
- User profiles with upvotes
- Integration links to Emplois platform

**Technology stack:**
- Django (Python)
- machina (Django forum library)
- Tarteaucitron (GDPR consent)
- HTMX (dynamic interactions)
