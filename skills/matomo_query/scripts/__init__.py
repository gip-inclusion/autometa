"""Matomo API utilities.

DEPRECATED: Import from lib.query instead:
    from lib.query import MatomoAPI, MatomoError
"""
from lib.query import MatomoAPI, MatomoError
from lib.sources import get_matomo as load_api

__all__ = ["MatomoAPI", "MatomoError", "load_api"]
