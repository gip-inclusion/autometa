# Emplois

- URL: https://emplois.inclusion.beta.gouv.fr
- Matomo site ID: 117
- GitHub: https://github.com/gip-inclusion/les-emplois

## Traffic Baselines (2025)

Data retrieved 2026-01-06 via Matomo API.

### Monthly Visitor Stats

| Month   | Unique Visitors | Visits    | Daily Avg Visitors | Daily Avg Visits |
|---------|-----------------|-----------|--------------------|-----------------:|
| 2025-01 |         189,083 |   460,201 |              6,099 |           14,845 |
| 2025-02 |         177,970 |   434,333 |              6,356 |           15,512 |
| 2025-03 |         188,675 |   466,830 |              6,086 |           15,059 |
| 2025-04 |         187,006 |   447,922 |              6,234 |           14,931 |
| 2025-05 |         165,132 |   391,514 |              5,327 |           12,629 |
| 2025-06 |         175,318 |   425,531 |              5,844 |           14,184 |
| 2025-07 |         169,339 |   424,698 |              5,463 |           13,700 |
| 2025-08 |         155,529 |   339,390 |              5,017 |           10,948 |
| 2025-09 |         219,810 |   526,170 |              7,327 |           17,539 |
| 2025-10 |         221,726 |   545,370 |              7,152 |           17,593 |
| 2025-11 |         189,674 |   452,497 |              6,322 |           15,083 |
| 2025-12 |         170,160 |   405,574 |              5,489 |           13,083 |

**Typical range:** 5,017-7,327 unique visitors/day, 10,948-17,593 visits/day.

### User Type Distribution (visits)

| Month   |    anonymous |     employer |   itou_staff |   job_seeker | labor_inspec |   prescriber |
|---------|--------------|--------------|--------------|--------------|--------------|--------------|
| 2025-01 |      280,748 |       91,138 |          160 |       24,197 |          245 |       63,710 |
| 2025-02 |      264,333 |       87,988 |           87 |       22,849 |          272 |       58,804 |
| 2025-03 |      283,548 |       96,849 |          139 |       25,378 |          367 |       60,539 |
| 2025-04 |      272,379 |       90,260 |          134 |       25,075 |          267 |       59,798 |
| 2025-05 |      240,363 |       79,116 |          115 |       22,347 |          199 |       49,333 |
| 2025-06 |      257,911 |       87,870 |          123 |       21,972 |          235 |       57,417 |
| 2025-07 |      253,321 |       89,411 |          119 |       21,503 |          359 |       59,983 |
| 2025-08 |      213,971 |       63,929 |           77 |       18,365 |          218 |       42,829 |
| 2025-09 |      326,291 |      102,636 |          141 |       27,321 |          815 |       68,947 |
| 2025-10 |      337,149 |      102,533 |          152 |       30,760 |          604 |       73,892 |
| 2025-11 |      281,392 |       82,199 |          173 |       26,756 |          427 |       61,538 |
| 2025-12 |      249,482 |       75,882 |          110 |       22,599 |          366 |       57,135 |

### Engagement Metrics

| Month   | Bounce Rate | Actions/Visit | Avg Time on Site |
|---------|-------------|---------------|------------------|
| 2025-01 |         23% |           9.4 |           6m 03s |
| 2025-02 |         23% |           9.3 |           6m 10s |
| 2025-03 |         24% |           9.1 |           6m 01s |
| 2025-04 |         23% |           9.1 |           6m 00s |
| 2025-05 |         24% |             9 |           5m 54s |
| 2025-06 |         23% |             9 |           5m 56s |
| 2025-07 |         23% |           9.2 |           6m 02s |
| 2025-08 |         27% |           8.7 |           5m 33s |
| 2025-09 |         26% |           8.7 |           5m 40s |
| 2025-10 |         26% |           8.8 |           5m 44s |
| 2025-11 |         26% |           8.8 |           5m 34s |
| 2025-12 |         25% |             9 |           5m 38s |

## Baseline Interpretations

*Manual analyses - preserved by sync.*

