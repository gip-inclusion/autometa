# HeatmapSessionRecording Module (Premium)

Heatmaps visualize where users click, move, and scroll on pages. Session recordings capture actual user sessions for replay and analysis.

## Methods

### List & Configuration

```
HeatmapSessionRecording.getHeatmaps(idSite)
HeatmapSessionRecording.getHeatmap(idSite, idSiteHsr)
HeatmapSessionRecording.getSessionRecordings(idSite)
HeatmapSessionRecording.getSessionRecording(idSite, idSiteHsr)
```

### Analytics Retrieval

```
HeatmapSessionRecording.getRecordedHeatmap(idSite, idSiteHsr, period, date, heatmapType, deviceType, segment = '')
HeatmapSessionRecording.getRecordedHeatmapMetadata(idSite, idSiteHsr, period, date, segment = '')
HeatmapSessionRecording.getRecordedSessions(idSite, idSiteHsr, period, date, segment = '', filter_limit = '')
HeatmapSessionRecording.getRecordedSession(idSite, idSiteHsr, idLogHsr)
```

### Management (Write)

```
HeatmapSessionRecording.addHeatmap(idSite, name, matchPageRules, ...)
HeatmapSessionRecording.updateHeatmap(idSite, idSiteHsr, ...)
HeatmapSessionRecording.deleteHeatmap(idSite, idSiteHsr)
HeatmapSessionRecording.endHeatmap(idSite, idSiteHsr)

HeatmapSessionRecording.addSessionRecording(idSite, name, matchPageRules, ...)
HeatmapSessionRecording.updateSessionRecording(idSite, idSiteHsr, ...)
HeatmapSessionRecording.deleteSessionRecording(idSite, idSiteHsr)
HeatmapSessionRecording.endSessionRecording(idSite, idSiteHsr)
```

### Reference Data

```
HeatmapSessionRecording.getAvailableStatuses()
HeatmapSessionRecording.getAvailableDeviceTypes()
HeatmapSessionRecording.getAvailableHeatmapTypes()
HeatmapSessionRecording.getAvailableTargetPageRules()
```

## Key Concepts

### Heatmap Types

| Key | Name | Description |
|-----|------|-------------|
| 1 | Move | Mouse movement patterns |
| 2 | Click | Click positions and frequency |
| 3 | Scroll | Scroll depth and attention |

### Device Types

| Key | Name |
|-----|------|
| 1 | Desktop |
| 2 | Tablet |
| 3 | Mobile |

### Page Matching Rules

Heatmaps/recordings target pages using rules:

| Attribute | Description | Match Types |
|-----------|-------------|-------------|
| `url` | Full URL | equals_exactly, equals_simple, contains, starts_with, regexp |
| `path` | URL path only | equals_exactly, equals_simple, contains, starts_with, regexp |
| `urlparam` | Query parameter | exists, equals_exactly, contains, regexp |

Example rule:
```json
{
  "attribute": "url",
  "type": "contains",
  "value": "/apply/prescriptions/list",
  "inverted": "0"
}
```

## Tested and Working (2026-01-11)

### getHeatmaps - List All Heatmaps

```python
api = MatomoAPI()
heatmaps = api.request('HeatmapSessionRecording.getHeatmaps', idSite=117)
# Returns: list of heatmap configs with idsitehsr, name, match_page_rules, sample_rate, etc.
```

**Key fields:**
- `idsitehsr`: Internal ID (use for other calls)
- `name`: Human-readable name
- `sample_rate`: Percentage of visits sampled (e.g., "10.0")
- `sample_limit`: Max samples to collect
- `match_page_rules`: List of targeting rules
- `status`: "active" or "ended"

**Current heatmaps on Emplois (117):**
- ID 66: "Pages candidatures" (apply/prescriptions/list, prescriber/details)
- ID 65: "Pages candidats"
- ID 64: "GPS"

### getHeatmap - Single Heatmap Config

```python
heatmap = api.request('HeatmapSessionRecording.getHeatmap', idSite=117, idSiteHsr=66)
# Returns: full config including page_treemirror, screenshot_url, breakpoint_mobile
```

### getRecordedHeatmapMetadata - Sample Counts

