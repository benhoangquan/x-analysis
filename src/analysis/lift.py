"""Pooled lift tables, author-clustered bootstrap intervals, and evidence gates (Milestone 4)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.metrics.baselines import TIER_LABELS, even_author_cap

MIN_POSTS = 20
MIN_AUTHORS = 10


def pooled_cr_bmk(df: pd.DataFrame) -> float:
    """Total bookmarks / total impressions * 1000."""
    if df.empty:
        return float("nan")
    imp = float(df["impressions"].sum())
    return float(df["bookmarks"].sum() / imp * 1000.0) if imp > 0 else float("nan")


def analysis_corpus(df: pd.DataFrame) -> pd.DataFrame:
    """Filter-passing, eligible, mature, author-capped posts with valid views and bookmarks."""
    mask = df["eligible"].astype(bool) & df["mature"].astype(bool)
    mask &= df["is_researcher_post"] == True  # noqa: E712
    d = df[mask].dropna(subset=["impressions", "bookmarks"]).copy()
    d = d[d["impressions"] > 0].copy()
    if d.empty:
        return d
    if "in_author_cap" in d.columns:
        d = d[d["in_author_cap"].astype(bool)].copy()
    else:
        d = d[even_author_cap(d)].copy()
    return d


def _bootstrap_lift(
    df: pd.DataFrame,
    group_cols: list[str],
    tier_col: str,
    n_boot: int,
    seed: int,
) -> tuple[dict, dict]:
    by_tier = tier_col in group_cols
    key_cols = list(dict.fromkeys([*group_cols, tier_col])) if by_tier else list(group_cols)
    author_codes, uniques = pd.factorize(df["author_handle"], sort=False)
    n_authors = len(uniques)
    work = df[key_cols].copy()
    work["_au"] = author_codes
    work["_b"] = df["bookmarks"].astype("float64")
    work["_i"] = df["impressions"].astype("float64")
    au_cell = work.groupby(["_au", *key_cols], dropna=False, sort=False)[["_b", "_i"]].sum()
    au_cell = au_cell.reset_index()

    au_idx = au_cell["_au"].to_numpy()
    b_arr = au_cell["_b"].to_numpy()
    i_arr = au_cell["_i"].to_numpy()
    cell_keys = list(au_cell[group_cols].itertuples(index=False, name=None))
    uniq_cells = list(dict.fromkeys(cell_keys))
    cell_map = {k: idx for idx, k in enumerate(uniq_cells)}
    cell_code = np.array([cell_map[k] for k in cell_keys], dtype=int)

    if by_tier:
        tier_vals = list(au_cell[tier_col])
        uniq_tiers = list(dict.fromkeys(tier_vals))
        tier_map = {t: idx for idx, t in enumerate(uniq_tiers)}
        tier_code = np.array([tier_map[t] for t in tier_vals], dtype=int)
        cell_to_tier = np.array([tier_map[k[group_cols.index(tier_col)]] for k in uniq_cells])
    else:
        tier_code = np.zeros(len(au_cell), dtype=int)
        uniq_tiers = ["__all__"]
        cell_to_tier = np.zeros(len(uniq_cells), dtype=int)

    n_cells = len(uniq_cells)
    n_tiers = len(uniq_tiers)
    rates = np.full((n_boot, n_cells), np.nan, dtype="float64")
    lifts = np.full((n_boot, n_cells), np.nan, dtype="float64")
    rng = np.random.default_rng(seed)

    for b in range(n_boot):
        pick = rng.choice(n_authors, size=n_authors, replace=True)
        w = np.bincount(pick, minlength=n_authors)[au_idx]
        wb = b_arr * w
        wi = i_arr * w
        cb = np.bincount(cell_code, weights=wb, minlength=n_cells)
        ci = np.bincount(cell_code, weights=wi, minlength=n_cells)
        tb = np.bincount(tier_code, weights=wb, minlength=n_tiers)
        ti = np.bincount(tier_code, weights=wi, minlength=n_tiers)
        with np.errstate(divide="ignore", invalid="ignore"):
            cr = np.where(ci > 0, cb / ci * 1000.0, np.nan)
            tr = np.where(ti > 0, tb / ti * 1000.0, np.nan)
            base = tr[cell_to_tier]
            lf = np.where(base > 0, cr / base, np.nan)
        rates[b] = cr
        lifts[b] = lf

    rate_ci: dict = {}
    lift_ci: dict = {}
    for idx, k in enumerate(uniq_cells):
        rc = rates[:, idx]
        lc = lifts[:, idx]
        rate_ci[k] = (
            tuple(float(v) for v in np.nanpercentile(rc, [2.5, 97.5]))
            if not np.isnan(rc).all()
            else (float("nan"), float("nan"))
        )
        lift_ci[k] = (
            tuple(float(v) for v in np.nanpercentile(lc, [2.5, 97.5]))
            if not np.isnan(lc).all()
            else (float("nan"), float("nan"))
        )
    return rate_ci, lift_ci


def lift_table(
    df: pd.DataFrame,
    group_cols: list[str] | str,
    *,
    tier_col: str = "follower_tier",
    n_boot: int = 1000,
    seed: int = 20261112,
) -> pd.DataFrame:
    """Pooled CR_bmk lift table with 95% author-clustered bootstrap intervals and evidence gate."""
    cols = [group_cols] if isinstance(group_cols, str) else list(group_cols)
    out_cols = [
        *cols, "n_posts", "n_authors", "bookmarks", "impressions",
        "cr_bmk", "ci_low", "ci_high", "tier_cr_bmk",
        "lift_vs_tier", "lift_ci_low", "lift_ci_high", "passes_gate", "evidence",
    ]
    if df.empty:
        return pd.DataFrame(columns=out_cols)

    rate_ci, lift_ci = _bootstrap_lift(df, cols, tier_col, n_boot=n_boot, seed=seed)
    by_tier = tier_col in cols
    if by_tier:
        t_grp = df.groupby(tier_col)[["bookmarks", "impressions"]].sum()
        tier_rates = (t_grp["bookmarks"] / t_grp["impressions"].replace(0, np.nan) * 1000).to_dict()
    else:
        overall = pooled_cr_bmk(df)
        tier_rates = {"__all__": overall}

    rows = []
    for key, g in df.groupby(cols, dropna=False, sort=False):
        k_tup = key if isinstance(key, tuple) else (key,)
        bmk = float(g["bookmarks"].sum())
        imp = float(g["impressions"].sum())
        cr = bmk / imp * 1000.0 if imp > 0 else float("nan")
        base_key = k_tup[cols.index(tier_col)] if by_tier else "__all__"
        base_cr = float(tier_rates.get(base_key, float("nan")))
        lift = cr / base_cr if base_cr > 0 else float("nan")
        n_posts = len(g)
        n_authors = int(g["author_handle"].nunique())
        passes = n_posts >= MIN_POSTS and n_authors >= MIN_AUTHORS
        r_lo, r_hi = rate_ci.get(k_tup, (float("nan"), float("nan")))
        l_lo, l_hi = lift_ci.get(k_tup, (float("nan"), float("nan")))
        row = dict(zip(cols, k_tup, strict=True))
        row.update(
            n_posts=n_posts,
            n_authors=n_authors,
            bookmarks=bmk,
            impressions=imp,
            cr_bmk=cr,
            ci_low=r_lo,
            ci_high=r_hi,
            tier_cr_bmk=base_cr,
            lift_vs_tier=lift,
            lift_ci_low=l_lo,
            lift_ci_high=l_hi,
            passes_gate=passes,
            evidence="ok" if passes else "insufficient data",
        )
        rows.append(row)

    out = pd.DataFrame(rows, columns=out_cols)
    if by_tier and not out.empty:
        rank = {t: i for i, t in enumerate(TIER_LABELS)}
        out["_t"] = out[tier_col].map(lambda t: rank.get(t, 99))
        out = out.sort_values(
            ["_t", "passes_gate", "lift_vs_tier"], ascending=[True, False, False]
        ).drop(columns=["_t"])
    elif not out.empty:
        out = out.sort_values(["passes_gate", "lift_vs_tier"], ascending=[False, False])
    return out.reset_index(drop=True)
