#!/usr/bin/env python3
"""Sync Matomo site data to PostgreSQL cache tables."""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from sqlalchemy import delete

from lib.query import MatomoAPI, MatomoError
from lib.sources import get_matomo
from web.db import get_db
from web.models import MatomoBaseline, MatomoDimension, MatomoEvent, MatomoSegment


def fetch_custom_dimensions(api: MatomoAPI, site_id: int) -> list[dict]:
    try:
        dims = api.get_configured_dimensions(site_id)
        return [
            {"id": d.get("idcustomdimension"), "name": d.get("name"), "scope": d.get("scope"), "active": d.get("active")}
            for d in dims
        ]
    except MatomoError:
        return []


def fetch_saved_segments(api: MatomoAPI, site_id: int) -> list[dict]:
    try:
        segments = api._request("SegmentEditor.getAll", {"idSite": site_id})
        if not isinstance(segments, list):
            return []
        return [{"name": s.get("name"), "definition": s.get("definition")} for s in segments]
    except MatomoError:
        return []


def fetch_event_names(api: MatomoAPI, site_id: int, period: str, date: str) -> list[dict]:
    try:
        events = api.get_event_names(site_id, period, date, limit=200)
        return [{"name": e.get("label"), "events": e.get("nb_events", 0), "visits": e.get("nb_visits", 0)} for e in events]
    except MatomoError:
        return []


@dataclass
class SiteConfig:
    name: str
    matomo_id: int
    url: Optional[str] = None
    user_kind_dimension: Optional[int] = None


SITES = {
    "emplois": SiteConfig("Emplois", 117, "https://emplois.inclusion.beta.gouv.fr", user_kind_dimension=1),
    "pilotage": SiteConfig("Pilotage", 146, "https://pilotage.inclusion.gouv.fr"),
    "communaute": SiteConfig("Communaute", 206, "https://communaute.inclusion.gouv.fr"),
    "dora": SiteConfig("Dora", 211, "https://dora.inclusion.beta.gouv.fr"),
    "plateforme": SiteConfig("Plateforme", 212, "https://inclusion.beta.gouv.fr"),
    "rdv-insertion": SiteConfig("RDV Insertion", 214, "https://rdv-insertion.fr"),
    "mon-recap": SiteConfig("Mon Recap", 217, "https://mon-recap.inclusion.beta.gouv.fr"),
    "marche": SiteConfig("Marche", 136, "https://lemarche.inclusion.beta.gouv.fr"),
}


def get_months_for_year(year: int) -> list[str]:
    today = date.today()
    return [date(year, m, 1).strftime("%Y-%m-%d") for m in range(1, 13) if date(year, m, 1) <= today]


