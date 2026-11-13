"""MVP descriptive analysis on the small initial dataset. Writes outputs/reports/mvp-findings.md.

This is deliberately descriptive: the plan's evidence gate (>=20 posts, >=10 authors per cell)
is not met, so nothing here is a lift estimate or a recommendation backed by statistics.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.enrichment.rules import add_rule_features
from src.ingestion.load_raw import load
from src.metrics.baselines import ReachModel, add_baselines, sanity_table

OUT_PARQUET = Path("data/processed/posts_enriched.parquet")


def build(inputs: list[Path]) -> tuple[pd.DataFrame, ReachModel]:
    df, _ = load(*inputs)
    return add_baselines(add_rule_features(df))


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
    by_author = (
        scored.groupby("author_handle")
        .agg(
            followers=("followers_at_collection", "first"),
            posts=("post_id", "count"),
            median_views=("impressions", "median"),
            median_r_out=("r_out", "median"),
            median_s_intent=("s_intent", "median"),
            median_cr_bmk=("cr_bmk", "median"),
        )
        .reset_index()
        .sort_values("median_r_out", ascending=False)
    )
    top = scored.sort_values("s_intent", ascending=False).head(8)[
        ["author_handle", "text", "impressions", "r_out", "s_intent", "cr_bmk", "media_count"]
    ]
    top = top.assign(text=_clip(top["text"], 80))

    feat_rows = []
    for feat in ["has_media", "has_link", "has_number", "is_question"]:
        for val, g in scored.groupby(feat):
            feat_rows.append(
                {"feature": feat, "value": bool(val), "n": len(g),
                 "authors": g["author_handle"].nunique(),
                 "median_s_intent": g["s_intent"].median(),
                 "median_cr_bmk": g["cr_bmk"].median()}
            )  # fmt: skip
    feats = pd.DataFrame(feat_rows)

    own = scored[scored["cohort"] == "OWN"]
    funnel = pd.DataFrame(
        {
            "stage": ["rows loaded", "eligible (no replies/retweets)", "mature (>=7 days)"],
            "posts": [len(df), len(elig), len(scored)],
        }
    )
    authors = ", ".join(sorted(df["author_handle"].unique()))
    return f"""# MVP findings: initial dataset ({len(df)} posts)

Data: first Apify test calls (the only ones returned before the actor's free-plan run limit).
Authors: {authors}. Collected {df["collected_at"].max():%Y-%m-%d}.

**Read this first.** {len(scored)} scored posts from {scored["author_handle"].nunique()} authors is
far below the plan's evidence gate (>=20 posts and >=10 authors per cell). Everything below is
descriptive. There are no lift estimates, no confidence intervals and no hook-archetype or rigor
labels yet (the classifier is milestone 3). Treat the observations as hypotheses to test, not
findings.

## Funnel

{_md(funnel)}

## Per author (eligible, mature posts)

{
        _md(
            by_author,
            {
                "followers": "{:,.0f}",
                "median_views": "{:,.0f}",
                "median_r_out": "{:.1f}",
                "median_s_intent": "{:.4f}",
                "median_cr_bmk": "{:.2f}",
            },
        )
    }

## Highest-intent posts (by S_intent)

{
        _md(
            top,
            {"impressions": "{:,.0f}", "r_out": "{:.1f}", "s_intent": "{:.4f}", "cr_bmk": "{:.2f}"},
        )
    }

## Rule features vs intent (descriptive only)

{_md(feats, {"median_s_intent": "{:.4f}", "median_cr_bmk": "{:.2f}"})}

## Tiptree's own posts

{
        _md(
            own.assign(text=_clip(own["text"], 70))[
                ["author_handle", "text", "followers_at_collection", "impressions", "r_out",
                 "s_intent", "cr_bmk", "media_count"]
            ].sort_values("s_intent", ascending=False),
            {"impressions": "{:,.0f}", "r_out": "{:.1f}", "s_intent": "{:.4f}", "cr_bmk": "{:.2f}"},
        )
    }

## Hypotheses for Martin to test (from this snapshot; not statistically supported)

1. **Reach is not intent.** Tiptree's biggest post by views (5,042, 50x its follower count) is a
   Lacuna/Althea product post with media, and it has the lowest S_intent of the seven (0.0012)
   and no bookmarks. Next time, track bookmarks per 1k views and not views alone, as AGENTS.md
   already prescribes.
2. **Short, claim-led text posts carry Tiptree's intent.** Its top two by S_intent are plain-text
   posts built on one clear claim ("Know what has been done. Do what hasn't.") and a concrete
   research question. Test two or three more posts of this form against a product post on the
   same topic.
3. **Bookmarks are rare for Tiptree.** Only the Claude-connector announcement (3.5 per 1k views)
   scored; the other six are 0. The strongest bookmark rates in the sample (karpathy 4.3 to 10.1)
   come from posts that carry something to save, such as an interpretability argument with a
   figure. Try a post that carries a reusable artefact (a Lacuna map or a result table) and
   check whether CR_bmk moves.
4. **Do not copy karpathy's absolute numbers.** At 4.4M followers his reach is not comparable
   to a 67-follower account. Use the follower-tier comparisons from milestone 2 once more authors
   are collected.

Open limits: no archetype, rigor or visual labels yet; no reach-vs-expected fit (it needs many
authors); the discovery cohort is empty, so nothing here speaks to researcher posts across X.
"""  # fmt: skip


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
Posts with a trailing-30-day baseline (>=3 prior eligible posts, OWN/BENCHMARK): {base_n}.

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
            },
        )
    }

Review checklist: reach_vs_expected medians near 1.0 within each tier; the fit slope below 1
(views grow slower than followers); tiers with one author are not comparable to each other.
"""


def main() -> None:
    inputs = sorted(p for p in Path("data/raw").glob("*.jsonl"))
    df, model = build(inputs)
    df = df.drop_duplicates("post_id")
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)
    Path("outputs/reports").mkdir(parents=True, exist_ok=True)
    Path("outputs/reports/mvp-findings.md").write_text(report(df))
    Path("outputs/reports/baselines-sanity.md").write_text(sanity_report(df, model))
    print(f"{len(df)} posts -> {OUT_PARQUET}; reports written")


if __name__ == "__main__":
    main()
