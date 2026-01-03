# Funnels Module (Premium)

Conversion funnel analysis - track how visitors progress through defined steps.

## Methods

```
Funnels.getMetrics(idSite, period, date, idFunnel = '', idGoal = '', segment = '')
Funnels.getFunnelFlow(idSite, period, date, idFunnel = '', idGoal = '', segment = '')
Funnels.getFunnelEntries(idSite, period, date, idFunnel, segment = '', step = '', expanded = '', idSubtable = '', flat = '')
Funnels.getFunnelExits(idSite, period, date, idFunnel, segment = '', step = '')
Funnels.getGoalFunnel(idSite, idGoal)
Funnels.getAllActivatedFunnelsForSite(idSite)
Funnels.hasAnyActivatedFunnelForSite(idSite)
Funnels.deleteGoalFunnel(idSite, idGoal)
Funnels.setGoalFunnel(idSite, idGoal, isActivated, steps)
Funnels.getAvailablePatternMatches()
Funnels.testUrlMatchesSteps(url, steps)
```

## Key Methods

### getMetrics
Returns funnel conversion metrics: entries, exits, conversion rate per step.

### getFunnelFlow
Visual funnel data showing progression between steps.

### getFunnelEntries / getFunnelExits
Which pages brought users into / took users out of each funnel step.

## Use Cases

1. **Registration flow**: Landing → Signup form → Confirmation → Dashboard
2. **Application process**: Job listing → Application start → Submission
3. **Checkout**: Cart → Shipping → Payment → Confirmation