def fetch_baselines(api: MatomoAPI, site: SiteConfig, year: int) -> list[dict]:
    rows = []
    for month_date in get_months_for_year(year):
        month_label = month_date[:7]
        try:
            summary = api.get_visits(site_id=site.matomo_id, period="month", date=month_date)
            visitors = summary.get("nb_uniq_visitors", 0)
            visits = summary.get("nb_visits", 0)

            if visitors == 0 and visits == 0:
                rows.append({"site_id": site.matomo_id, "month": month_label})
                continue

            year_m, month_m = int(month_date[:4]), int(month_date[5:7])
            next_month = date(year_m + (month_m // 12), (month_m % 12) + 1, 1)
            days = (next_month - date(year_m, month_m, 1)).days

            user_types = None
            if site.user_kind_dimension:
                try:
                    kinds = api.get_dimension(site_id=site.matomo_id, dimension_id=site.user_kind_dimension, period="month", date=month_date)
                    user_types = json.dumps({k.get("label", "unknown"): k.get("nb_visits", 0) for k in kinds})
                except MatomoError:
                    pass  # dimension not available for this month

            rows.append({
                "site_id": site.matomo_id,
                "month": month_label,
                "visitors": visitors,
                "visits": visits,
                "daily_avg_visitors": round(visitors / days) if days else 0,
                "daily_avg_visits": round(visits / days) if days else 0,
                "bounce_rate": summary.get("bounce_rate", "0%"),
                "actions_per_visit": round(summary.get("nb_actions_per_visit", 0), 1),
                "avg_time_on_site": int(summary.get("avg_time_on_site", 0)),
                "user_types": user_types,
            })
        except MatomoError as e:
            print(f"   Warning: Could not fetch {month_label}: {e}")
            rows.append({"site_id": site.matomo_id, "month": month_label})

    return rows


def save_baselines(rows: list[dict]):
    with get_db() as session:
        for row in rows:
            obj = MatomoBaseline(
                site_id=row["site_id"],
                month=row["month"],
                visitors=row.get("visitors"),
                visits=row.get("visits"),
                daily_avg_visitors=row.get("daily_avg_visitors"),
                daily_avg_visits=row.get("daily_avg_visits"),
                bounce_rate=row.get("bounce_rate"),
                actions_per_visit=row.get("actions_per_visit"),
                avg_time_on_site=row.get("avg_time_on_site"),
                user_types=row.get("user_types"),
                synced_at=datetime.now(),
            )
            session.merge(obj)


def save_dimensions(site_id: int, dimensions: list[dict]):
    with get_db() as session:
        session.execute(delete(MatomoDimension).where(MatomoDimension.site_id == site_id))
        session.add_all([
            MatomoDimension(
                site_id=site_id,
                dimension_id=d["id"],
                name=d["name"],
                scope=d.get("scope"),
                active=d.get("active", True),
                synced_at=datetime.now(),
            )
            for d in dimensions
        ])


def save_segments(site_id: int, segments: list[dict]):
    with get_db() as session:
        session.execute(delete(MatomoSegment).where(MatomoSegment.site_id == site_id))
        session.add_all([
            MatomoSegment(
                site_id=site_id,
                name=s["name"],
                definition=s.get("definition"),
                synced_at=datetime.now(),
            )
            for s in segments
        ])


def save_events(site_id: int, events: list[dict], reference_month: str):
    with get_db() as session:
        session.execute(
            delete(MatomoEvent).where(MatomoEvent.site_id == site_id, MatomoEvent.reference_month == reference_month)
        )
        session.add_all([
            MatomoEvent(
                site_id=site_id,
                name=e["name"],
                event_count=e.get("events", 0),
                visit_count=e.get("visits", 0),
                reference_month=reference_month,
                synced_at=datetime.now(),
            )
            for e in events
        ])


def main():
    parser = argparse.ArgumentParser(description="Sync Matomo data to PostgreSQL")
    parser.add_argument("--site", help="Sync a single site")
    parser.add_argument("--year", type=int, default=date.today().year - 1)
    args = parser.parse_args()

    today = date.today()
    if today.month == 1:
        ref_date = date(today.year - 1, 12, 1)
    else:
        ref_date = date(today.year, today.month - 1, 1)
    ref_month = ref_date.strftime("%Y-%m")

    print(f"Matomo Sync — year={args.year}, ref_month={ref_month}")

    api = get_matomo()

    sites_to_sync = SITES
    if args.site:
        if args.site not in SITES:
            print(f"Unknown site: {args.site}. Available: {', '.join(SITES.keys())}", file=sys.stderr)
            sys.exit(1)
        sites_to_sync = {args.site: SITES[args.site]}

    for site_key, site_config in sites_to_sync.items():
        print(f"\n--- {site_config.name} (ID: {site_config.matomo_id}) ---")

        print(f"  Baselines {args.year}...", end=" ", flush=True)
        rows = fetch_baselines(api, site_config, args.year)
        print(f"{len(rows)} months")
        save_baselines(rows)

        print("  Dimensions...", end=" ", flush=True)
        dims = fetch_custom_dimensions(api, site_config.matomo_id)
        print(f"{len(dims)}")
        save_dimensions(site_config.matomo_id, dims)

        print("  Segments...", end=" ", flush=True)
        segs = fetch_saved_segments(api, site_config.matomo_id)
        print(f"{len(segs)}")
        save_segments(site_config.matomo_id, segs)

        print(f"  Events ({ref_month})...", end=" ", flush=True)
        events = fetch_event_names(api, site_config.matomo_id, "month", ref_date.strftime("%Y-%m-%d"))
        print(f"{len(events)}")
        save_events(site_config.matomo_id, events, ref_month)

    print("Done.")


if __name__ == "__main__":
    main()
