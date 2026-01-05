# RDV-Insertion

- URL: https://www.rdv-insertion.fr
- Matomo site ID: 214
- GitHub: https://github.com/gip-inclusion/rdv-insertion

## Traffic Baselines (2025)

Data retrieved 2026-01-03 via Matomo API.

### Monthly Visitor Stats

| Month   | Unique Visitors | Visits  | Daily Avg Visitors | Daily Avg Visits |
|---------|-----------------|---------|--------------------|-----------------:|
| 2025-01 | 3,962           | 14,648  | 128                | 473              |
| 2025-02 | 3,563           | 13,617  | 127                | 486              |
| 2025-03 | 4,013           | 15,739  | 129                | 508              |
| 2025-04 | 3,874           | 14,954  | 129                | 498              |
| 2025-05 | 2,556           | 8,851   | 82                 | 285              |
| 2025-06 | 4               | 5       | <1                 | <1               |
| 2025-07 | 2,542           | 11,264  | 82                 | 363              |
| 2025-08 | 820             | 6,499   | 26                 | 210              |
| 2025-09 | 1,043           | 8,738   | 35                 | 291              |
| 2025-10 | 980             | 8,979   | 32                 | 290              |
| 2025-11 | 877             | 8,091   | 29                 | 270              |
| 2025-12 | 914             | 7,597   | 29                 | 245              |

**Note:** June 2025 data appears anomalous (likely tracking issue). Late 2025 shows reduced unique visitors but consistent visit counts, suggesting higher engagement per user.

**Typical range:** 25-130 unique visitors/day, 200-500 visits/day.

**Engagement metrics:** High actions per visit (20-28) and average time on site (12-16 minutes) indicate professional users deeply engaged with the platform.

**Seasonal patterns:**
- Peak: January-April (normal operations)
- Drop: May-August (tracking issues and summer holidays)
- Stable: September-December (normalized at lower unique visitor count)

## Custom Dimensions

No custom dimensions configured for this site.

## Matomo Events

Data retrieved 2026-01-03 from both Matomo API and GitHub codebase analysis.

### Implementation

RDV-Insertion uses Matomo Tag Manager (MTM) for event tracking, not the standard Matomo JS tracker.

- **Tag Manager Container:** Loaded via `MATOMO_CONTAINER_ID` environment variable
- **Controller:** `app/javascript/controllers/matomo_script_tag_controller.js` - initializes MTM
- **Tracking consent:** Only enabled for logged-in agents who have accepted tracking (`tracking_accepted?`)
- **URL anonymization:** Route patterns replace IDs (e.g., `/organisations/:id/users` instead of `/organisations/123/users`)
- **Event binding:** Uses HTML element IDs prefixed with `rdvi_` or standard button IDs

### Event Actions (Dec 2025)

Most events use the page URL as category and an action identifier. Top events by volume:

| Action | Events | Description |
|--------|--------|-------------|
| Chargement du fichier | 46,991 | File upload processing (Upload category) |
| confirm-button | 2,697 | Confirmation modal clicks |
| archive-button | 2,392 | Archive user clicks |
| rdvi_header_organisation-nav | 2,519 | Organisation navigation dropdown |
| toggle-rdv-status | 2,208 | Toggle appointment status |
| rdvi_index-nav_filter-status-button | 1,492 | Status filter button |
| rdvi_index-nav_create-one-user | 702 | Create single user button |
| rdvi_index-nav_filter-referent-button | 637 | Referent filter button |
| Vues | 336 | Page Configuration views |

### Event Categories

Events are categorized primarily by page URL pattern:

| Category Pattern | Description |
|------------------|-------------|
| `Upload` | File upload processing events |
| `Page Configuration` | Configuration page views |
| `/organisations/{id}/users` | Organisation user list actions |
| `/departments/{id}/users` | Department user list actions |
| `Others` | Uncategorized events |

### UI Element Events (rdvi_ prefix)

Events tracked via HTML element IDs in ERB templates:

#### Header Navigation
- `rdvi_header_organisation-nav` - Organisation switcher dropdown
- `rdvi_header_help-center` - Help menu button
- `rdvi_header_log-out` - Logout link
- `rdvi_header_redirection` - Logo/home link

