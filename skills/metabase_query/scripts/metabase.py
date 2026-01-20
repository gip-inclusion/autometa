"""
DEPRECATED: MetabaseAPI has moved to lib.query.

Migration:
    # Old (deprecated)
    from skills.metabase_query.scripts.metabase import MetabaseAPI

    # New (use this instead)
    from lib.query import MetabaseAPI, execute_metabase_query, CallerType

The new location provides automatic query logging and conversation tracking.
"""

raise ImportError(
    "MetabaseAPI has moved to lib.query.\n\n"
    "Replace:\n"
    "    from skills.metabase_query.scripts.metabase import MetabaseAPI\n\n"
    "With:\n"
    "    from lib.query import MetabaseAPI\n\n"
    "Or use the execute function:\n"
    "    from lib.query import execute_metabase_query, CallerType\n"
    "    result = execute_metabase_query(instance='stats', caller=CallerType.AGENT, sql='...', database_id=2)\n"
)
