"""Field-coverage report for a raw JSONL file: settles open item A (are impressions present?)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.ingestion.adapters import normalise_row
from src.ingestion.filler import queries_for, split_filler

FIELDS = ["impressions", "bookmarks", "followers_at_collection", "likes", "replies", "reposts",
          "quotes", "created_at", "text"]  # fmt: skip


def coverage(path: Path) -> dict[str, float]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    queries = queries_for(path)
    filler_share = 0.0
    if queries:  # decision 49: report filler, then measure coverage on what is kept
        kept, filler = split_filler(rows, queries)
        filler_share = len(filler) / (len(rows) or 1)
        rows = kept
    n = len(rows) or 1
    norm = [normalise_row(r) for r in rows]
    fields = {f: sum(f in r for r in norm) / n for f in FIELDS}
    return fields | {"n_rows": float(len(rows)), "filler_share": filler_share}


if __name__ == "__main__":
    for k, v in coverage(Path(sys.argv[1])).items():
        print(f"{k:28s} {v:.0%}" if k != "n_rows" else f"{k:28s} {int(v)}")
