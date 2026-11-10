"""Baselines: maturity filter, eligibility, follower tiers, follower-expected reach,
trailing author medians.

Follower count drives views but not linearly, so impressions are normalised two ways:
- reach_vs_expected: actual / expected impressions from a log-log fit across the corpus.
- baseline_ratio: actual / the author's trailing-30-day median (needs a full timeline).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.metrics.formulas import FOLLOWER_FLOOR

MATURITY_DAYS = 7
BASELINE_WINDOW = "30D"
BASELINE_MIN_PRIOR = 3
MIN_FIT_POSTS = 20
MIN_FIT_AUTHORS = 10  # same evidence gate the plan uses for lifts
TIER_EDGES = [0, 2_000, 20_000, 200_000, np.inf]
TIER_LABELS = ["<2k", "2k-20k", "20k-200k", ">200k"]
BASELINE_COHORTS = {"OWN", "BENCHMARK"}


@dataclass(frozen=True)
class ReachModel:
    slope: float
    intercept: float
    n_posts: int
    n_authors: int

    @property
    def reliable(self) -> bool:
        return self.n_posts >= MIN_FIT_POSTS and self.n_authors >= MIN_FIT_AUTHORS

    def expected(self, followers: pd.Series) -> pd.Series:
        logf = np.log(followers.clip(lower=FOLLOWER_FLOOR).astype("float64"))
        return np.exp(self.intercept + self.slope * logf)


def follower_tier(followers: pd.Series) -> pd.Series:
    return pd.cut(followers, bins=TIER_EDGES, labels=TIER_LABELS, right=False).astype(str)


def add_eligibility(df: pd.DataFrame) -> pd.DataFrame:
    """Add age_days, mature, is_self_reply, eligible, follower_tier."""
    out = df.copy()
    created = pd.to_datetime(out["created_at"], utc=True)
    collected = pd.to_datetime(out["collected_at"], utc=True)
    out["age_days"] = (collected - created).dt.total_seconds() / 86400
    out["mature"] = out["age_days"] >= MATURITY_DAYS
    out["is_self_reply"] = out["is_reply"] & (
        out["in_reply_to_username"].str.lower() == out["author_handle"].str.lower()
    )
    # Originals and quotes only. Replies are dropped; a self-reply is a thread continuation
    # whose opener is already counted.
    out["eligible"] = ~out["is_retweet"] & ~out["is_reply"]
    out["follower_tier"] = follower_tier(out["followers_at_collection"])
    return out


def fit_reach_model(df: pd.DataFrame) -> ReachModel:
    """OLS of log(impressions) on log(max(followers, 100)) over eligible, mature posts."""
    d = df[df["eligible"] & df["mature"] & (df["impressions"] > 0)]
    if len(d) < 2 or d["followers_at_collection"].clip(lower=FOLLOWER_FLOOR).nunique() < 2:
        return ReachModel(np.nan, np.nan, len(d), d["author_handle"].nunique())
    x = np.log(d["followers_at_collection"].clip(lower=FOLLOWER_FLOOR).astype("float64"))
    y = np.log(d["impressions"].astype("float64"))
    slope, intercept = np.polyfit(x, y, 1)
    return ReachModel(float(slope), float(intercept), len(d), d["author_handle"].nunique())


def trailing_baseline(df: pd.DataFrame) -> pd.Series:
    """Median impressions of the author's earlier eligible posts in the prior 30 days.

    Only for OWN and BENCHMARK (full timelines). NaN with fewer than 3 prior posts.
    """
    out = pd.Series(np.nan, index=df.index, dtype="float64")
    pool = df[df["eligible"] & df["impressions"].notna() & df["cohort"].isin(BASELINE_COHORTS)]
    for _, g in pool.groupby("author_handle"):
        g = g.assign(_t=pd.to_datetime(g["created_at"], utc=True)).sort_values("_t")
        roll = (
            g.set_index("_t")["impressions"]
            .astype("float64")
            .rolling(BASELINE_WINDOW, closed="left", min_periods=BASELINE_MIN_PRIOR)
            .median()
        )
        out.loc[g.index] = roll.to_numpy()
    return out


def add_baselines(df: pd.DataFrame) -> tuple[pd.DataFrame, ReachModel]:
    out = add_eligibility(df)
    model = fit_reach_model(out)
    out["reach_expected"] = model.expected(out["followers_at_collection"])
    out["reach_vs_expected"] = out["impressions"] / out["reach_expected"]
    out["reach_model_reliable"] = model.reliable
    out["baseline_ratio"] = out["impressions"] / trailing_baseline(out)
    scored = out["eligible"] & out["mature"]
    out["pctile_in_tier"] = np.nan
    out.loc[scored, "pctile_in_tier"] = (
        out[scored].groupby("follower_tier")["reach_vs_expected"].rank(pct=True)
    )
    return out, model


def sanity_table(df: pd.DataFrame) -> pd.DataFrame:
    """Per follower tier summary over eligible, mature posts, for manual review."""
    s = df[df["eligible"] & df["mature"]]
    g = s.groupby("follower_tier")
    t = g.agg(
        posts=("post_id", "count"),
        authors=("author_handle", "nunique"),
        median_views=("impressions", "median"),
        median_r_out=("r_out", "median"),
        median_reach_vs_expected=("reach_vs_expected", "median"),
        median_s_intent=("s_intent", "median"),
        median_cr_bmk=("cr_bmk", "median"),
    )
    return t.reindex([x for x in TIER_LABELS if x in t.index]).reset_index()
