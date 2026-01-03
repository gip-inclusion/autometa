# Cohorts Module (Premium)

Cohort analysis groups visitors by their first visit date and tracks behavior over subsequent periods.

## Methods

```
Cohorts.getCohorts(idSite, period, date, metric = '', segment = '', filter_limit = '')
Cohorts.getCohortsOverTime(idSite, period, displayDateRange, cohorts, segment = '', filter_limit = '')
Cohorts.getByPeriodOfFirstVisit(idSite, cohorts, period, segment = '', periodsFromStart = '')
```

## How It Works

A **cohort** = visitors whose first visit was within a specific period.

**Archiving:** Records aggregate metrics by the day of first visit. For non-day periods, daily records are summed.

**API transformation:** Records (by first day of visit) are transformed to reports (by period of first visit). Rows with the same period label are grouped together.

## Parameters

- `cohorts` - Cohort specification (format TBD - needs testing when endpoint is up)
- `displayDateRange` - Date range for the cohorts over time report
- `periodsFromStart` - Number of periods from cohort start to include
- `metric` - Specific metric to return

## Use Cases

1. **Retention analysis**: How many users from month X are still active in month X+1, X+2, etc.?
2. **Feature adoption**: Did users who joined after feature launch behave differently?
3. **Seasonal comparison**: Compare cohorts from different seasons/years.
