"""Apify collector: the only module that talks to Apify. Writes raw JSONL verbatim.

Rules from the plan: one concurrent run, <=5 queries per run, >=50 items per query,
Latest sort, no customMapFunction filtering, token via header (never in the URL).
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import ACTOR_ID, MAX_QUERIES_PER_RUN, MIN_ITEMS_PER_QUERY

RAW_DIR = Path("data/raw")
Transport = Callable[[str, dict[str, Any], str], list[dict[str, Any]]]


def _http_transport(url: str, payload: dict[str, Any], token: str) -> list[dict[str, Any]]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:  # noqa: S310
        return json.loads(resp.read())


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
) -> Path:
    """Run the actor synchronously and store the items verbatim as JSONL."""
    token = token or os.environ.get("APIFY_TOKEN", "")
    if not token:
        raise RuntimeError("APIFY_TOKEN is not set (put it in .env or the environment)")
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
    items = transport(url, build_input(queries, max_items), token)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"{label}_{stamp}.jsonl"
    with path.open("w") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")
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


if __name__ == "__main__":
    main()
