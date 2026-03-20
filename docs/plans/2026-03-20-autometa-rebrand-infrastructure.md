# Autometa Rebrand — Infrastructure Phases

Phase 1 (done): renamed all user-facing strings, code identifiers, and
in-repo config from Matometa to Autometa.  Everything below involves
external side effects.

---

## Phase 2: GitHub Repository

**Rename `gip-inclusion/Matometa` → `gip-inclusion/Autometa`.**

GitHub auto-redirects the old URL, so nothing breaks immediately.

Side effects:
- Update clone URLs in `README.md` and `web/templates/connaissances.html`
  (currently still point to `gip-inclusion/Matometa`)
- Update any CI/CD that references the repo by name
- Inform team members (bookmarks, local remotes)

## Phase 3: SQLite Database File

**Rename `data/matometa.db` → `data/autometa.db`.**

Referenced in: `web/config.py`, `scripts/sync_to_scalingo.py`,
`scripts/migrate_to_scalingo.py`, `scripts/backfill_tool_taxonomy.py`,
`skills/wishlist/scripts/wishlist.py`, `AGENTS.md`, `README.md`,
`knowledge/notion/_index.md`.

Side effects:
- Every deployment (local, VPS, Scalingo) must `mv matometa.db autometa.db`
- The VPS rsync path in `scripts/sync_to_scalingo.py` references the
  remote file by name — coordinate with remote rename

## Phase 4: Scalingo App

**Rename or recreate the Scalingo app from `matometa` to `autometa`.**

Scalingo doesn't support app rename; this means creating a new app and
migrating.

Side effects:
- New app name in `.github/workflows/deploy.yml` (git remote)
- New app name in `AGENTS.local.md` (all `scalingo -a matometa` commands)
- New app name in `scripts/import_sql.py`
- New Scalingo PostgreSQL addon → database migration
- DNS: update CNAME for `matometa.inclusion.gouv.fr` (or create new
  `autometa.inclusion.gouv.fr`)
- Update CORS origins in `web/routes/query.py` (3 URLs)
- Update `docs/scaling-recommendations.md` AllowedOrigins

## Phase 5: DNS and URLs

**Migrate domain names.**

- Update `BASE_URL` env var on all deployments
- Update `docs/interactive-apps.md` BASE_URL example
- Keep old domains as redirects for a transition period

## Phase 6: S3 Bucket

**Rename `S3_BUCKET=matometa` → `S3_BUCKET=autometa`.**

Side effects:
- Create new bucket, copy objects, update env vars
- Update `README.md` Scalingo setup instructions

## Phase 7: Datalake PostgreSQL

**Rename the `matometa` schema and `matometa_*` tables.**

This is the heaviest migration.  ~95k rows in inscriptions alone.

Tables to rename:
- `matometa_webinaires` → `autometa_webinaires`
- `matometa_webinaire_sessions` → `autometa_webinaire_sessions`
- `matometa_webinaire_inscriptions` → `autometa_webinaire_inscriptions`
- `matometa_webinaire_sync_meta` → `autometa_webinaire_sync_meta`
- Schema `matometa` → `autometa`

Side effects:
- `ALTER TABLE ... RENAME` + `ALTER SCHEMA ... RENAME` on live datalake
- Update `lib/webinaires.py` table constants
- Update `scripts/datalake_create_webinaires.py` DDL
- Update `knowledge/webinaires/_index.md` (all SQL examples)
- Update `knowledge/datalake/README.md` table docs
- Update `docs/interactive-apps.md` schema references
- Coordinate with any Metabase questions that query these tables

## Phase 8: External Identities

Low priority, may not be worth the effort:
- RDV-Insertion API user `matometa` (id=35) — request rename from rdvi team
- Email `matometa@inclusion.gouv.fr` — request from IT
- SSH user `matometa@ljt.cc` on VPS

## Signal Backward Compatibility

`lib/api_signals.py` currently accepts both `[AUTOMETA:API:...]` and
`[MATOMETA:API:...]` in its regex.  This covers the transition period
where old containers or cached agent sessions may still emit the old
prefix.  Remove the `MATOMETA` alternative once all deployments are
updated (after phase 4).
