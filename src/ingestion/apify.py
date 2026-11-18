"""Apify collector: the only module that talks to Apify. Writes raw JSONL verbatim.

Rules from the plan: one concurrent run, <=5 queries per run, >=50 items per query,
Latest sort, no customMapFunction filtering, token via header (never in the URL).

Budget: every run is checked against APIFY_BUDGET_USD before it starts, assuming the worst
case (every query returns max_items), and its actual item count is appended to SPEND_LOG.
The run also carries a server-side maxItems cap, so a run cannot be charged past the budget.
The log is an estimate at the listed price; the Apify console is the bill.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import (
    ACTOR_ID,
    APIFY_BUDGET_USD,
    APIFY_PRICE_PER_1K_USD,
    MAX_QUERIES_PER_RUN,
    MIN_ITEMS_PER_QUERY,
)
from src.ingestion.filler import write_sidecar

RAW_DIR = Path("data/raw")
SPEND_LOG = Path("data/apify_spend.csv")
SPEND_COLS = ["at_utc", "label", "queries", "max_items", "items", "est_usd"]
Transport = Callable[[str, dict[str, Any], str], list[dict[str, Any]]]


class BudgetExceededError(RuntimeError):
    """A run could push estimated Apify spend past APIFY_BUDGET_USD."""


def cost_usd(n_items: int) -> float:
    return n_items * APIFY_PRICE_PER_1K_USD / 1000


def spent_usd(log: Path = SPEND_LOG) -> float:
    if not log.exists():
        return 0.0
    with log.open() as f:
        return sum(float(r["est_usd"]) for r in csv.DictReader(f))


def check_budget(
    n_queries: int, max_items: int, log: Path = SPEND_LOG, budget: float = APIFY_BUDGET_USD
) -> int:
    """Raise if the worst case of this run breaks the budget; return items still affordable."""
    spent = spent_usd(log)
    worst = cost_usd(n_queries * max_items)
    if spent + worst > budget + 1e-9:
        raise BudgetExceededError(
            f"run could cost ${worst:.2f}; spent ${spent:.2f} of ${budget:.2f}. "
            "Lower max_items or queries, or raise APIFY_BUDGET_USD with Ben's approval."
        )
    return int((budget - spent) / APIFY_PRICE_PER_1K_USD * 1000)


def record_spend(
    label: str, n_queries: int, max_items: int, n_items: int, log: Path = SPEND_LOG
) -> None:
    new = not log.exists()
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if new:
            w.writerow(SPEND_COLS)
        stamp = datetime.now(UTC).isoformat(timespec="seconds")
        w.writerow([stamp, label, n_queries, max_items, n_items, f"{cost_usd(n_items):.4f}"])


def _http_transport(url: str, payload: dict[str, Any], token: str) -> list[dict[str, Any]]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise RuntimeError(f"Apify HTTP {e.code}: {detail}") from e


def build_input(queries: list[str], max_items: int, sort: str = "Latest") -> dict[str, Any]:
    if not 1 <= len(queries) <= MAX_QUERIES_PER_RUN:
        raise ValueError(f"need 1..{MAX_QUERIES_PER_RUN} queries per run")
    if max_items < MIN_ITEMS_PER_QUERY:
        raise ValueError(f"maxItems must be >= {MIN_ITEMS_PER_QUERY} (actor rule)")
    return {"searchTerms": queries, "maxItems": max_items, "sort": sort}


def run(
    queries: list[str],
    max_items: int,
    label: str,
    token: str | None = None,
    transport: Transport = _http_transport,
    out_dir: Path = RAW_DIR,
    spend_log: Path = SPEND_LOG,
) -> Path:
    """Run the actor synchronously, store the items verbatim as JSONL, and log the spend."""
    token = token or os.environ.get("APIFY_TOKEN", "")
    if not token:
        raise RuntimeError("APIFY_TOKEN is not set (put it in .env or the environment)")
    payload = build_input(queries, max_items)
    affordable = check_budget(len(queries), max_items, spend_log)
    params = urllib.parse.urlencode({"maxItems": min(affordable, len(queries) * max_items)})
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items?{params}"
    items = transport(url, payload, token)
    record_spend(label, len(queries), max_items, len(items), spend_log)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"{label}_{stamp}.jsonl"
    with path.open("w") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")
    write_sidecar(path, queries, max_items, label)  # decision 49: ingestion drops filler
    return path


def _load_dotenv(path: Path = Path(".env")) -> None:
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--query", action="append", required=True)
    p.add_argument("--max-items", type=int, default=50)
    p.add_argument("--label", default="test")
    a = p.parse_args()
    _load_dotenv()
    print(run(a.query, a.max_items, a.label))
    print(f"estimated Apify spend: ${spent_usd():.2f} of ${APIFY_BUDGET_USD:.2f}")


if __name__ == "__main__":
    main()
