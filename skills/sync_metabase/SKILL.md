---
name: sync_metabase
description: Sync the Metabase cards and dashboards inventory of every instance into the PostgreSQL cache read by the agent
---

# Metabase Sync Skill

Synchronize the cards and dashboards of every configured Metabase instance into the application database (`metabase_cards`, `metabase_dashboards`). At startup the application turns them into `data/cache/metabase/` files, which the agent reads. Nothing is written to `knowledge/`.

## Usage

```bash
python -m skills.sync_metabase.scripts.sync_inventory
```

No option: every instance is synced. In production it runs nightly in the `synchros` cron batch (`cron/sync-inventory/CRON.md`).

## What it does

1. **Fetches dashboards and cards** of each Metabase instance
2. **Extracts table references** from each card's SQL and infers a topic from them
3. **Writes the inventory** into the cache tables, replacing the previous one

## Public Dashboards

Dashboards published on pilotage.inclusion.beta.gouv.fr (stats instance), for reference:

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

Rows in `metabase_cards` and `metabase_dashboards`, exposed as `data/cache/metabase/*.md` after the next application start.

## Prerequisites

- Instance URLs and API keys from `config/sources.yaml` (`METABASE_*_API_KEY` in `.env`)

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
