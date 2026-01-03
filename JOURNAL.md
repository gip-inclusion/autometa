# Cyberputois Journal

> Here are all the updates to the context engine (ie, AGENTS.md, ./knowledge and ./skills).
> New entries are added to the top of the list.

- 2026-01-03. Tested Cohorts API: all 3 methods work (getCohorts, getCohortsOverTime, getByPeriodOfFirstVisit). Documented usage patterns, example retention data, and caveat about segments causing timeouts. Updated knowledge/matomo/cohorts.md.
- 2026-01-03. CRITICAL fix: documented that Matomo segments filter VISITS not EVENTS. Added methodology for identifying which events fire ON specific pages (clone repo, grep for matomo_event, check template paths). Updated sync-events/SKILL.md and knowledge/matomo/core-modules.md.
- 2026-01-03. Fixed import path in matomo.py to use relative import for ui_mapping, ensuring compatibility when run from different directories.
- 2026-01-03. Added sync-events skill: two-pronged approach to sync Matomo events between codebase and actual tracking.
- 2026-01-03. Added Matomo events documentation to emplois.md: ~108 events across 23 categories. Documented dynamic patterns (connexion+account_type, candidature+user_kind, status appends). Verified against live Matomo data.
- 2026-01-03. Reorganized knowledge/: sites/ for website docs, matomo/ for API reference. Split API reference into README.md (index), core-modules.md, cohorts.md, funnels.md. Updated AGENTS.md with new structure.
- 2026-01-03. AGENTS.md: reports must be written in French by default.
- 2026-01-03. Updated Cohorts methods with correct API: get_cohorts() uses Cohorts.getCohorts, added get_cohorts_over_time() and get_cohorts_by_first_visit().
- 2026-01-03. Added get_visit_frequency() and get_cohorts() to matomo.py. Updated UI_MAPPING.
- 2026-01-03. Refactored querying skill: extracted UI mapping to ui_mapping.py. Added test suite (test_matomo.py) with 18 unit tests + 14 integration tests. Added conftest.py for configurable test parameters.
- 2026-01-03. Fixed _UI_MAPPING with correct Matomo category/subcategory IDs discovered via API.getWidgetMetadata. Added exploring-web-ui skill for testing UI links.
- 2026-01-03. Extended querying skill with 5 new modules: Events (get_event_categories/actions/names), Entry/Exit pages, Transitions (page flow), VisitTime (by hour/day), Referrers (types/websites/search/social). Updated _UI_MAPPING and SKILL.md documentation.
- 2026-01-03. Updated AGENTS.md: clarified data sourcing rules — every data point needs a clickable Matomo UI link + raw API call.
- 2026-01-03. Added `get_ui_url()` and `format_data_source()` to scripts/matomo.py: generates clickable Matomo web UI links from API method calls. Maps API methods to UI categories.
- 2026-01-03. Added 2025 traffic baselines to emplois.md: monthly visitor stats, user type distribution by month, baseline proportions (employer:prescriber ~1.3:1 site-wide), custom dimensions reference.
- 2026-01-03. Edited example.md: added baseline levels of widgets.
