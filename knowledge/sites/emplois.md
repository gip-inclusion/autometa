# Emplois

- URL: https://emplois.inclusion.beta.gouv.fr
- Matomo site ID: 117
- GitHub: https://github.com/gip-inclusion/les-emplois

## Traffic Baselines (2025)

Data retrieved 2026-01-03 via Matomo API.

### Monthly Visitor Stats

| Month   | Unique Visitors | Visits    | Daily Avg Visitors | Daily Avg Visits |
|---------|-----------------|-----------|--------------------|-----------------:|
| 2025-01 | 189,083         | 460,201   | 6,099              | 14,845           |
| 2025-02 | 177,970         | 434,333   | 6,356              | 15,512           |
| 2025-03 | 188,675         | 466,830   | 6,086              | 15,059           |
| 2025-04 | 187,006         | 447,922   | 6,234              | 14,931           |
| 2025-05 | 165,132         | 391,514   | 5,327              | 12,629           |
| 2025-06 | 175,318         | 425,531   | 5,844              | 14,184           |
| 2025-07 | 169,339         | 424,698   | 5,463              | 13,700           |
| 2025-08 | 155,529         | 339,390   | 5,017              | 10,948           |
| 2025-09 | 219,810         | 526,170   | 7,327              | 17,539           |
| 2025-10 | 221,726         | 545,370   | 7,152              | 17,593           |
| 2025-11 | 189,674         | 452,497   | 6,322              | 15,083           |
| 2025-12 | 167,571         | 398,250   | 5,406              | 12,847           |

**Typical range:** 5,000-7,500 unique visitors/day, 11,000-17,500 visits/day.

**Seasonal patterns:**
- Peak: September-October (rentrée)
- Low: August (summer holidays), May (bridge holidays), December (year-end)

### User Type Distribution (visits)

| Month   | prescriber | employer  | job_seeker | anonymous  | labor_inspector | itou_staff |
|---------|------------|-----------|------------|------------|-----------------|------------|
| 2025-01 | 63,710     | 91,138    | 24,197     | 280,748    | 245             | 160        |
| 2025-02 | 58,804     | 87,988    | 22,849     | 264,333    | 272             | 87         |
| 2025-03 | 60,539     | 96,849    | 25,378     | 283,548    | 367             | 139        |
| 2025-04 | 59,798     | 90,260    | 25,075     | 272,379    | 267             | 134        |
| 2025-05 | 49,333     | 79,116    | 22,347     | 240,363    | 199             | 115        |
| 2025-06 | 57,417     | 87,870    | 21,972     | 257,911    | 235             | 123        |
| 2025-07 | 59,983     | 89,411    | 21,503     | 253,321    | 359             | 119        |
| 2025-08 | 42,829     | 63,929    | 18,365     | 213,971    | 218             | 77         |
| 2025-09 | 68,947     | 102,636   | 27,321     | 326,291    | 815             | 141        |
| 2025-10 | 73,892     | 102,533   | 30,760     | 337,149    | 604             | 152        |
| 2025-11 | 61,538     | 82,199    | 26,756     | 281,392    | 427             | 173        |
| 2025-12 | 56,347     | 74,509    | 22,111     | 244,814    | 362             | 107        |

### User Type Proportions (baseline)

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

This baseline is essential for comparing feature-specific usage. For example, if a feature shows prescribers > employers, that feature is disproportionately used by prescribers relative to the site average.

## Custom Dimensions

| ID | Index | Scope  | Name                 | Notes                           |
|----|-------|--------|----------------------|---------------------------------|
| 1  | 1     | visit  | UserKind             | prescriber, employer, job_seeker, anonymous, labor_inspector, itou_staff |
| 2  | 2     | visit  | Unused               | Inactive                        |
| 3  | 1     | action | UserOrganizationKind | FT, ACI, AI, ML, EI, ETTI, etc. |
| 4  | 2     | action | UserDepartment       | French département number (01-976) |

Query visit-scoped dimensions with `idDimension=1`.
Query action-scoped dimensions with `idDimension=3` (org) or `idDimension=4` (dept).
