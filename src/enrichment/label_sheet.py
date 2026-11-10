"""Write the hand-labelling sheet for Ben: data/gold/label_sheet.csv.

Fill the blank columns, save as data/gold/hand_labels.csv, then run enrichment.evaluate.
Posts are shown without model labels so the hand labels are independent.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

POSTS = Path("data/processed/posts_enriched.parquet")
SHEET = Path("data/gold/label_sheet.csv")


def split_of(post_id: str) -> str:
    """Stable tuning/held-out split by hash, so it never shifts when posts are added."""
    return "tune" if int(hashlib.sha256(post_id.encode()).hexdigest(), 16) % 2 == 0 else "heldout"


def make_sheet(posts: pd.DataFrame, n: int | None = None) -> pd.DataFrame:
    d = posts[posts["eligible"]].sort_values("post_id")
    if n:
        d = d.sample(min(n, len(d)), random_state=0)
    out = d[["post_id", "url", "media_kind", "text"]].copy()
    out["split"] = out["post_id"].map(split_of)
    for c in ["is_researcher_post", "hook_archetype", "visual_type", "technical_rigor_score"]:
        out[c] = ""
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    a = ap.parse_args()
    sheet = make_sheet(pd.read_parquet(POSTS), a.n)
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    sheet.to_csv(SHEET, index=False)
    print(f"wrote {len(sheet)} posts to {SHEET}")


if __name__ == "__main__":
    main()
