# Multi-Source Architecture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add support for multiple Metabase instances with clean credential management and knowledge organization.

**Architecture:** Config file (`config/sources.yaml`) defines instances with `${env.VAR}` syntax for secrets. New `lib/sources.py` module loads config and returns configured API clients. Sync scripts read from config and require explicit `--instance` flag.

**Tech Stack:** Python, PyYAML, existing MetabaseAPI client

---

### Task 1: Create config directory and sources.yaml

**Files:**
- Create: `config/sources.yaml`
- Create: `config/sources.yaml.example`
- Modify: `.gitignore`

**Step 1: Create config directory**

```bash
mkdir -p config
```

**Step 2: Create sources.yaml.example (template for git)**

```yaml
# Data source configuration
# Copy to sources.yaml and fill in API keys in .env

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
    url: https://datalake.example.com
    api_key: ${env.METABASE_DATALAKE_API_KEY}
    knowledge_path: knowledge/datalake/
    dashboards: {}

matomo:
  _default: inclusion

  inclusion:
    url: https://matomo.inclusion.beta.gouv.fr
    token: ${env.MATOMO_TOKEN}
```

**Step 3: Copy to sources.yaml (actual config)**

```bash
cp config/sources.yaml.example config/sources.yaml
```

**Step 4: Commit**

```bash
git add config/sources.yaml.example
git commit -m "add config/sources.yaml.example for multi-source setup"
```

---

### Task 2: Create lib/sources.py module

**Files:**
- Create: `lib/__init__.py`
- Create: `lib/sources.py`

**Step 1: Create lib directory and __init__.py**

```bash
mkdir -p lib
touch lib/__init__.py
```

**Step 2: Create sources.py**

```python
"""
Load data source configuration and return configured API clients.

Usage:
    from lib.sources import get_metabase, get_matomo, load_config

    api = get_metabase()           # default instance (stats)
    api = get_metabase("datalake") # explicit instance

    matomo = get_matomo()          # default instance (inclusion)
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml


# Config file location
CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"

# Cached config
_config: dict | None = None


def _substitute_env_vars(value: Any) -> Any:
    """Recursively substitute ${env.VAR} patterns with environment values."""
    if isinstance(value, str):
        pattern = r'\$\{env\.([^}]+)\}'

        def replacer(match):
            var_name = match.group(1)
            env_value = os.environ.get(var_name)
            if env_value is None:
                raise ValueError(f"Environment variable {var_name} not set")
            return env_value

        return re.sub(pattern, replacer, value)

    elif isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]

    return value


def load_config(force_reload: bool = False) -> dict:
    """Load and parse sources.yaml, substituting environment variables."""
    global _config

    if _config is not None and not force_reload:
        return _config

    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config file not found: {CONFIG_PATH}\n"
            f"Copy config/sources.yaml.example to config/sources.yaml"
        )

    with open(CONFIG_PATH) as f:
        raw_config = yaml.safe_load(f)

    _config = _substitute_env_vars(raw_config)
    return _config


def get_source_config(source_type: str, instance: str | None = None) -> dict:
    """
    Get configuration for a specific source instance.

    Args:
        source_type: "metabase" or "matomo"
        instance: Instance name, or None for default

    Returns:
        Configuration dict for the instance
    """
    config = load_config()

    if source_type not in config:
        raise ValueError(f"Unknown source type: {source_type}")

    source_config = config[source_type]

    # Resolve instance name
    if instance is None:
        instance = source_config.get("_default")
        if instance is None:
            raise ValueError(f"No default instance for {source_type}")

    if instance not in source_config:
        available = [k for k in source_config.keys() if not k.startswith("_")]
        raise ValueError(
            f"Unknown {source_type} instance: {instance}. "
            f"Available: {', '.join(available)}"
        )

    return source_config[instance]


def get_metabase(instance: str | None = None):
    """
    Get a configured MetabaseAPI client.

    Args:
        instance: Instance name ("stats", "datalake"), or None for default

    Returns:
        Configured MetabaseAPI instance
    """
    from skills.metabase_query.scripts.metabase import MetabaseAPI

    config = get_source_config("metabase", instance)

    return MetabaseAPI(
        url=config["url"],
        api_key=config["api_key"],
    )


def get_matomo(instance: str | None = None):
    """
    Get a configured MatomoAPI client.

    Args:
        instance: Instance name, or None for default

    Returns:
        Configured MatomoAPI instance
    """
    from skills.matomo_query.scripts.matomo import MatomoAPI

    config = get_source_config("matomo", instance)

    return MatomoAPI(
        base_url=config["url"],
        token=config["token"],
    )


def list_instances(source_type: str) -> list[str]:
    """List available instances for a source type."""
    config = load_config()

    if source_type not in config:
        return []

    return [k for k in config[source_type].keys() if not k.startswith("_")]


def get_default_instance(source_type: str) -> str | None:
    """Get the default instance name for a source type."""
    config = load_config()

    if source_type not in config:
        return None

    return config[source_type].get("_default")
```