### Seasonal Patterns

- **Typical range:** 5,000-7,500 unique visitors/day, 11,000-17,500 visits/day
- **Peak:** September-October (rentrée)
- **Low:** August (summer holidays), May (bridge holidays), December (year-end)

### User Type Proportions

Based on December 2025 (representative month):

| User Type       | Visits  | % of total |
|-----------------|---------|------------|
| anonymous       | 244,814 | 61.5%      |
| employer        | 74,509  | 18.7%      |
| prescriber      | 56,347  | 14.1%      |
| job_seeker      | 22,111  | 5.6%       |
| labor_inspector | 362     | 0.1%       |
| itou_staff      | 107     | <0.1%      |

**Key ratio:** Employers outnumber prescribers ~1.3:1 site-wide.

### GPS (Referral Network)

Analysis based on Dec 2025 data (`/gps/*`):
- **Audience Mix:** Prescribers (57%) > Employers (38%). Inverse of site-wide baseline.
- **Loyalty:** 98.3% of visits from returning users.
- **Regional Concentration:** Département 59 (Nord) is the primary driver of GPS traffic.
- **Engagement:** Very high (37+ actions/visit).

## Custom Dimensions

| ID | Index | Scope  | Name                 | Notes                           |
|----|-------|--------|----------------------|---------------------------------|
| 1  | 1     | visit  | UserKind             | prescriber, employer, job_seeker, anonymous, labor_inspector, itou_staff |
| 2  | 2     | visit  | Unused               | Inactive                        |
| 3  | 1     | action | UserOrganizationKind | FT, ACI, AI, ML, EI, ETTI, etc. |
| 4  | 2     | action | UserDepartment       | French département number (01-976) |

Query visit-scoped dimensions with `idDimension=1`.
Query action-scoped dimensions with `idDimension=3` (org) or `idDimension=4` (dept).

## Event Names

*Data from 2025-12, retrieved 2026-01-06 via Matomo API.*

**146 distinct events tracked.**

| Name | Events | Visits |
|------|--------|--------|
| clic-metiers | 84,316 | 39,253 |
| se-connecter-avec-pro-connect | 83,843 | 78,280 |
| start_application | 63,094 | 39,694 |
| candidatures | 54,876 | 33,878 |
| clic-card-fichedeposte | 53,089 | 17,399 |
| details-salarie-tableau | 43,611 | 16,812 |
| clic-onglet-fichesdeposte | 41,340 | 27,138 |
| clic-structure | 38,639 | 16,331 |
| voir-liste-candidatures-À traiter | 32,602 | 20,264 |
| candidature_prescripteur | 31,688 | 20,509 |
| voir-liste-candidatures | 23,869 | 15,223 |
| voir-candidature-employeur | 18,730 | 8,126 |
| voir-liste-agrements | 18,656 | 12,355 |
| candidats-utilisateur | 16,582 | 11,179 |
| salaries-pass-iae | 13,653 | 8,238 |
| refuse_application | 11,732 | 4,972 |
| batch-refuse-application-reason-submit | 11,611 | 4,790 |
| batch-refuse-application-job-seeker-answer-submit | 11,325 | 4,723 |
| copied_jobseeker_email | 10,349 | 4,580 |
| historique | 10,260 | 7,482 |
| mes-candidatures | 9,573 | 6,722 |
| clic-onglet-employeur | 9,353 | 7,371 |
| batch-refuse-application-prescriber-answer-submit | 9,146 | 4,029 |
| toutes-les-nouveautes | 9,032 | 8,960 |
| création | 8,203 | 3,786 |
| accept_application_confirmation | 8,026 | 6,217 |
| informations-generales | 7,517 | 5,592 |
| processing_application | 7,471 | 3,498 |
| candidature_candidat | 7,390 | 3,504 |
| statistiques | 6,829 | 5,244 |
| postuler-pour-ce-candidat | 6,496 | 4,366 |
| accept_application | 6,133 | 4,642 |
| edit_jobseeker_infos_submit | 5,984 | 3,743 |
| candidats-organisation | 5,829 | 3,535 |
| voir-liste-fiches-salaries | 5,745 | 4,233 |
| impression-fiche-candidature | 5,242 | 2,441 |
| fiches-salaries-asp | 5,233 | 3,569 |
| se-connecter-avec-pe | 4,840 | 3,994 |
| detail-candidature | 4,446 | 3,072 |
| commentaires | 4,411 | 2,939 |
| vue-d-ensemble | 4,367 | 3,558 |
| voir-liste-candidatures-En attente | 4,192 | 2,955 |
| declarer-embauche | 4,103 | 3,172 |
| voir_candidature_prescripteur | 3,563 | 2,349 |
| clic-structure-fichedeposte | 3,541 | 2,577 |
| postpone_application | 3,531 | 1,922 |
| copied_sender_phone | 3,530 | 1,854 |
| candidatures-envoyees | 3,352 | 2,639 |
| onglet-fiches-salaries | 3,319 | 2,371 |
| tdb_liste_beneficiaires | 3,298 | 2,507 |

