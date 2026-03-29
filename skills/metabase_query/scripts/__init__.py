"""Metabase query scripts.

DEPRECATED: Import from lib.query instead:
    from lib.query import MetabaseAPI, MetabaseError
"""
from lib.query import MetabaseAPI, MetabaseError
from lib.metabase import QueryResult
from lib.sources import get_metabase as load_api
from .cards_db import CardsDB, Card, Dashboard, load_cards_db, TOPICS

__all__ = [
    "MetabaseAPI",
    "MetabaseError",
    "QueryResult",
    "load_api",
    "CardsDB",
    "Card",
    "Dashboard",
    "load_cards_db",
    "TOPICS",
]