**Step 3: Commit**

```bash
git add lib/
git commit -m "add lib/sources.py for multi-instance config loading"
```

---

### Task 3: Update .env and .env.example

**Files:**
- Modify: `.env`
- Create or modify: `.env.example` (if exists)

**Step 1: Check current .env structure**

```bash
grep -E "METABASE|MATOMO" .env
```

**Step 2: Update .env with new variable names**

Rename:
- `METABASE_API_KEY` → `METABASE_STATS_API_KEY`
- Keep `MATOMO_TOKEN` as-is (already correct)

Remove (now in sources.yaml):
- `METABASE_BASE_URL`
- `METABASE_DATABASE_ID`

**Step 3: No commit needed** (.env is gitignored)

---

### Task 4: Update sync_inventory.py to use config

**Files:**
- Modify: `skills/sync_metabase/scripts/sync_inventory.py`

**Step 1: Remove hardcoded PUBLIC_DASHBOARDS dict**

Delete lines 50-76 (the `PUBLIC_DASHBOARDS = {...}` block).

**Step 2: Add imports and config loading at top**

After the existing imports, add:

```python
from lib.sources import load_config, get_source_config, get_metabase
```

**Step 3: Update argument parser**

Replace the `--dashboards` argument with `--instance` and `--all`:

```python
def main():
    parser = argparse.ArgumentParser(description="Sync Metabase cards to markdown/SQLite")
    parser.add_argument("--instance", type=str, help="Metabase instance to sync (e.g., stats, datalake)")
    parser.add_argument("--all", action="store_true", help="Sync all configured instances")
    parser.add_argument("--skip-categorize", action="store_true", help="Skip AI categorization")
    parser.add_argument("--sqlite", action="store_true", help="Also generate SQLite database")
    parser.add_argument("--sqlite-only", action="store_true", help="Only generate SQLite, skip markdown")
    args = parser.parse_args()

    # Require explicit instance selection
    if not args.instance and not args.all:
        config = load_config()
        available = [k for k in config.get("metabase", {}).keys() if not k.startswith("_")]
        print("Error: Please specify --instance <name> or --all")
        print(f"Available instances: {', '.join(available)}")
        sys.exit(1)

    # Determine which instances to sync
    if args.all:
        config = load_config()
        instances = [k for k in config.get("metabase", {}).keys() if not k.startswith("_")]
    else:
        instances = [args.instance]

    for instance_name in instances:
        sync_instance(instance_name, args)
```

**Step 4: Extract sync logic into sync_instance function**

Create new function that takes instance name and args:

```python
def sync_instance(instance_name: str, args):
    """Sync a single Metabase instance."""

    # Load instance config
    instance_config = get_source_config("metabase", instance_name)
    dashboard_ids = list(instance_config.get("dashboards", {}).keys())
    public_dashboards = instance_config.get("dashboards", {})
    knowledge_path = Path(instance_config.get("knowledge_path", f"knowledge/{instance_name}/"))

    # Output directories (relative to project root)
    project_root = Path(__file__).parent.parent.parent.parent
    stats_dir = project_root / knowledge_path
    cards_dir = stats_dir / "cards"
    dashboards_dir = stats_dir / "dashboards"

    # ... rest of sync logic, using dashboard_ids and public_dashboards
```

