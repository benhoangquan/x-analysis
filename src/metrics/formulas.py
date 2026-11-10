"""The three AGENTS.md formulas as pure vectorised functions (pandas Series or numpy arrays)."""

from __future__ import annotations

import pandas as pd

FOLLOWER_FLOOR = 100
IMPRESSION_FLOOR = 1


def outperformance_ratio(impressions: pd.Series, followers: pd.Series) -> pd.Series:
    """R_out = impressions / max(followers, 100)."""
    return impressions / followers.clip(lower=FOLLOWER_FLOOR)


def high_intent_score(
    bookmarks: pd.Series,
    quotes: pd.Series,
    reposts: pd.Series,
    replies: pd.Series,
    likes: pd.Series,
    impressions: pd.Series,
) -> pd.Series:
    """S_intent = (3*bookmarks + 2*(quotes+reposts) + 2*replies + likes) / max(impressions, 1)."""
    numerator = 3 * bookmarks + 2 * (quotes + reposts) + 2 * replies + likes
    return numerator / impressions.clip(lower=IMPRESSION_FLOOR)


def bookmark_conversion_rate(bookmarks: pd.Series, impressions: pd.Series) -> pd.Series:
    """CR_bmk = bookmarks / max(impressions, 1) * 1000 (bookmarks per 1k views)."""
    return bookmarks / impressions.clip(lower=IMPRESSION_FLOOR) * 1000


def add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Append r_out, s_intent, cr_bmk. Missing impressions or bookmarks yield NaN, not 0."""
    out = df.copy()
    imp = out["impressions"].astype("float64")
    bmk = out["bookmarks"].astype("float64")
    out["r_out"] = outperformance_ratio(imp, out["followers_at_collection"])
    out["s_intent"] = high_intent_score(
        bmk, out["quotes"], out["reposts"], out["replies"], out["likes"], imp
    )
    out["cr_bmk"] = bookmark_conversion_rate(bmk, imp)
    return out
