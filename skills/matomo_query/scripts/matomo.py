"""
DEPRECATED: MatomoAPI has moved to lib.query.

Migration:
    # Old (deprecated)
    from skills.matomo_query.scripts.matomo import MatomoAPI

    # New (use this instead)
    from lib.query import MatomoAPI, execute_matomo_query, CallerType

The new location provides automatic query logging and conversation tracking.

Note: format_data_source is still available from the ui_mapping module:
    from skills.matomo_query.scripts.ui_mapping import format_data_source
"""

raise ImportError(
    "MatomoAPI has moved to lib.query.\n\n"
    "Replace:\n"
    "    from skills.matomo_query.scripts.matomo import MatomoAPI\n\n"
    "With:\n"
    "    from lib.query import MatomoAPI\n\n"
    "Or use the execute function:\n"
    "    from lib.query import execute_matomo_query, CallerType\n"
    "    result = execute_matomo_query(instance='inclusion', caller=CallerType.AGENT, method='VisitsSummary.get', params={...})\n\n"
    "For format_data_source, use:\n"
    "    from skills.matomo_query.scripts.ui_mapping import format_data_source\n"
)
