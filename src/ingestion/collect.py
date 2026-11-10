"""Collect cohorts one run at a time: own + benchmark timelines, candidate search."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta

from src import config
from src.ingestion.apify import _load_dotenv, run


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--what", choices=["timelines", "discovery"], required=True)
    p.add_argument("--timeline-items", type=int, default=300)
    p.add_argument("--slice-items", type=int, default=500)
    p.add_argument("--slice-days", type=int, default=30)
    a = p.parse_args()
    _load_dotenv()
    today = datetime.now(UTC).date()
    start = today - timedelta(days=config.WINDOW_DAYS)

    if a.what == "timelines":
        for h in config.OWN_HANDLES + config.BENCHMARK_HANDLES:
            q = config.timeline_query(h, start.isoformat(), today.isoformat())
            print(h, run([q], a.timeline_items, f"timeline_{h}"))
    else:
        d = start
        while d < today:
            e = min(d + timedelta(days=a.slice_days), today)
            for q in config.discovery_queries(d.isoformat(), e.isoformat()):
                print(d, run([q], a.slice_items, f"discovery_{d}"))
            d = e


if __name__ == "__main__":
    main()
