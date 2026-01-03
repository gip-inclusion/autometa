# Cohorts Module (Premium)

Cohort analysis groups visitors by their first visit date and tracks behavior over subsequent periods.

## Methods

```
Cohorts.getCohorts(idSite, period, date, metric = '', segment = '', filter_limit = '')
Cohorts.getCohortsOverTime(idSite, period, displayDateRange, cohorts, segment = '', filter_limit = '')
Cohorts.getByPeriodOfFirstVisit(idSite, cohorts, period, segment = '', periodsFromStart = '')
```

## Tested and Working (2026-01-03)

### getCohorts - Basic Retention

Returns data keyed by cohort start date. Each date has an array of cohorts labeled `Cohorts_month0`, `Cohorts_month1`, etc.

```python
api.get_cohorts(site_id=117, period='month', date='2025-10-01', limit=20)
# Returns: {'2025-10-01': [{'label': 'Cohorts_month0', 'nb_visits': 213688, ...}, ...]}
```

**Key fields:**
- `label`: `Cohorts_monthN` where N = months since first visit
- `nb_uniq_visitors`: unique visitors in this cohort still active
- `Cohorts_returning_visitors_percent`: retention rate (e.g., "9.2%")
- `goal_N_nb_conversions`: goal conversions for this cohort

**Example retention (October 2025 cohort on les Emplois):**
- Month 0: 149,085 unique visitors (100%)
- Month 1: 13,715 returning (9.2%)
- Month 2: 6,402 returning (4.3%)

### getCohortsOverTime - Time Series

Shows cohort metrics across a date range.

```python
api._request('Cohorts.getCohortsOverTime', {
    'idSite': 117,
    'period': 'month',
    'displayDateRange': '2025-10-01,2025-12-31',
    'cohorts': '2025-10-01,2025-11-01',
})
# Returns: {'2025-10': [...], '2025-11': [...], '2025-12': [...]}
```

### getByPeriodOfFirstVisit - Grouped by Display Period

Returns data keyed by the display period, with cohort data nested inside.

```python
api._request('Cohorts.getByPeriodOfFirstVisit', {
    'idSite': 117,
    'period': 'month',
    'cohorts': '2025-10-01,2025-11-01',
})
```

## Parameters

- `cohorts` - Comma-separated dates: `'2025-10-01,2025-11-01'`
- `displayDateRange` - Date range: `'2025-10-01,2025-12-31'`
- `periodsFromStart` - Number of periods from cohort start to include
- `metric` - Specific metric to return

## Caveats

**⚠️ Segments cause timeouts.** Cohort queries are heavy. Adding a segment like
`pageUrl=@/gps/` will likely cause HTTP 504 Gateway Timeout errors. Query cohorts
without segments for best results.

**Long-term data.** Old cohorts (e.g., from 2021) still appear in results,
showing visitors who have been returning for years.

## Use Cases

1. **Retention analysis**: How many users from month X are still active in month X+1, X+2, etc.?
2. **Feature adoption**: Did users who joined after feature launch behave differently?
3. **Seasonal comparison**: Compare cohorts from different seasons/years.