*... and 96 more events with lower volume.*

## Matomo Events

Scraped from codebase 2026-01-03. ~108 events tracked.

### Implementation

- **Template tag:** `{% matomo_event "category" "action" "name" %}`
- **JS handler:** `/itou/static/js/matomo.js` - catches clicks on `data-matomo-*` elements
- **Context processor:** sets custom dimensions (user kind, org kind, department)

### Event Categories

#### candidature (47 events)
Core application workflow. Most important category.

| Action | Name | Description |
|--------|------|-------------|
| clic | start_application | User starts a job application |
| clic | postuler-pour-ce-candidat | Prescriber applies on behalf of candidate |
| clic | accept_application | Employer accepts application |
| clic | refuse_application | Employer refuses application |
| clic | postpone_application | Employer postpones decision |
| submit | accept_application_confirmation | Confirms acceptance |
| submit | processing_application | Submits processing action |
| clic-onglet | informations-generales | Views general info tab |
| clic-onglet | appointments | Views appointments tab |
| clic-onglet | historique | Views history tab |
| clic | proposer-rdv | Proposes appointment |
| clic | ajout-commentaire-sidebar | Adds comment |
| exports | export-siae | SIAE exports applications |
| exports | export-prescripteur | Prescriber exports applications |
| submit | batch-*-submit | Batch operations (process, archive, refuse, etc.) |

#### employeurs (16 events)
Employer dashboard and company management.

| Action | Name | Description |
|--------|------|-------------|
| clic | structure-presentation | Views company presentation |
| clic | modifier-infos-entreprise | Edits company info |
| clic | voir-liste-candidatures | Views received applications |
| clic | voir-liste-agrements | Views PASS IAE approvals |
| clic | voir-liste-fiches-salaries | Views ASP employee records |
| clic | creer-fiche-de-poste | Creates job description |
| clic | declarer-embauche | Declares a hire |

#### connexion (7 events)
Authentication flows.

| Action | Name | Description |
|--------|------|-------------|
| clic | se-connecter-avec-pro-connect | ProConnect login |
| clic | se-connecter-avec-pe | France Travail (ex-Pôle emploi) login |
| clic | se-connecter-avec-france-connect | FranceConnect login |

#### inscription-candidat
Job seeker registration.

| Action | Name | Description |
|--------|------|-------------|
| clic | je-n-ai-pas-d-adresse-email | No email option |
| clic | creer-un-compte-candidat | Create account CTA |

#### prescribers (4 events)
Prescriber organization management.

| Action | Name | Description |
|--------|------|-------------|
| clic | organisation-presentation | Views org presentation |
| clic | gerer-collaborateurs | Manages team members |