#### User List Actions
- `rdvi_index-nav_filter-status-button` - Status filter dropdown
- `rdvi_index-nav_filter-referent-button` - Referent filter dropdown
- `rdvi_index-nav_filter-tags-button` - Tags filter dropdown
- `rdvi_index-nav_filter-orientation-type-button` - Orientation type filter
- `rdvi_index-nav_filter-creation-date` - Creation date filter
- `rdvi_index-nav_create-one-user` - Create single user button
- `rdvi_index-nav_upload-users` - Upload users button
- `rdvi_index-nav_redirect-rdvs` - RDV-Solidarites link
- `csvExportButton` - CSV export dropdown

#### Upload Workflow (file selection)
- `rdvi_upload_select-category_validate` - Validate category selection
- `rdvi_upload_select-category_back` - Back from category selection
- `rdvi_upload_select-file_file-choice` - File picker label
- `rdvi_upload_select-file_validate` - Validate file selection
- `rdvi_upload_select-file_delete` - Remove selected file
- `rdvi_upload_select-file_change-file` - Change selected file
- `rdvi_upload_select-file_back` - Back from file selection
- `rdvi_upload_select-file_drag-drop` - Drag-and-drop file (JS)

#### Upload Workflow (user data)
- `rdvi_upload_users-data_all-select` - Select all users checkbox
- `rdvi_upload_users-data_user-select-{id}` - Select individual user
- `rdvi_upload_users-data_create-folder` - Create/update folders button
- `rdvi_upload_users-data_pass-invit` - Skip to invitations
- `rdvi_upload_users-data_end-course` - End workflow
- `rdvi_upload_users-data_all-data-user` - View all users tab
- `rdvi_upload_users-data_data-user-error` - View error users tab
- `rdvi_upload_users-data_folder-error` - Folder error tab
- `rdvi_upload_users-data_data-complete` - Complete data with CNAF
- `rdvi_upload_users-data_open-folder-user-{id}` - Open user folder
- `rdvi_upload_users-data_return` - Return to previous step
- Sort buttons: `*_first-name_sort`, `*_last-name_sort`, `*_folder-statut_sort`

#### Upload Workflow (invitations)
- `rdvi_upload_users-invit_send-invit` - Send invitations button
- `rdvi_upload_users-invit_all-select` - Select all for invitation
- `rdvi_upload_users-invit_user-select-{id}` - Select user for invitation
- `rdvi_upload_users-invit_user-download-{id}` - Download invitation
- `rdvi_upload_users-invit_end` - Finish workflow
- `rdvi_upload_users-invit_all-folder` - All folders tab
- `rdvi_upload_users-invit_folder-error` - Error folders tab
- Status/alert elements: `*_success-alert`, `*_warning-alert`, `*_statut-tag-error-{id}`

#### Footer Links
- `rdvi_footer_help-center` - Guide link
- `rdvi_footer_stats-link` - Statistics page
- `rdvi_footer_rdvs-redirection` - RDV-Solidarites link
- `rdvi_footer_pdi-redirection` - Plateforme de l'inclusion link
- `rdvi_footer_legal-notice-link` - Legal notice
- `rdvi_footer_CGU-link` - Terms of service
- `rdvi_footer_DPA-link` - Data processing agreement
- `rdvi_footer_privacy-link` - Privacy policy
- `rdvi_footer_accessibility-link` - Accessibility statement
- `rdvi_footer_cookies-link` - Cookie settings

### Core Button Events

Standard button IDs tracked via MTM (not rdvi_ prefixed):

| ID | Description | Volume (Dec 2025) |
|----|-------------|-------------------|
| `confirm-button` | Confirmation modal confirm | 2,697 |
| `archive-button` | Archive user action | 2,392 |
| `toggle-rdv-status` | Change appointment status | 2,208 |
| `csvExportButton` | Export users to CSV | 296 |
| `btn-notification-center` | Notification center | 32 |
| `dora-link-index` | Dora service link (index) | 27 |
| `dora-link-user-loc` | Dora service link (user with location) | 19 |

### Special Events

#### Upload Progress Event
Category: `Upload`
Action: `Chargement du fichier`
Name: `Upload - resultat ok`
Description: Fired when file upload/processing completes successfully. Highest volume event (47k/month).

#### Page Configuration Views
Category: `Page Configuration`
Action: `Vues`
Name: `Page Vue Configuration`
Description: Configuration page view tracking.

### Notes

- Events use French labels (e.g., "Chargement du fichier" = "File loading")
- Page URL is used as event category, creating many unique category values per organisation/department
- Event names often include `Clic sur *******` with masked values
- The `_mtm` array is used instead of `_paq` for Matomo Tag Manager
- Tracking requires agent login and consent
