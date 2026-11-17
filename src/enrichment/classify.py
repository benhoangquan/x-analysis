"""CLI: label eligible posts with the judge. Resumable; cached by (post_id, label_version).

python -m src.enrichment.classify --model jev-latest [--limit N] [--force]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.enrichment.judge import DEFAULT_MODEL, JevError, JevJudge, Judge
from src.enrichment.media import fetch_image
from src.ingestion.apify import _load_dotenv
from src.schema import PostLabels

POSTS = Path("data/processed/posts_enriched.parquet")
LABELS = Path("data/processed/labels.parquet")
LABELLED = Path("data/processed/posts_labelled.parquet")


def load_cache(path: Path = LABELS) -> pd.DataFrame:
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


def run(
    posts: pd.DataFrame, judge: Judge, cache: pd.DataFrame, force: bool = False
) -> pd.DataFrame:
    """Label every post lacking a successful label at judge.version; failures keep a reason."""
    done: set[str] = set()
    if not cache.empty and not force:
        ok = cache[(cache["label_version"] == judge.version) & cache["error"].isna()]
        done = set(ok["post_id"])
    rows = [r for r in cache.to_dict("records")] if not cache.empty else []
    rows = [r for r in rows if r["post_id"] not in set(posts["post_id"]) - done]
    for p in posts[~posts["post_id"].isin(done)].itertuples():
        kind = None if pd.isna(p.media_kind) else p.media_kind  # Parquet gives NaN, not None
        image = None
        if kind == "photo" and len(p.media_urls):
            image = fetch_image(p.post_id, p.media_urls[0])
        try:
            lab = judge.label(p.post_id, p.text, kind, image)
        except (JevError, KeyError, ValueError) as e:
            lab = PostLabels(post_id=p.post_id, label_version=judge.version, error=str(e)[:300])
        rows.append(lab.model_dump(mode="json"))
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--ids", type=Path, help="CSV with a post_id column: label only these")
    ap.add_argument("--out", type=Path, help="write labels here, leaving the main cache alone")
    a = ap.parse_args()
    _load_dotenv()
    posts = pd.read_parquet(POSTS)
    posts = posts[posts["eligible"]]
    if a.ids:  # e.g. the pilot check (decision 41): data/gold/pilot_sheet.csv
        wanted = set(pd.read_csv(a.ids, dtype={"post_id": str})["post_id"])
        posts = posts[posts["post_id"].astype(str).isin(wanted)]
    if a.limit:
        posts = posts.head(a.limit)
    judge = JevJudge(model=a.model)
    labels = run(posts, judge, load_cache(a.out) if a.out else load_cache(), a.force)
    for col in ("archetype_probs", "framing_probs"):
        if col in labels:
            labels[col] = labels[col].astype(str)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        labels.to_parquet(a.out, index=False)
        failed = int(labels["error"].notna().sum())
        print(f"labelled {len(labels) - failed} -> {a.out}, failed {failed}, "
              f"input tokens {judge.input_tokens}")  # fmt: skip
        return
    LABELS.parent.mkdir(parents=True, exist_ok=True)
    labels.to_parquet(LABELS, index=False)
    merged = pd.read_parquet(POSTS).merge(
        labels.drop(columns=["label_rationale"]), on="post_id", how="left"
    )
    merged.to_parquet(LABELLED, index=False)
    failed = int(labels["error"].notna().sum())
    print(f"labelled {len(labels) - failed}, failed {failed}, input tokens {judge.input_tokens}")


if __name__ == "__main__":
    main()
