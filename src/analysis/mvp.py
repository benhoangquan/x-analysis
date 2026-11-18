"""Corpus baselines and descriptive summary (Milestone 2). Writes posts_enriched.parquet and
outputs/reports/{mvp-findings.md, baselines-sanity.md}.

Everything here is descriptive: hypothesis tests (E1-E6) and lift tables run in Milestone 4.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.enrichment.rules import add_rule_features
from src.ingestion.load_raw import DEFAULT_OUT as POSTS_PARQUET
from src.ingestion.load_raw import load
from src.metrics.baselines import TIER_LABELS, ReachModel, add_baselines, sanity_table

OUT_PARQUET = Path("data/processed/posts_enriched.parquet")
STATS_JSON = Path("data/processed/ingestion_stats.json")


def build_with_stats(inputs: list[Path]) -> tuple[pd.DataFrame, ReachModel, list[tuple[int, str]]]:
    df, rejected = load(*inputs)
    enriched, model = add_baselines(add_rule_features(df))
    return enriched, model, rejected


def build(inputs: list[Path]) -> tuple[pd.DataFrame, ReachModel]:
    enriched, model, _ = build_with_stats(inputs)
    return enriched, model


def _md(df: pd.DataFrame, fmt: dict[str, str] | None = None) -> str:
    fmt = fmt or {}
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            cells.append(fmt.get(c, "{}").format(v) if pd.notna(v) else "n/a")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _clip(s: pd.Series, n: int) -> pd.Series:
    return s.str.replace(r"\s+", " ", regex=True).str[:n]


def report(df: pd.DataFrame) -> str:
    elig = df[df["eligible"]]
    scored = elig[elig["mature"]]
    capped = scored[scored["in_author_cap"]] if "in_author_cap" in scored else scored

    rank = {t: i for i, t in enumerate(TIER_LABELS)}
    cohort_tier = (
        df.groupby(["cohort", "follower_tier"], dropna=False)
        .agg(
            posts=("post_id", "count"),
            eligible=("eligible", "sum"),
            mature=("mature", "sum"),
            authors=("author_handle", "nunique"),
            median_views=("impressions", "median"),
            median_cr_bmk=("cr_bmk", "median"),
            median_cr_bmk_shrunk=("cr_bmk_shrunk", "median"),
        )
        .reset_index()
    )
    cohort_tier["_t"] = cohort_tier["follower_tier"].map(lambda t: rank.get(t, 99))
    cohort_tier = cohort_tier.sort_values(["cohort", "_t"]).drop(columns=["_t"])

    feat_rows = []
    for feat in ["has_media", "has_link", "has_number", "is_question", "is_thread_opener"]:
        if feat not in scored.columns:
            continue
        for val, g in scored.groupby(feat):
            feat_rows.append(
                {
                    "feature": feat,
                    "value": bool(val),
                    "n": len(g),
                    "authors": g["author_handle"].nunique(),
                    "median_s_intent": g["s_intent"].median(),
                    "median_cr_bmk": g["cr_bmk"].median(),
                }
            )
    feats = pd.DataFrame(feat_rows)

    own = scored[scored["cohort"] == "OWN"]
    funnel = pd.DataFrame(
        {
            "stage": [
                "rows loaded",
                "eligible (no replies/retweets)",
                "mature (>=7 days)",
                "within author cap (<=40/author)",
            ],
            "posts": [len(df), len(elig), len(scored), len(capped)],
        }
    )
    own_table = (
        _md(
            own.assign(text=_clip(own["text"], 70))[
                [
                    "author_handle", "text", "followers_at_collection", "impressions",
                    "r_out", "s_intent", "cr_bmk", "cr_bmk_shrunk", "media_count",
                ]
            ].sort_values("cr_bmk_shrunk", ascending=False),
            {
                "impressions": "{:,.0f}",
                "r_out": "{:.1f}",
                "s_intent": "{:.4f}",
                "cr_bmk": "{:.2f}",
                "cr_bmk_shrunk": "{:.2f}",
            },
        )
        if not own.empty
        else "_No mature eligible posts from `@tiptreesystems` or `@martincsweiss1`._"
    )
    return f"""# Corpus summary & baselines ({len(df)} posts)

