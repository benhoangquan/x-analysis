"""CLI: validate raw rows, dedupe, compute metrics, write Parquet.

python -m src.ingestion.load_raw --input data/raw/posts_export.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.ingestion.adapters import rows_to_posts
from src.metrics.formulas import add_metrics

DEFAULT_OUT = Path("data/processed/posts.parquet")


def load(input_path: Path) -> tuple[pd.DataFrame, list[tuple[int, str]]]:
    raw = pd.read_csv(input_path, dtype=str, keep_default_na=False)
    posts, rejected = rows_to_posts(raw.to_dict("records"))
    df = pd.DataFrame([p.model_dump(mode="python") for p in posts])
    if df.empty:
        return df, rejected
    for col in ("cohort", "post_kind"):
        df[col] = df[col].astype(str)
    df = df.drop_duplicates(subset="post_id", keep="last").reset_index(drop=True)
    return add_metrics(df), rejected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    df, rejected = load(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.output, index=False)
    print(f"wrote {len(df)} posts to {args.output}; rejected {len(rejected)}")
    for idx, reason in rejected:
        print(f"  row {idx}: {reason}")


if __name__ == "__main__":
    main()