#### gps (6 events)
GPS referral network feature (Réseau d'intervenants).

| Action | Name | Events (Dec 2025) | Description |
|--------|------|-------------------|-------------|
| clic | tdb_liste_beneficiaires | 3,298 | Click "Réseau d'intervenants" from menu |
| clic | displayed_member_email | 590 | Shows member email |
| clic | displayed_member_phone | 64 | Shows member phone |
| clic | copied_user_phone | 21 | Copies user phone |
| clic | copied_user_pe_id | 16 | Copies France Travail ID |
| clic | copied_user_email | 10 | Copies user email |

**Note:** These events are defined in Django Python code using `matomo_event_name=` / `matomo_event_option=` patterns, not in HTML templates.

#### dashboard (4 events)
Main dashboard navigation.

| Action | Name | Description |
|--------|------|-------------|
| clic-onglet | vue-d-ensemble | Overview tab |
| clic-onglet | statistiques | Statistics tab |
| clic | candidats-sans-solution | Views stalled candidates |

#### salaries (4 events)
Employee/contract management.

| Action | Name | Description |
|--------|------|-------------|
| clic | details-salarie | Views employee details |
| clic | edit_jobseeker_infos | Edits job seeker info |

#### help (7 events)
Documentation and support links.

| Action | Name | Description |
|--------|------|-------------|
| clic | footer_documentation | Footer doc link |
| clic | header_documentation | Header doc link |
| clic | zendesk_form | Support contact form |

#### offcanvasNav
Mobile/sidebar navigation clicks. All use `clic` action with menu item names:
- mes-candidatures, candidatures, candidatures-envoyees
- salaries-pass-iae, fiches-salaries-asp
- structure-presentation, metiers-recrutement
- collaborateurs, etc.

#### recherche (2 events)
Search functionality.

| Action | Name | Description |
|--------|------|-------------|
| clic | enregistrer-une-recherche | Saves search |
| clic | clic-sur-recherche-enregistree | Uses saved search |

### Dynamic Event Patterns

Several events use dynamic names constructed at runtime:

#### Category: `connexion {account_type}`
Built from `MATOMO_ACCOUNT_TYPE` enum in `itou/users/enums.py`:
- `connexion prescripteur` (44k events/month)
- `connexion employeur inclusif` (38k events/month)

Template: `{% matomo_event "connexion "|add:matomo_account_type "clic" "..." %}`

#### Name: `voir-liste-candidatures-{status}`
Dashboard links append status name:
- `voir-liste-candidatures-À traiter` (32k)
- `voir-liste-candidatures-En attente` (4k)
- `voir-liste-candidatures-Vivier`

Template: `{% matomo_event "employeurs" "clic" "voir-liste-candidatures-"|add:category.name %}`

#### Name: `candidature_{user_kind}`
Application submission appends user type:
- `candidature_prescripteur` (31k) - prescriber submitting for candidate
- `candidature_candidat` (7k) - job seeker submitting themselves

Template: `matomo_name="candidature_"|add:request.user.get_kind_display`

#### Multi-step wizard: `batch-refuse-application-{step}-submit`
Refuse wizard fires per step:
- `batch-refuse-application-reason-submit` (11k)
- `batch-refuse-application-job-seeker-answer-submit` (11k)
- `batch-refuse-application-prescriber-answer-submit` (9k)

Code: `matomo_event_name = f"batch-refuse-application-{self.step}-submit"`

### Additional Categories (from Matomo Dec 2025)

| Category | Events | Description |
|----------|--------|-------------|
| fiches-salarié | 8k | Employee record creation (ASP). Uses `création` event. |
| modale-nouveautes | 9k | News modal popup |
| compte-candidat | 4k | Job seeker account creation |
| nir-temporaire | 1k | Temporary NIR (social security) skip |
| partners | 2k | External partner links (Diagoriente) |
| telechargement-pdf | 241 | PDF downloads (PASS IAE) |
| employers | 696 | English variant (legacy?) |
| salarie | 94 | Singular variant (legacy?) |

### Notes

- French/English mix: `employeurs` vs `employers`, `salaries` vs `salarie`
- Accents preserved: `fiches-salarié`, `À traiter`, `création`
- Top events by volume: `clic-metiers` (83k), `se-connecter-avec-pro-connect` (83k), `start_application` (62k)
