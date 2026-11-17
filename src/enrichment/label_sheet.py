"""Write the hand-labelling sheet for Ben (guide: docs/hand-labelling.md).

Fill the blank columns, save as data/gold/hand_labels.csv (or pilot_labels.csv for the pilot),
then run enrichment.evaluate. Posts are shown without model labels so hand labels are
independent of Jev.

    uv run python -m src.enrichment.label_sheet --pilot   # 40-post pilot from v0 data
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

from src.ingestion.panel import arxiv_ids_by_post

POSTS = Path("data/processed/posts_labelled.parquet")
SHEET = Path("data/gold/label_sheet.csv")
PILOT_SHEET = Path("data/gold/pilot_sheet.csv")
RAW_GLOB = "data/raw/*.jsonl"
ARXIV_ABS = "https://arxiv.org/abs/"
TIERS = ["<2k", "2k-20k", "20k-200k", ">200k"]
LABEL_FIELDS = [
    "is_researcher_post",
    "hook_archetype",
    "visual_type",
    "technical_rigor_score",
    "framing",
    "poster_role",
    "note",
]


def split_of(post_id: str) -> str:
    """Stable tuning/held-out split by hash, so it never shifts when posts are added."""
    return "tune" if int(hashlib.sha256(post_id.encode()).hexdigest(), 16) % 2 == 0 else "heldout"


def make_sheet(
    posts: pd.DataFrame,
    per_tier: int,
    paper_links: dict[str, list[str]],
    max_per_author: int = 2,
    seed: int = 0,
    split: str | None = None,
) -> pd.DataFrame:
    """Sample `per_tier` eligible posts per follower tier, at most `max_per_author` each."""
    d = posts[posts["eligible"]].sample(frac=1, random_state=seed)
    d = d.groupby("author_handle", sort=False).head(max_per_author)
    d = d.groupby("follower_tier", sort=False).head(per_tier)
    d = d.assign(_t=d["follower_tier"].map({t: i for i, t in enumerate(TIERS)}))
    d = d.sort_values(["_t", "post_id"])
    papers = d["post_id"].map(lambda p: paper_links.get(str(p), []))
    out = pd.DataFrame(
        {
            "post_id": d["post_id"].astype(str),
            "split": split or d["post_id"].astype(str).map(split_of),
            "tier": d["follower_tier"],
            "author_handle": d["author_handle"],
            "url": d["url"],
            "media_kind": d["media_kind"].fillna(""),
            "paper_link": papers.map(lambda ids: " ".join(ARXIV_ABS + i for i in ids)),
            "text": d["text"],
        }
    )
    for c in LABEL_FIELDS:
        out[c] = ""
    return out.reset_index(drop=True)


def pilot_pool(posts: pd.DataFrame) -> pd.DataFrame:
    """v0 posts by likely roster authors: Jev-passing authors plus own and benchmark accounts."""
    e = posts[posts["eligible"] & posts["mature"]]
    authors = set(e.loc[e["is_researcher_post"] == True, "author_handle"])  # noqa: E712
    return e[e["author_handle"].isin(authors) | e["cohort"].isin(["OWN", "BENCHMARK"])]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true", help="40-post pilot from v0 data")
    ap.add_argument("--per-tier", type=int, default=50)
    a = ap.parse_args()
    posts = pd.read_parquet(POSTS)
    links = arxiv_ids_by_post(Path().glob(RAW_GLOB))
    if a.pilot:
        sheet = make_sheet(pilot_pool(posts), 10, links, split="pilot")
        path = PILOT_SHEET
    else:
        sheet = make_sheet(posts, a.per_tier, links)
        path = SHEET
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.to_csv(path, index=False)
    print(f"wrote {len(sheet)} posts to {path}")
    print(sheet.groupby("tier").size().to_string())
    print(f"posts with a paper link: {(sheet['paper_link'] != '').sum()}")


if __name__ == "__main__":
    main()