**Step 5: Update API initialization**

Replace:
```python
api = MetabaseAPI()
```

With:
```python
api = get_metabase(instance_name)
```

**Step 6: Update dashboard metadata to use config**

Replace references to `PUBLIC_DASHBOARDS.get(dash_id)` with `public_dashboards.get(dash_id)`.

**Step 7: Test the changes**

```bash
python -m skills.sync_metabase.scripts.sync_inventory
# Should error: "Please specify --instance <name> or --all"

python -m skills.sync_metabase.scripts.sync_inventory --instance stats --skip-categorize
# Should work
```

**Step 8: Commit**

```bash
git add skills/sync_metabase/scripts/sync_inventory.py
git commit -m "sync_inventory: require explicit --instance, read config from sources.yaml"
```

---

### Task 5: Create knowledge/datalake/ structure

**Files:**
- Create: `knowledge/datalake/README.md`
- Create: `knowledge/datalake/cards/.gitkeep`
- Create: `knowledge/datalake/dashboards/.gitkeep`

**Step 1: Create directory structure**

```bash
mkdir -p knowledge/datalake/cards knowledge/datalake/dashboards
```

**Step 2: Create README.md**

```markdown
# Datalake Metabase Instance

**URL:** https://datalake.example.com
**Instance name:** `datalake`

## Usage

```python
from lib.sources import get_metabase

api = get_metabase("datalake")
result = api.execute_sql("SELECT 1", database_id=1)
```

## Databases

| ID | Name | Description |
|----|------|-------------|
| TBD | TBD | TBD |

## Key Tables

TBD - document tables after initial exploration.
```

**Step 3: Create .gitkeep files**

```bash
touch knowledge/datalake/cards/.gitkeep
touch knowledge/datalake/dashboards/.gitkeep
```

**Step 4: Commit**

```bash
git add knowledge/datalake/
git commit -m "add knowledge/datalake/ structure for new instance"
```

---

### Task 6: Update AGENTS.md with new usage patterns

**Files:**
- Modify: `AGENTS.md`

**Step 1: Find and update Metabase usage section**

Add after the existing Metabase import example:

```markdown
### Multi-Instance Support

Data sources are configured in `config/sources.yaml`. Use `lib/sources` to get configured clients:

```python
from lib.sources import get_metabase, get_matomo

# Default instance (stats)
api = get_metabase()

# Explicit instance
api = get_metabase("datalake")

# Matomo (same pattern)
matomo = get_matomo()
```

**Available Metabase instances:**
- `stats` (default) - IAE employment dashboards at stats.inclusion.beta.gouv.fr
- `datalake` - Other domain data

**Sync commands:**
```bash
python -m skills.sync_metabase.scripts.sync_inventory --instance stats
python -m skills.sync_metabase.scripts.sync_inventory --instance datalake
python -m skills.sync_metabase.scripts.sync_inventory --all
```
```

**Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: add multi-instance usage patterns to AGENTS.md"
```

---

### Task 7: Final verification

**Step 1: Test full sync with stats instance**

```bash
python -m skills.sync_metabase.scripts.sync_inventory --instance stats --skip-categorize
```

**Step 2: Verify lib/sources works**

```bash
python -c "from lib.sources import get_metabase; api = get_metabase(); print(api.get_current_user())"
```

**Step 3: Verify error messages**

```bash
python -m skills.sync_metabase.scripts.sync_inventory
# Should show: "Error: Please specify --instance <name> or --all"

python -c "from lib.sources import get_metabase; get_metabase('nonexistent')"
# Should show: "Unknown metabase instance: nonexistent"
```

**Step 4: Final commit with updated design doc**

```bash
git add docs/plans/2026-01-16-multi-source-design.md
git commit -m "docs: mark multi-source design as implemented"
```
