"""Field-coverage report for a raw JSONL file: settles open item A (are impressions present?)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.ingestion.adapters import normalise_row

FIELDS = ["impressions", "bookmarks", "followers_at_collection", "likes", "replies", "reposts",
          "quotes", "created_at", "text"]  # fmt: skip


def coverage(path: Path) -> dict[str, float]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    n = len(rows) or 1
    norm = [normalise_row(r) for r in rows]
    return {f: sum(f in r for r in norm) / n for f in FIELDS} | {"n_rows": float(len(rows))}


if __name__ == "__main__":
    for k, v in coverage(Path(sys.argv[1])).items():
        print(f"{k:28s} {v:.0%}" if k != "n_rows" else f"{k:28s} {int(v)}")
