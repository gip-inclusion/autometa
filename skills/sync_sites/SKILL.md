---
name: sync_sites
description: Sync Matomo baselines, dimensions, segments and events into the PostgreSQL cache read by the agent (project)
---

# Site Sync Skill

Copy fresh Matomo data (baselines, dimensions, segments, events) into PostgreSQL cache tables. At startup the application turns them into `data/cache/matomo/` files, which the agent reads next to the hand-written site documents (`knowledge/sites/*.md`). The script never writes to `knowledge/`.

## Philosophy

This skill **enriches existing documents with objective, measurable data**. It does NOT:
- Generate analyses or interpretations
- Make hypotheses about user behavior
- Add commentary that could bias the agent's reasoning

The goal is to provide **raw facts** that the agent can use as context when answering questions. All data must be:
- **Measurable**: numbers from APIs, not estimates
- **Verifiable**: includes source links or API calls
- **Dated**: always shows when data was retrieved

This keeps the knowledge base clean and prevents the agent from being influenced by stale interpretations.

## Site documents

`knowledge/sites/*.md` are written by hand (description, event documentation, analyses tied to a feature). Measured data lives in the cache, not in these documents: do not paste baselines into them.

## Usage

```bash
# Full sync (all sites, previous year's baselines + current data)
python -m skills.sync_sites.scripts.sync_sites

# Single site
python -m skills.sync_sites.scripts.sync_sites --site emplois

# Baselines of a given year
python -m skills.sync_sites.scripts.sync_sites --year 2025
```

## What it syncs

### Baselines (weekly)

For each site, fetches from Matomo:
- Monthly visitor stats (unique visitors, visits, daily averages)
- User type distribution (if custom dimensions exist)
- Engagement metrics (bounce rate, actions/visit, time on site)

### Custom Dimensions

Fetches configured custom dimensions:
- ID, name, scope (visit or action)
- Active/inactive status

### Saved Segments

Fetches saved segments from Matomo:
- Segment name and definition
- Useful for understanding pre-defined filters

### Event Names

Fetches all event names directly from Matomo:
- Event name, event count, visit count
- Top 50 events shown, sorted by volume
- Data from the reference month (default: last month)

### Event Discovery (manual)

When documenting events, search for these patterns in codebases:

**Django templates:**
- `{% matomo_event "category" "action" "name" %}`
- `data-matomo-category=`, `data-matomo-action=`, `data-matomo-option=`

**Django Python code:**
- `matomo_event_name=`, `matomo_event_option=`
- `matomo_category=`, `matomo_action=`

**JavaScript:**
- `_paq.push(['trackEvent', ...])`
- `Matomo.trackEvent(...)`

## Sites

Keys accepted by `--site`. Names, URLs and Matomo IDs are defined once, in the « Sites web » table of `AGENT.md`.

| `--site` key | Matomo ID |
|------|-----------|
| emplois | 117 |
| pilotage | 146 |
| communaute | 206 |
| dora | 211 |
| plateforme | 212 |
| rdv-insertion | 214 |
| mon-recap | 217 |
| marche | 136 |

The `plateforme` key is a legacy name: it designates the Site institutionnel (212), not the Plateforme (117).

## Schedule

Nightly, in the `synchros` cron batch (`cron/sync-sites/CRON.md`).

## Output

Rows in the Matomo cache tables of the application database (baselines, dimensions, segments, event names). They reach the agent as `data/cache/matomo/*.md`, regenerated at application startup.
