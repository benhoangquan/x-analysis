"""CLI: validate raw rows, dedupe, compute metrics, write Parquet.

python -m src.ingestion.load_raw --input data/raw/posts_export.csv
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.config import cohort_for
from src.ingestion.adapters import rows_to_posts
from src.ingestion.filler import queries_for, split_filler
from src.metrics.formulas import add_metrics
from src.schema import Cohort

DEFAULT_OUT = Path("data/processed/posts.parquet")


def _read_rows(input_path: Path, dropped: list[tuple[int, str]] | None = None) -> list[dict]:
    if input_path.suffix == ".jsonl":
        collected = datetime.fromtimestamp(input_path.stat().st_mtime, UTC).isoformat()
        rows = [json.loads(x) for x in input_path.read_text().splitlines() if x.strip()]
        rows = [r for r in rows if not r.get("noResults")]  # actor placeholder rows
        queries = queries_for(input_path)
        if queries:  # decision 49: keep only items that match the run's own query
            rows, filler = split_filler(rows, queries)
            if dropped is not None:
                dropped += [(-1, f"filler from {input_path.name}: {r.get('id')}") for r in filler]
        default = Cohort.PANEL if "panel" in input_path.parts else Cohort.DISCOVERED
        for r in rows:
            handle = (r.get("author") or {}).get("userName") or r.get("userName") or ""
            r.setdefault("cohort", str(cohort_for(handle, default)))
            r.setdefault("collected_at", collected)
            r["source"] = "apify"  # overrides the actor's own field (posting client)
        return rows
    return pd.read_csv(input_path, dtype=str, keep_default_na=False).to_dict("records")


def load(*input_paths: Path) -> tuple[pd.DataFrame, list[tuple[int, str]]]:
    filler: list[tuple[int, str]] = []
    rows = [r for p in input_paths for r in _read_rows(p, filler)]
    posts, rejected = rows_to_posts(rows)
    rejected = filler + rejected
    df = pd.DataFrame([p.model_dump(mode="python") for p in posts])
    if df.empty:
        return df, rejected
    for col in ("cohort", "post_kind"):
        df[col] = df[col].astype(str)
    df = df.drop_duplicates(subset="post_id", keep="last").reset_index(drop=True)
    return add_metrics(df), rejected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    df, rejected = load(*args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.output, index=False)
    print(f"wrote {len(df)} posts to {args.output}; rejected {len(rejected)}")
    for idx, reason in rejected:
        print(f"  row {idx}: {reason}")


if __name__ == "__main__":
    main()
