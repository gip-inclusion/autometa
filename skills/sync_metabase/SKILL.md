---
name: sync_metabase
description: Sync Metabase cards inventory to markdown files (default) or SQLite database
---

# Metabase Sync Skill

Synchronize Metabase cards from public dashboards on pilotage.inclusion.beta.gouv.fr to Markdown files for git tracking.

## Usage

```bash
# Full sync with AI categorization (generates markdown)
python -m skills.sync_metabase.scripts.sync_inventory

# Quick sync without AI categorization
python -m skills.sync_metabase.scripts.sync_inventory --skip-categorize

# Also generate SQLite database
python -m skills.sync_metabase.scripts.sync_inventory --sqlite

# SQLite only (no markdown)
python -m skills.sync_metabase.scripts.sync_inventory --sqlite-only

# Sync specific dashboards only
python -m skills.sync_metabase.scripts.sync_inventory --dashboards 216 408
```

## What it does

1. **Fetches dashboards** from pilotage.inclusion.beta.gouv.fr (18 public dashboards)
2. **Extracts cards** from each dashboard with SQL queries
3. **AI categorization** (optional) - uses Claude to assign topic categories
4. **Writes Markdown files** (default) to `knowledge/stats/`
5. **Writes SQLite database** (optional, with `--sqlite`) to `knowledge/metabase/cards.db`

## Public Dashboards

The sync covers all dashboards visible on pilotage.inclusion.beta.gouv.fr:

| ID | Dashboard | Pilotage URL |
|----|-----------|--------------|
| 90 | Métiers recherchés et proposés | /tableaux-de-bord/metiers/ |
| 150 | Postes en tension | /tableaux-de-bord/postes-en-tension/ |
| 54 | Zoom sur les employeurs | /tableaux-de-bord/zoom-employeurs/ |
| 408 | Candidats file active | /tableaux-de-bord/candidat-file-active-IAE/ |
| 216 | Femmes dans l'IAE | /tableaux-de-bord/femmes-iae/ |
| 337 | Bilan annuel candidatures | /tableaux-de-bord/bilan-candidatures-iae/ |
| 218 | Cartographies | /tableaux-de-bord/cartographies-iae/ |
| 116 | Traitement candidatures | /tableaux-de-bord/etat-suivi-candidatures/ |
| 32 | Auto-prescription | /tableaux-de-bord/auto-prescription/ |
| 52 | Zoom prescripteurs | /tableaux-de-bord/zoom-prescripteurs/ |
| 136 | Prescripteurs habilités | /tableaux-de-bord/prescripteurs-habilites/ |
| 287 | Conventionnements IAE | /tableaux-de-bord/conventionnements-iae/ |
| 325 | Analyses conventionnements | /tableaux-de-bord/analyses-conventionnements-iae/ |
| 336 | Demandes prolongation | /tableaux-de-bord/suivi-demandes-prolongation/ |
| 217 | Suivi Pass IAE | /tableaux-de-bord/suivi-pass-iae/ |
| 571 | ESAT 2025 | /tableaux-de-bord/zoom-esat-2025/ |
| 471 | ESAT 2024 | /tableaux-de-bord/zoom-esat-2024/ |
| 306 | ESAT 2023 | /tableaux-de-bord/zoom-esat/ |

## Output

### Markdown (default)

- `knowledge/stats/_index.md` - overview with links
- `knowledge/stats/cards/topic-*.md` - cards grouped by topic
- `knowledge/stats/dashboards/dashboard-*.md` - cards per dashboard

### SQLite (optional)

- `knowledge/metabase/cards.db` - full-text searchable database

## Prerequisites

- `METABASE_BASE_URL` and `METABASE_API_KEY` in `.env`
- `ANTHROPIC_API_KEY` in `.env` (for AI categorization)

## Topics

Cards are categorized into these topics:

| Topic | Description |
|-------|-------------|
| file-active | Candidates waiting 30+ days |
| postes-tension | Hard to fill positions |
| candidatures | Application flows |
| demographie | Age/gender breakdowns |
| employeurs | SIAE/employer data |
| prescripteurs | Prescriber data |
| auto-prescription | Auto-prescription metrics |
| controles | Compliance data |
| prolongations | PASS extensions |
| etp-effectifs | Workforce metrics |
| esat | ESAT-specific |
| pass-iae | PASS IAE delivery and tracking |
| autre | Uncategorized |
