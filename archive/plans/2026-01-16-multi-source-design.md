# Multi-Source Architecture Design

**Date:** 2026-01-16
**Status:** Draft

## Problem

Currently Matometa supports a single Metabase instance. We need to add a second instance (datalake) with a completely different data domain. This requires:

1. Managing multiple API credentials
2. Organizing knowledge clearly by instance
3. Updating API clients and sync scripts

## Design

### 1. Credential Management

Create `config/sources.yaml` to define data sources:

```yaml
metabase:
  _default: stats

  stats:
    url: https://stats.inclusion.beta.gouv.fr
    api_key: ${env.METABASE_STATS_API_KEY}
    knowledge_path: knowledge/stats/
    dashboards:
      90: /tableaux-de-bord/metiers/
      150: /tableaux-de-bord/postes-en-tension/
      54: /tableaux-de-bord/zoom-employeurs/
      408: /tableaux-de-bord/candidat-file-active-IAE/
      216: /tableaux-de-bord/femmes-iae/
      337: /tableaux-de-bord/bilan-candidatures-iae/
      218: /tableaux-de-bord/cartographies-iae/
      116: /tableaux-de-bord/etat-suivi-candidatures/
      32: /tableaux-de-bord/auto-prescription/
      52: /tableaux-de-bord/zoom-prescripteurs/
      136: /tableaux-de-bord/prescripteurs-habilites/
      287: /tableaux-de-bord/conventionnements-iae/
      325: /tableaux-de-bord/analyses-conventionnements-iae/
      336: /tableaux-de-bord/suivi-demandes-prolongation/
      217: /tableaux-de-bord/suivi-pass-iae/
      571: /tableaux-de-bord/zoom-esat-2025/
      471: /tableaux-de-bord/zoom-esat-2024/
      306: /tableaux-de-bord/zoom-esat/

  datalake:
    url: https://datalake.inclusion.beta.gouv.fr
    api_key: ${env.METABASE_DATALAKE_API_KEY}
    knowledge_path: knowledge/datalake/
    dashboards: {}

matomo:
  _default: inclusion

  inclusion:
    url: https://matomo.inclusion.beta.gouv.fr
    token: ${env.MATOMO_TOKEN}
```

**Principles:**
- URLs and metadata are version-controlled (not secrets)
- API keys stay in `.env` via `${env.VAR}` syntax (parsed at load time)
- `database_id` is not in config - it's query-level, documented in knowledge

### 2. Knowledge Organization

Preserve separation between technical and business knowledge:

```
knowledge/
  # Technical - how to use APIs
  matomo/
    README.md              # API patterns, timeout handling
  metabase/
    README.md              # API patterns, SQL tips, generic reference

  # Business - what data exists (per instance)
  sites/                   # website tracking context (Matomo)
    emplois.md
    marche.md
    ...
  stats/                   # stats Metabase instance (IAE data)
    README.md              # instance overview, databases, key tables
    _index.md              # generated cards/dashboards index
    cards/
      topic-candidatures.md
      topic-controles.md
      ...
    dashboards/
      dashboard-32.md
      ...
  datalake/                # datalake Metabase instance (other domain)
    README.md
    _index.md
    cards/
    dashboards/
```

**Migration:** Move existing `knowledge/stats/` content as-is (it's already for the stats instance).

### 3. API Client

New helper module `lib/sources.py`:

```python
from lib.sources import get_metabase, get_matomo

# Default instance (stats)
api = get_metabase()
api.execute_sql("SELECT 1", database_id=2)

# Explicit instance
api = get_metabase("datalake")
api.execute_sql("SELECT 1", database_id=1)

# Matomo (same pattern)
matomo = get_matomo()  # default: inclusion
```

**Implementation:**
1. Load `config/sources.yaml`
2. Parse `${env.VAR}` patterns, substitute from environment
3. Return configured client instance
4. Cache parsed config (reload on file change optional)

### 4. Sync Scripts

Require explicit instance selection:

```bash
# Must specify instance
python -m skills.sync_metabase.scripts.sync_inventory --instance stats
python -m skills.sync_metabase.scripts.sync_inventory --instance datalake

# Sync all instances
python -m skills.sync_metabase.scripts.sync_inventory --all

# No args = error with usage hint
```

**Changes to sync_inventory.py:**
- Remove hardcoded `PUBLIC_DASHBOARDS` dict
- Read dashboards from `config/sources.yaml`
- Write output to instance's `knowledge_path`
- Require `--instance` or `--all` flag

### 5. Environment Variables

Update `.env` (and `.env.example`):

```bash
# Before
METABASE_BASE_URL=https://stats.inclusion.beta.gouv.fr
METABASE_API_KEY=xxx
METABASE_DATABASE_ID=2

# After
METABASE_STATS_API_KEY=xxx
METABASE_DATALAKE_API_KEY=yyy
MATOMO_TOKEN=zzz
```

Note: `DATABASE_ID` moves to knowledge docs or per-query parameter.

## Files to Create/Modify

**Create:**
- `config/sources.yaml` - source definitions
- `config/sources.yaml.example` - template without secrets (for git)
- `lib/sources.py` - config loader and client factory
- `knowledge/datalake/README.md` - new instance docs

**Modify:**
- `skills/metabase_query/scripts/metabase.py` - use sources.py or keep standalone
- `skills/sync_metabase/scripts/sync_inventory.py` - read config, require --instance
- `.env` / `.env.example` - rename env vars
- `.gitignore` - ignore `config/sources.yaml` if it contains secrets (or keep it public since secrets are in .env)

**Migrate:**
- `knowledge/stats/` stays in place (already correct location)
- Update `knowledge/metabase/README.md` to reference per-instance docs

## Open Questions

1. Should `config/sources.yaml` be gitignored?
   - Recommendation: No, keep it in git. Only secrets are in `.env`.

2. Backwards compatibility for existing scripts using `MetabaseAPI()` directly?
   - Recommendation: Keep working via `_default` + fallback to env vars during transition.