```python
metadata = api.request('HeatmapSessionRecording.getRecordedHeatmapMetadata',
    idSite=117, idSiteHsr=66, period='month', date='2025-12-01')
# Returns: {'nb_samples_device_all': 0}  (or sample counts by device type)
```

### getRecordedHeatmap - Heatmap Data Points

```python
data = api.request('HeatmapSessionRecording.getRecordedHeatmap',
    idSite=117, idSiteHsr=66,
    period='month', date='2025-12-01',
    heatmapType=2,  # 1=Move, 2=Click, 3=Scroll
    deviceType=1    # 1=Desktop, 2=Tablet, 3=Mobile
)
# Returns: list of coordinate data for rendering heatmap visualization
```

### getSessionRecordings - List All Recordings

```python
recordings = api.request('HeatmapSessionRecording.getSessionRecordings', idSite=214)
# Returns: list of recording configs
```

**Key fields (session recordings):**
- `idsitehsr`: Internal ID
- `name`: Human-readable name
- `min_session_time`: Minimum session duration to record (seconds)
- `requires_activity`: Only record if user is active
- `capture_keystrokes`: Whether to capture keyboard input
- `status`: "active" or "ended"
- `created_date`, `updated_date`: Timestamps

### getRecordedSessions - List Captured Sessions

```python
sessions = api.request('HeatmapSessionRecording.getRecordedSessions',
    idSite=214, idSiteHsr=55, period='month', date='2025-01-01')
# Returns: list of individual recorded sessions
```

**Key fields per session:**
- `idloghsr`: Session log ID (use to replay)
- `idvisit`: Visit ID
- `idvisitor`: Visitor ID
- `first_url`, `last_url`: Entry and exit URLs
- `time_on_site`: Duration in milliseconds
- `nb_pageviews`: Number of pages viewed
- `server_time`: Session timestamp
- `location_*`: Geolocation (country, region, city)
- `config_*`: Device info (OS, browser, device type)
- `sessionReplayUrl`: URL to watch the replay

### getRecordedSession - Full Session Replay Data

```python
session = api.request('HeatmapSessionRecording.getRecordedSession',
    idSite=214, idSiteHsr=55, idLogHsr=41112)
# Returns: full session data including events array for replay
```

**Warning:** Response can be very large (several MB). The `events` array contains
all mouse movements, clicks, scrolls, and DOM mutations for replay.

**Key fields:**
- `url`: Page URL
- `viewport_w_px`, `viewport_h_px`: Browser viewport size
- `scroll_y_max_relative`: Maximum scroll depth
- `time_on_page`: Duration in milliseconds
- `events`: Array of recorded interactions (can be 1000+ items)
- `pageviews`: Array of pages visited during session
- `numPageviews`: Total page count

## Sites with Active Heatmaps/Recordings

| Site | ID | Heatmaps | Session Recordings |
|------|-----|----------|-------------------|
| Emplois | 117 | 3 | 0 |
| Dora | 211 | 3 | 0 |
| RDV-Insertion | 214 | 4 | 2 |
| Mon Recap | 217 | 1 | 0 |
| Emplois (Recette) | 220 | 1 | 1 |

## Use Cases

### 1. Identify Click Targets
Analyze click heatmaps to see which buttons/links users actually click vs. which they ignore.

### 2. Scroll Depth Analysis
Use scroll heatmaps to determine how far users scroll on long pages. Place important CTAs above the fold.

### 3. Form Abandonment Investigation
Watch session recordings of users who abandoned forms to identify UX issues.

### 4. Mobile vs Desktop Comparison
Compare heatmaps by device type to ensure responsive design works for all users.

### 5. A/B Test Validation
Combine with A/B testing to visually verify that users interact with new designs as expected.

## Caveats

**Sample limits:** Heatmaps have `sample_limit` caps (default 1000). Once reached, no new data is collected until the heatmap is reset or ended.

**Privacy:** Session recordings may capture sensitive data. `capture_keystrokes: false` is recommended for privacy compliance.

**Response sizes:** `getRecordedSession` returns large payloads (several MB per session). Query with care.

**Status matters:** Only "active" heatmaps/recordings collect data. Check `status` field.
