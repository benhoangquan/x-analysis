"""Swipe-file selection: top 5% by shrunk CR_bmk within tier (Milestone 4)."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd

from src.metrics.baselines import TIER_LABELS

LABELLED = Path("data/processed/posts_labelled.parquet")
CURATION = Path("data/swipe_file/curation.csv")
OUT_CSV = Path("data/swipe_file/swipe_file.csv")
MAX_AUTHOR_SHARE = 0.05
TOP_FRAC = 0.05


def _dropped_ids(curation: pd.DataFrame | None) -> set[str]:
    if curation is None or curation.empty or "post_id" not in curation.columns:
        return set()
    c = curation.copy()
    c["post_id"] = c["post_id"].astype(str)
    if "drop" in c.columns:
        flag = c["drop"].astype(str).str.strip().str.lower().isin(["true", "1", "yes", "y"])
        return set(c.loc[flag, "post_id"])
    if "keep" in c.columns:
        flag = c["keep"].astype(str).str.strip().str.lower().isin(["false", "0", "no", "n"])
        return set(c.loc[flag, "post_id"])
    return set(c["post_id"])


def _pick_with_cap(
    cands: pd.DataFrame, tier_targets: dict[str, int], max_per_author: int
) -> list[int]:
    counts: dict[str, int] = {}
    picked: list[int] = []
    tiers = [t for t in TIER_LABELS if t in tier_targets] + sorted(
        t for t in tier_targets if t not in TIER_LABELS
    )
    for tier in tiers:
        need = tier_targets[tier]
        if need <= 0:
            continue
        sub = cands[cands["follower_tier"] == tier].sort_values(
            ["cr_bmk_shrunk", "post_id"], ascending=[False, True]
        )
        got = 0
        for idx, row in sub.iterrows():
            au = str(row["author_handle"]).lower()
            if counts.get(au, 0) >= max_per_author:
                continue
            picked.append(idx)
            counts[au] = counts.get(au, 0) + 1
            got += 1
            if got >= need:
                break
    return picked


def select_swipe_file(
    df: pd.DataFrame, curation: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Select top 5% of mature filter-passing posts per tier with baseline >= 1 and no hype."""
    if df.empty:
        return df.copy()
    passing = df[
        df["eligible"].astype(bool)
        & df["mature"].astype(bool)
        & (df["is_researcher_post"] == True)  # noqa: E712
    ].copy()
    if passing.empty:
        return passing

    mask = passing["baseline_ratio"].notna() & (passing["baseline_ratio"] >= 1.0)
    mask &= passing["cr_bmk_shrunk"].notna()
    if "hype_flags" in passing.columns:
        mask &= passing["hype_flags"].fillna("").astype(str).str.strip().eq("")
    if "technical_rigor_score" in passing.columns:
        rigor = pd.to_numeric(passing["technical_rigor_score"], errors="coerce")
        mask &= rigor > 1
    drops = _dropped_ids(curation)
    if drops:
        mask &= ~passing["post_id"].astype(str).isin(drops)
    cands = passing[mask].copy()
    if cands.empty:
        return cands

    tier_passing = passing.groupby("follower_tier").size().to_dict()
    tier_avail = cands.groupby("follower_tier").size().to_dict()
    targets = {
        t: min(tier_avail.get(t, 0), math.ceil(TOP_FRAC * n))
        for t, n in tier_passing.items()
        if tier_avail.get(t, 0) > 0
    }
    est_n = sum(targets.values())
    if est_n == 0:
        return cands.iloc[0:0].copy()

    cap = max(1, math.floor(MAX_AUTHOR_SHARE * est_n))
    picked = _pick_with_cap(cands, targets, cap)
    while len(picked) >= 20:
        new_cap = max(1, math.floor(MAX_AUTHOR_SHARE * len(picked)))
        if new_cap >= cap:
            break
        cap = new_cap
        picked = _pick_with_cap(cands, targets, cap)

    out = cands.loc[picked].copy()
    rank = {t: i for i, t in enumerate(TIER_LABELS)}
    out["_t"] = out["follower_tier"].map(lambda t: rank.get(t, 99))
    out = out.sort_values(["_t", "cr_bmk_shrunk"], ascending=[True, False]).drop(columns=["_t"])
    return out.reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=LABELLED)
    ap.add_argument("--curation", type=Path, default=CURATION)
    ap.add_argument("--output", type=Path, default=OUT_CSV)
    a = ap.parse_args()
    df = pd.read_parquet(a.data)
    curation = pd.read_csv(a.curation, dtype=str) if a.curation.exists() else None
    swipe = select_swipe_file(df, curation)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    swipe.to_csv(a.output, index=False)
    print(f"wrote {len(swipe)} swipe-file posts -> {a.output}")


if __name__ == "__main__":
    main()
