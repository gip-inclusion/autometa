"""
Matomo API client for cyberputois.

Usage:
    from scripts.matomo import MatomoAPI

    api = MatomoAPI()  # loads from .env
    summary = api.get_visits(site_id=117, period="month", date="2025-12-01")
"""

import os
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any, Optional


class MatomoAPI:
    """Client for querying the Matomo API."""

    def __init__(self, url: Optional[str] = None, token: Optional[str] = None):
        """
        Initialize the API client.

        If url/token not provided, loads from .env file in project root.
        """
        if url and token:
            self.url = url
            self.token = token
        else:
            self._load_env()

    def _load_env(self):
        """Load credentials from .env file."""
        env_path = Path(__file__).parent.parent.parent.parent / ".env"
        if not env_path.exists():
            raise FileNotFoundError(f".env file not found at {env_path}")

        env = {}
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()

        self.url = env.get("MATOMO_URL")
        self.token = env.get("MATOMO_API_KEY")

        if not self.url or not self.token:
            raise ValueError("MATOMO_URL and MATOMO_API_KEY must be set in .env")

    def _request(self, method: str, params: dict, timeout: int = 180) -> Any:
        """Make an API request."""
        base_params = {
            "module": "API",
            "method": method,
            "format": "JSON",
            "token_auth": self.token,
        }
        base_params.update(params)

        query = urllib.parse.urlencode(base_params)
        url = f"https://{self.url}/?{query}"

        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                data = json.loads(response.read().decode())

                # Check for API errors
                if isinstance(data, dict) and data.get("result") == "error":
                    raise MatomoError(data.get("message", "Unknown error"))

                return data
        except urllib.error.URLError as e:
            raise MatomoError(f"Request failed: {e}")

    def get_api_url(self, method: str, params: dict) -> str:
        """
        Get the full API URL for a request (for documentation purposes).
        Token is redacted.
        """
        base_params = {
            "module": "API",
            "method": method,
            "format": "JSON",
            "token_auth": "[REDACTED]",
        }
        base_params.update(params)
        query = urllib.parse.urlencode(base_params)
        return f"https://{self.url}/?{query}"

    # --- High-level methods ---

    def get_sites(self) -> list[dict]:
        """Get all sites the API key has access to."""
        return self._request("SitesManager.getSitesWithAtLeastViewAccess", {})

    def get_visits(
        self,
        site_id: int,
        period: str,
        date: str,
        segment: Optional[str] = None,
    ) -> dict:
        """
        Get visit summary for a site.

        Args:
            site_id: Matomo site ID
            period: day, week, month, or year
            date: today, yesterday, YYYY-MM-DD, or lastN
            segment: Optional segment filter (e.g., "pageUrl=@/gps/")

        Returns:
            Dict with nb_uniq_visitors, nb_visits, nb_actions, etc.
        """
        params = {"idSite": site_id, "period": period, "date": date}
        if segment:
            params["segment"] = segment
        return self._request("VisitsSummary.get", params)

    def get_unique_visitors(
        self,
        site_id: int,
        period: str,
        date: str,
        segment: Optional[str] = None,
    ) -> int:
        """Get unique visitor count."""
        params = {"idSite": site_id, "period": period, "date": date}
        if segment:
            params["segment"] = segment
        result = self._request("VisitsSummary.getUniqueVisitors", params)
        return result.get("value", 0)

    def get_pages(
        self,
        site_id: int,
        period: str,
        date: str,
        pattern: Optional[str] = None,
        segment: Optional[str] = None,
        flat: bool = True,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get page URL statistics.

        Args:
            site_id: Matomo site ID
            period: day, week, month, or year
            date: today, yesterday, YYYY-MM-DD, or lastN
            pattern: Filter URLs containing this pattern
            segment: Optional segment filter
            flat: Flatten hierarchical results
            limit: Max rows to return

        Returns:
            List of dicts with label (URL), nb_visits, nb_hits, etc.
        """
        params = {
            "idSite": site_id,
            "period": period,
            "date": date,
            "filter_limit": limit,
        }
        if pattern:
            params["filter_pattern"] = pattern
        if segment:
            params["segment"] = segment
        if flat:
            params["flat"] = 1
        return self._request("Actions.getPageUrls", params)

    def get_configured_dimensions(self, site_id: int) -> list[dict]:
        """
        Get custom dimensions configured for a site.

        Returns list of dicts with:
            - idcustomdimension: internal ID
            - index: dimension index (use this for queries)
            - scope: "visit" or "action"
            - name: human-readable name
            - active: bool
        """
        return self._request(
            "CustomDimensions.getConfiguredCustomDimensions",
            {"idSite": site_id}
        )

    def get_dimension(
        self,
        site_id: int,
        dimension_id: int,
        period: str,
        date: str,
        segment: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get breakdown by custom dimension.

        Args:
            site_id: Matomo site ID
            dimension_id: The dimension index (or idcustomdimension for action-scoped)
            period: day, week, month, or year
            date: today, yesterday, YYYY-MM-DD, or lastN
            segment: Optional segment filter
            limit: Max rows to return

        Returns:
            List of dicts with label, nb_visits, nb_actions, etc.
        """
        params = {
            "idSite": site_id,
            "idDimension": dimension_id,
            "period": period,
            "date": date,
            "filter_limit": limit,
        }
        if segment:
            params["segment"] = segment
        return self._request("CustomDimensions.getCustomDimension", params)

    def get_dimension_by_week(
        self,
        site_id: int,
        dimension_id: int,
        year: int,
        month: int,
        segment: Optional[str] = None,
        limit: int = 100,
    ) -> dict[str, list[dict]]:
        """
        Get dimension breakdown for each week in a month.

        Useful for avoiding timeouts on large queries.

        Returns:
            Dict keyed by week start date, values are dimension breakdowns.
        """
        from datetime import date, timedelta

        # Get first day of month
        start = date(year, month, 1)

        # Get last day of month
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)

        results = {}
        current = start

        while current <= end:
            week_str = current.isoformat()
            try:
                data = self.get_dimension(
                    site_id=site_id,
                    dimension_id=dimension_id,
                    period="week",
                    date=week_str,
                    segment=segment,
                    limit=limit,
                )
                results[week_str] = data
            except MatomoError as e:
                results[week_str] = {"error": str(e)}

            current += timedelta(days=7)

        return results

    # --- Events ---

    def get_event_categories(
        self,
        site_id: int,
        period: str,
        date: str,
        segment: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get event categories with counts.

        Returns list of dicts with label (category name), nb_events, nb_visits, etc.
        """
        params = {
            "idSite": site_id,
            "period": period,
            "date": date,
            "filter_limit": limit,
        }
        if segment:
            params["segment"] = segment
        return self._request("Events.getCategory", params)

    def get_event_actions(
        self,
        site_id: int,
        period: str,
        date: str,
        segment: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get event actions with counts.

        Returns list of dicts with label (action name), nb_events, nb_visits, etc.
        """
        params = {
            "idSite": site_id,
            "period": period,
            "date": date,
            "filter_limit": limit,
        }
        if segment:
            params["segment"] = segment
        return self._request("Events.getAction", params)

    def get_event_names(
        self,
        site_id: int,
        period: str,
        date: str,
        segment: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get event names with counts.

        Returns list of dicts with label (event name), nb_events, nb_visits, etc.
        """
        params = {
            "idSite": site_id,
            "period": period,
            "date": date,
            "filter_limit": limit,
        }
        if segment:
            params["segment"] = segment
        return self._request("Events.getName", params)

    # --- Entry/Exit pages ---

    def get_entry_pages(
        self,
        site_id: int,
        period: str,
        date: str,
        segment: Optional[str] = None,
        flat: bool = True,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get landing pages (first page of visits).

        Returns list of dicts with label (URL), entry_nb_visits, entry_bounce_count, etc.
        """
        params = {
            "idSite": site_id,
            "period": period,
            "date": date,
            "filter_limit": limit,
        }
        if segment:
            params["segment"] = segment
        if flat:
            params["flat"] = 1
        return self._request("Actions.getEntryPageUrls", params)

    def get_exit_pages(
        self,
        site_id: int,
        period: str,
        date: str,
        segment: Optional[str] = None,
        flat: bool = True,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get exit pages (last page of visits).

        Returns list of dicts with label (URL), exit_nb_visits, exit_rate, etc.
        """
        params = {
            "idSite": site_id,
            "period": period,
            "date": date,
            "filter_limit": limit,
        }
        if segment:
            params["segment"] = segment
        if flat:
            params["flat"] = 1
        return self._request("Actions.getExitPageUrls", params)

    # --- Transitions (page flow) ---

    def get_transitions(
        self,
        site_id: int,
        period: str,
        date: str,
        page_url: str,
        segment: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        """
        Get page flow: what pages users visited before and after a specific URL.

        Args:
            page_url: The page URL to analyze (e.g., "/gps/groups/list")

        Returns:
            Dict with:
            - previousPages: list of pages visited before
            - followingPages: list of pages visited after
            - referrers: external sources leading to this page
            - outlinks: external links clicked from this page
        """
        params = {
            "idSite": site_id,
            "period": period,
            "date": date,
            "actionType": "url",
            "actionName": page_url,
            "limitBeforeGrouping": limit,
        }
        if segment:
            params["segment"] = segment
        return self._request("Transitions.getTransitionsForAction", params)

    # --- Visit time patterns ---

    def get_visits_by_hour(
        self,
        site_id: int,
        period: str,
        date: str,
        segment: Optional[str] = None,
    ) -> list[dict]:
        """
        Get visit distribution by hour of day (server time).

        Returns list of 24 dicts (one per hour) with nb_visits, nb_uniq_visitors, etc.
        """
        params = {"idSite": site_id, "period": period, "date": date}
        if segment:
            params["segment"] = segment
        return self._request("VisitTime.getVisitInformationPerServerTime", params)

    def get_visits_by_day_of_week(
        self,
        site_id: int,
        period: str,
        date: str,
        segment: Optional[str] = None,
    ) -> list[dict]:
        """
        Get visit distribution by day of week.

        Returns list of 7 dicts (Monday=1 to Sunday=7) with nb_visits, etc.
        """
        params = {"idSite": site_id, "period": period, "date": date}
        if segment:
            params["segment"] = segment
        return self._request("VisitTime.getByDayOfWeek", params)

    # --- Referrers ---

    def get_referrers(
        self,
        site_id: int,
        period: str,
        date: str,
        segment: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get all referrer types with visit counts.

        Returns list of dicts with label (referrer type), nb_visits, nb_actions, etc.
        Types include: Direct Entry, Search Engines, Websites, Social Networks, Campaigns.
        """
        params = {
            "idSite": site_id,
            "period": period,
            "date": date,
            "filter_limit": limit,
        }
        if segment:
            params["segment"] = segment
        return self._request("Referrers.getReferrerType", params)

    def get_referrer_websites(
        self,
        site_id: int,
        period: str,
        date: str,
        segment: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get referring websites with visit counts.

        Returns list of dicts with label (website URL), nb_visits, nb_actions, etc.
        """
        params = {
            "idSite": site_id,
            "period": period,
            "date": date,
            "filter_limit": limit,
        }
        if segment:
            params["segment"] = segment
        return self._request("Referrers.getWebsites", params)

    def get_referrer_search_engines(
        self,
        site_id: int,
        period: str,
        date: str,
        segment: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get search engines with visit counts.

        Returns list of dicts with label (search engine name), nb_visits, etc.
        """
        params = {
            "idSite": site_id,
            "period": period,
            "date": date,
            "filter_limit": limit,
        }
        if segment:
            params["segment"] = segment
        return self._request("Referrers.getSearchEngines", params)

    def get_referrer_socials(
        self,
        site_id: int,
        period: str,
        date: str,
        segment: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get social networks with visit counts.

        Returns list of dicts with label (social network name), nb_visits, etc.
        """
        params = {
            "idSite": site_id,
            "period": period,
            "date": date,
            "filter_limit": limit,
        }
        if segment:
            params["segment"] = segment
        return self._request("Referrers.getSocials", params)


class MatomoError(Exception):
    """Error from Matomo API."""
    pass


# --- Web UI URL generation ---

# Mapping from API methods to web UI category/subcategory
# Discovered via API.getWidgetMetadata - these are the actual Matomo IDs
_UI_MAPPING = {
    # Visitors
    "VisitsSummary.get": ("General_Visitors", "General_Overview"),
    "VisitsSummary.getUniqueVisitors": ("General_Visitors", "General_Overview"),
    # Actions - Pages
    "Actions.getPageUrls": ("General_Actions", "General_Pages"),
    "Actions.getPageTitles": ("General_Actions", "Actions_SubmenuPageTitles"),
    "Actions.getEntryPageUrls": ("General_Actions", "Actions_SubmenuPagesEntry"),
    "Actions.getExitPageUrls": ("General_Actions", "Actions_SubmenuPagesExit"),
    # Custom dimensions - subcategory is "customdimension{N}" where N is dimension ID
    "CustomDimensions.getCustomDimension": ("General_Visitors", None),  # subcategory = f"customdimension{id}"
    # Events
    "Events.getCategory": ("General_Actions", "Events_Events"),
    "Events.getAction": ("General_Actions", "Events_Events"),
    "Events.getName": ("General_Actions", "Events_Events"),
    # Referrers
    "Referrers.getReferrerType": ("Referrers_Referrers", "Referrers_WidgetGetAll"),
    "Referrers.getWebsites": ("Referrers_Referrers", "Referrers_SubmenuWebsitesOnly"),
    "Referrers.getSearchEngines": ("Referrers_Referrers", "Referrers_SubmenuSearchEngines"),
    "Referrers.getSocials": ("Referrers_Referrers", "Referrers_Socials"),
    "Referrers.getAll": ("Referrers_Referrers", "Referrers_WidgetGetAll"),
    # Visit time
    "VisitTime.getVisitInformationPerServerTime": ("General_Visitors", "VisitTime_SubmenuTimes"),
    "VisitTime.getByDayOfWeek": ("General_Visitors", "VisitTime_SubmenuTimes"),
    # Transitions
    "Transitions.getTransitionsForAction": ("General_Actions", "Transitions_Transitions"),
    # Devices & Location
    "DevicesDetection.getType": ("General_Visitors", "DevicesDetection_Devices"),
    "DevicesDetection.getBrowsers": ("General_Visitors", "DevicesDetection_Software"),
    "UserCountry.getCountry": ("General_Visitors", "UserCountry_SubmenuLocations"),
    "UserCountry.getRegion": ("General_Visitors", "UserCountry_SubmenuLocations"),
    "UserCountry.getCity": ("General_Visitors", "UserCountry_SubmenuLocations"),
    # Engagement
    "VisitorInterest.getNumberOfVisitsPerVisitDuration": ("General_Actions", "VisitorInterest_Engagement"),
    "VisitorInterest.getNumberOfVisitsPerPage": ("General_Actions", "VisitorInterest_Engagement"),
}


def get_ui_url(
    base_url: str,
    method: str,
    site_id: int,
    period: str,
    date: str,
    segment: Optional[str] = None,
    dimension_id: Optional[int] = None,
) -> str:
    """
    Generate a Matomo web UI URL for a given API method.

    Args:
        base_url: Matomo instance URL (e.g., "matomo.inclusion.beta.gouv.fr")
        method: API method name (e.g., "VisitsSummary.get")
        site_id: Matomo site ID
        period: day, week, month, or year
        date: YYYY-MM-DD format
        segment: Optional segment filter
        dimension_id: Required for CustomDimensions methods

    Returns:
        Full URL to the Matomo web UI with the appropriate view.
    """
    mapping = _UI_MAPPING.get(method)
    if not mapping:
        # Fallback to dashboard
        category, subcategory = "Dashboard_Dashboard", "1"
    else:
        category, subcategory = mapping
        if subcategory is None and dimension_id is not None:
            # Custom dimensions use "customdimension{N}" format
            subcategory = f"customdimension{dimension_id}"

    # Build the hash fragment with category/subcategory
    hash_params = {
        "category": category,
        "subcategory": subcategory or "1",
    }
    if segment:
        hash_params["segment"] = segment

    # Use safe='@=;' to avoid over-encoding segment operators
    hash_fragment = urllib.parse.urlencode(hash_params, safe='@=;,')

    # Build the main URL
    main_params = {
        "module": "CoreHome",
        "action": "index",
        "idSite": site_id,
        "period": period,
        "date": date,
    }
    main_query = urllib.parse.urlencode(main_params)

    return f"https://{base_url}/index.php?{main_query}#?{hash_fragment}"


def format_data_source(
    base_url: str,
    method: str,
    params: dict,
    dimension_id: Optional[int] = None,
) -> str:
    """
    Format a data source reference for reports.

    Returns a markdown string with:
    - A hyperlink to the web UI
    - The raw API call for reproducibility

    Args:
        base_url: Matomo instance URL
        method: API method name
        params: Dict with idSite, period, date, and optionally segment
        dimension_id: For custom dimension queries

    Returns:
        Markdown-formatted data source string.
    """
    site_id = params.get("idSite")
    period = params.get("period")
    date = params.get("date")
    segment = params.get("segment")

    # Generate web UI link
    ui_url = get_ui_url(
        base_url=base_url,
        method=method,
        site_id=site_id,
        period=period,
        date=date,
        segment=segment,
        dimension_id=dimension_id,
    )

    # Generate raw API call (without token)
    api_params = {"idSite": site_id, "period": period, "date": date}
    if segment:
        api_params["segment"] = segment
    if dimension_id:
        api_params["idDimension"] = dimension_id

    api_call = f"{method}?" + "&".join(f"{k}={v}" for k, v in api_params.items())

    return f"[View in Matomo]({ui_url}) | `{api_call}`"


# --- Convenience functions for CLI usage ---

def load_api() -> MatomoAPI:
    """Load API client from .env in current directory or parents."""
    # Try current directory first
    if Path(".env").exists():
        return MatomoAPI()

    # Try parent directories
    cwd = Path.cwd()
    for parent in cwd.parents:
        env_path = parent / ".env"
        if env_path.exists():
            os.chdir(parent)
            api = MatomoAPI()
            os.chdir(cwd)
            return api

    raise FileNotFoundError("No .env file found in current directory or parents")


if __name__ == "__main__":
    # Quick test
    api = MatomoAPI()
    sites = api.get_sites()
    print(f"Found {len(sites)} sites:")
    for site in sites:
        print(f"  {site['idsite']}: {site['name']}")
