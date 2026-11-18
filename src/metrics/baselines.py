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
AUTHOR_CAP = 40
SHRINKAGE_VIEWS = 1000.0
MIN_FIT_POSTS = 20
MIN_FIT_AUTHORS = 10  # same evidence gate the plan uses for lifts
TIER_EDGES = [0, 2_000, 20_000, 200_000, np.inf]
TIER_LABELS = ["<2k", "2k-20k", "20k-200k", ">200k"]
BASELINE_COHORTS = {"OWN", "BENCHMARK", "ROSTER"}


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
    """OLS of log(impressions) on log(max(followers, 100)) over eligible, mature posts.

    Refits on ROSTER when ROSTER posts are present (plan line 276).
    """
    d = df[df["eligible"] & df["mature"] & (df["impressions"] > 0)]
    if "cohort" in d.columns and (d["cohort"] == "ROSTER").any():
        d = d[d["cohort"] == "ROSTER"]
    if len(d) < 2 or d["followers_at_collection"].clip(lower=FOLLOWER_FLOOR).nunique() < 2:
        return ReachModel(np.nan, np.nan, len(d), d["author_handle"].nunique())
    x = np.log(d["followers_at_collection"].clip(lower=FOLLOWER_FLOOR).astype("float64"))
    y = np.log(d["impressions"].astype("float64"))
    slope, intercept = np.polyfit(x, y, 1)
    return ReachModel(float(slope), float(intercept), len(d), d["author_handle"].nunique())


def trailing_baseline(df: pd.DataFrame) -> pd.Series:
    """Median impressions of the author's earlier eligible posts in the prior 30 days.

    Only for OWN, BENCHMARK and ROSTER (full timelines). NaN with fewer than 3 prior posts.
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


def even_author_cap(df: pd.DataFrame, max_posts: int = AUTHOR_CAP) -> pd.Series:
    """Select at most `max_posts` eligible, mature posts per author evenly across the window."""
    out = pd.Series(False, index=df.index, dtype="bool")
    if max_posts <= 0 or df.empty:
        return out
    pool = df[df["eligible"] & df["mature"]].copy()
    if pool.empty:
        return out
    pool["_t"] = pd.to_datetime(pool["created_at"], utc=True)
    sort_cols = ["_t", "post_id"] if "post_id" in pool.columns else ["_t"]
    for _, g in pool.groupby("author_handle", sort=False):
        g = g.sort_values(sort_cols)
        if len(g) <= max_posts:
            out.loc[g.index] = True
        else:
            pick = np.round(np.linspace(0, len(g) - 1, max_posts)).astype(int)
            out.loc[g.index[pick]] = True
    return out


def shrunk_bookmark_rate(df: pd.DataFrame, in_cap: pd.Series) -> pd.Series:
    """(bookmarks + r_tier) / (impressions + 1000) * 1000 using capped pooled tier rates."""
    if df.empty or "impressions" not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype="float64")
    imp = df["impressions"].astype("float64")
    if "bookmarks" in df.columns:
        bmk = df["bookmarks"].astype("float64")
    elif "cr_bmk" in df.columns:
        bmk = df["cr_bmk"].astype("float64") * imp / 1000.0
    else:
        return pd.Series(np.nan, index=df.index, dtype="float64")
    pool_mask = df["eligible"] & df["mature"] & in_cap & bmk.notna() & (imp > 0)
    if not pool_mask.any():
        return pd.Series(np.nan, index=df.index, dtype="float64")
    pool = pd.DataFrame({
        "tier": df.loc[pool_mask, "follower_tier"],
        "b": bmk[pool_mask],
        "i": imp[pool_mask],
    })
    grp = pool.groupby("tier", observed=True).sum()
    tier_r = (grp["b"] / grp["i"] * 1000.0).to_dict()
    row_r = df["follower_tier"].map(tier_r).astype("float64")
    out = pd.Series(np.nan, index=df.index, dtype="float64")
    valid = bmk.notna() & imp.notna() & row_r.notna()
    out.loc[valid] = (bmk[valid] + row_r[valid]) / (imp[valid] + SHRINKAGE_VIEWS) * 1000.0
    return out


def add_baselines(df: pd.DataFrame) -> tuple[pd.DataFrame, ReachModel]:
    out = add_eligibility(df)
    model = fit_reach_model(out)
    out["reach_expected"] = model.expected(out["followers_at_collection"])
    out["reach_vs_expected"] = out["impressions"] / out["reach_expected"]
    out["reach_model_reliable"] = model.reliable
    out["baseline_ratio"] = out["impressions"] / trailing_baseline(out)
    out["in_author_cap"] = even_author_cap(out, AUTHOR_CAP)
    out["cr_bmk_shrunk"] = shrunk_bookmark_rate(out, out["in_author_cap"])
    scored = out["eligible"] & out["mature"]
    out["pctile_in_tier"] = np.nan
    if scored.any():
        rank_col = (
            "cr_bmk_shrunk"
            if out.loc[scored, "cr_bmk_shrunk"].notna().any()
            else "reach_vs_expected"
        )
        out.loc[scored, "pctile_in_tier"] = (
            out[scored].groupby("follower_tier")[rank_col].rank(pct=True)
        )
    return out, model


def sanity_table(df: pd.DataFrame) -> pd.DataFrame:
    """Per follower tier summary over eligible, mature posts, for manual review."""
    s = df[df["eligible"] & df["mature"]]
    g = s.groupby("follower_tier")
    agg: dict[str, tuple[str, str]] = {
        "posts": ("post_id", "count"),
        "authors": ("author_handle", "nunique"),
        "median_views": ("impressions", "median"),
        "median_r_out": ("r_out", "median"),
        "median_reach_vs_expected": ("reach_vs_expected", "median"),
        "median_s_intent": ("s_intent", "median"),
        "median_cr_bmk": ("cr_bmk", "median"),
    }
    if "in_author_cap" in s.columns:
        agg["capped_posts"] = ("in_author_cap", "sum")
    if "cr_bmk_shrunk" in s.columns:
        agg["median_cr_bmk_shrunk"] = ("cr_bmk_shrunk", "median")
    t = g.agg(**agg)
    return t.reindex([x for x in TIER_LABELS if x in t.index]).reset_index()