Window: {df["created_at"].min():%Y-%m-%d} to {df["created_at"].max():%Y-%m-%d} \
(collected {df["collected_at"].max():%Y-%m-%d}; {df["author_handle"].nunique()} authors).

**Descriptive only.** Hypothesis verdicts and evidence-gated templates come from Milestone 4 \
(`experiments.py`, `lift.py`, `report.py`) once Jev labels are attached.

## Funnel

{_md(funnel)}

## Cohort × follower tier (all loaded posts)

{
        _md(
            cohort_tier,
            {
                "median_views": "{:,.0f}",
                "median_cr_bmk": "{:.2f}",
                "median_cr_bmk_shrunk": "{:.2f}",
            },
        )
    }

## Rule features vs intent (eligible, mature posts; descriptive)

{_md(feats, {"median_s_intent": "{:.4f}", "median_cr_bmk": "{:.2f}"})}

## Tiptree's own posts (eligible, mature)

{own_table}
"""


def sanity_report(df: pd.DataFrame, model: ReachModel) -> str:
    fit = (
        f"slope {model.slope:.2f}, intercept {model.intercept:.2f}"
        if not np.isnan(model.slope)
        else "not estimable"
    )
    status = "reliable" if model.reliable else "NOT reliable (below the 20 posts / 10 authors gate)"
    t = sanity_table(df)
    base = df[df["baseline_ratio"].notna()]
    base_n = f"{len(base)} posts across {base['author_handle'].nunique()} authors"
    return f"""# Baselines sanity check

Reach model: log(views) = intercept + slope * log(max(followers, 100)). Fit: {fit} on
{model.n_posts} posts from {model.n_authors} authors. Status: **{status}**.
Posts with a trailing-30-day baseline (>=3 prior eligible posts, OWN/BENCHMARK/ROSTER): {base_n}.

## Per follower tier (eligible, mature posts)

{
        _md(
            t,
            {
                "median_views": "{:,.0f}",
                "median_r_out": "{:.1f}",
                "median_reach_vs_expected": "{:.2f}",
                "median_s_intent": "{:.4f}",
                "median_cr_bmk": "{:.2f}",
                "capped_posts": "{:,.0f}",
                "median_cr_bmk_shrunk": "{:.2f}",
            },
        )
    }

Review checklist: reach_vs_expected medians near 1.0 within each tier; the fit slope below 1
(views grow slower than followers); tiers with one author are not comparable to each other.
"""


def default_inputs() -> list[Path]:
    v1 = sorted(Path("data/raw/roster").glob("*.jsonl")) + sorted(
        Path("data/raw/panel").glob("*.jsonl")
    )
    return v1 if v1 else sorted(Path("data/raw").glob("*.jsonl"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, nargs="*")
    a = ap.parse_args()
    inputs = a.input if a.input else default_inputs()
    df, model, rejected = build_with_stats(inputs)
    df = df.drop_duplicates("post_id").reset_index(drop=True)
    POSTS_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(POSTS_PARQUET, index=False)
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)
    n_filler = sum(1 for _, msg in rejected if msg.startswith("filler from "))
    stats = {
        "dropped_filler": n_filler,
        "rejected_other": len(rejected) - n_filler,
        "total_loaded": len(df),
    }
    STATS_JSON.write_text(json.dumps(stats, indent=2))
    Path("outputs/reports").mkdir(parents=True, exist_ok=True)
    Path("outputs/reports/mvp-findings.md").write_text(report(df))
    Path("outputs/reports/baselines-sanity.md").write_text(sanity_report(df, model))
    print(f"{len(df)} posts -> {OUT_PARQUET} (dropped filler: {n_filler}); reports written")


if __name__ == "__main__":
    main()
