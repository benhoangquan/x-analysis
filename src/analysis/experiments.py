"""Hypothesis-test harness for notes/40_experiments: E1-E6 entry points, estimators, and ledger.

Run: uv run python -m src.analysis.experiments E4 [--data PATH] [--status dry_run]
"""

from __future__ import annotations

import argparse
import itertools
import re
import subprocess
import warnings
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.enrichment.rules import VENUE_RE, thread_cues
from src.ingestion.panel import PAPERS, arxiv_ids
from src.metrics.baselines import even_author_cap, fit_reach_model, shrunk_bookmark_rate

PAPER_S2_META = Path("data/processed/paper_s2_meta.csv")

LEDGER = Path("notes/40_experiments/results.tsv")
LEDGER_COLS = [
    "date", "commit", "exp", "test", "data_version", "label_version", "estimate",
    "ci_low", "ci_high", "n_posts", "n_authors", "n_strata", "status", "description",
]
MIN_POSTS, MIN_AUTHORS, MIN_STRATA = 20, 10, 20
SMALLEST_EFFECT = 1.2
N_BOOT = 2000
SEED = 20261112

CURIOSITY_RE = re.compile(
    r"\b(?:do you know|did you know|ever wondered|here'?s why|you need to know|"
    r"nobody is talking)\b",
    re.I,
)


# ---------------------------------------------------------------- estimator


def mh_rate_ratio(
    df: pd.DataFrame, arm_col: str, a: set[str], b: set[str], count: str, expo: str, strata: str
) -> float:
    """Mantel-Haenszel rate ratio of arm set `a` over `b`; only strata holding both contribute."""
    d = df[df[arm_col].isin(a | b)]
    g = d.assign(_a=d[arm_col].isin(a)).groupby([strata, "_a"])[[count, expo]].sum().unstack("_a")
    g = g.dropna()
    if g.empty or (count, True) not in g or (count, False) not in g:
        return float("nan")
    cA, eA = g[(count, True)], g[(expo, True)]
    cB, eB = g[(count, False)], g[(expo, False)]
    ok = (eA > 0) & (eB > 0)
    if not ok.any():
        return float("nan")
    num = float((cA * eB / (eA + eB))[ok].sum())
    den = float((cB * eA / (eA + eB))[ok].sum())
    if num > 0 and den > 0:
        return num / den
    if num == 0 and den == 0:
        return float("nan")
    num_h = float(((cA + 0.5) * eB / (eA + eB))[ok].sum())
    den_h = float(((cB + 0.5) * eA / (eA + eB))[ok].sum())
    return num_h / den_h if den_h > 0 else float("nan")


def gm_ratio_within_strata(
    df: pd.DataFrame, arm_col: str, a: set[str], b: set[str], val_col: str, strata: str
) -> float:
    """Exponentiated mean within-stratum difference in mean log value (arm a minus arm b)."""
    d = df[df[arm_col].isin(a | b) & (df[val_col] > 0)].copy()
    if d.empty:
        return float("nan")
    d["_a"] = d[arm_col].isin(a)
    d["_logv"] = np.log(d[val_col].astype("float64"))
    g = d.groupby([strata, "_a"])["_logv"].mean().unstack("_a").dropna()
    if g.empty or True not in g or False not in g:
        return float("nan")
    return float(np.exp((g[True] - g[False]).mean()))


def cluster_bootstrap(
    df: pd.DataFrame,
    fn,
    cluster: str,
    n_boot: int = N_BOOT,
    seed: int = SEED,
    percentiles: tuple[float, float] = (0.5, 99.5),
) -> tuple[float, float, float]:
    """Point estimate and percentile interval, resampling whole clusters."""
    rng = np.random.default_rng(seed)
    groups = {k: v for k, v in df.groupby(cluster)}
    keys = np.array(list(groups))
    est = fn(df)
    if not len(keys):
        return float("nan"), float("nan"), float("nan")
    draws = []
    for _ in range(n_boot):
        pick = rng.choice(keys, size=len(keys), replace=True)
        # relabel each draw so repeated clusters stay distinct strata
        parts = [groups[k].assign(_boot=i) for i, k in enumerate(pick)]
        draws.append(fn(pd.concat(parts)))
    arr = np.asarray(draws, dtype="float64")
    if np.isnan(arr).all():
        return est, float("nan"), float("nan")
    lo, hi = np.nanpercentile(arr, list(percentiles))
    return est, float(lo), float(hi)


def shuffle_within(df: pd.DataFrame, col: str, strata: str, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = df.copy()
    out[col] = out.groupby(strata)[col].transform(lambda s: rng.permutation(s.to_numpy()))
    return out


def verdict(lo: float, hi: float, prediction: str) -> str:
    """README rule. prediction: 'up' (RR > 1) or 'null' (no lift)."""
    if np.isnan(lo) or np.isnan(hi):
        return "inconclusive"
    if prediction == "up":
        if lo > 1:
            return "supported"
        if hi < 1 or (lo >= 1 / SMALLEST_EFFECT and hi <= SMALLEST_EFFECT):
            return "refuted"
        return "inconclusive"
    if hi < SMALLEST_EFFECT:
        return "supported"
    return "refuted" if lo > 1 else "inconclusive"


@dataclass
class Spec:
    exp: str
    name: str
    arm_col: str
    a: set[str]
    b: set[str]
    count: str
    expo: str
    strata: str
    prediction: str
    cluster: str = "author_handle"
    min_strata: int = MIN_STRATA
    estimator: str = "mh"  # "mh" | "gm"


def _estimate(x: pd.DataFrame, t: Spec) -> float:
    s = t.strata
    if "_boot" in x and t.strata == t.cluster:
        s = "_boot_stratum"
        x = x.assign(_boot_stratum=x[t.strata].astype(str) + "|" + x["_boot"].astype(str))
    if t.estimator == "gm":
        return gm_ratio_within_strata(x, t.arm_col, t.a, t.b, t.count, s)
    return mh_rate_ratio(x, t.arm_col, t.a, t.b, t.count, t.expo, s)


def run_test(
    df: pd.DataFrame,
    t: Spec,
    status_override: str | None,
    desc: str,
    n_boot: int = N_BOOT,
    with_control: bool = True,
) -> dict:
    d = df[df[t.arm_col].isin(t.a | t.b)].copy()
    d["_arm"] = d[t.arm_col].isin(t.a)
    by_arm = d.groupby("_arm").agg(n=("post_id", "size"), au=("author_handle", "nunique"))
    both = d.groupby(t.strata)["_arm"].nunique().eq(2)
    n_strata = int(both.sum())
    row = dict(
        exp=t.exp, test=t.name, n_posts=len(d), n_authors=d["author_handle"].nunique(),
        n_strata=n_strata,
    )
    gate = (
        len(by_arm) == 2
        and (by_arm["n"] >= MIN_POSTS).all()
        and (by_arm["au"] >= MIN_AUTHORS).all()
        and n_strata >= t.min_strata
    )
    est, lo, hi = (
        cluster_bootstrap(d, lambda x: _estimate(x, t), t.cluster, n_boot=n_boot)
        if len(d)
        else (np.nan,) * 3
    )
    row.update(estimate=est, ci_low=lo, ci_high=hi)
    row["status"] = status_override or (
        verdict(lo, hi, t.prediction) if gate else "insufficient"
    )
    if status_override and not gate:
        desc += " [gate failed]"
    row["description"] = desc
    if with_control:
        nc = shuffle_within(d, t.arm_col, t.strata)
        nest, nlo, nhi = (
            cluster_bootstrap(nc, lambda x: _estimate(x, t), t.cluster, n_boot=min(500, n_boot))
            if len(nc)
            else (np.nan,) * 3
        )
        row["_nc"] = (nest, nlo, nhi, bool(nlo <= 1 <= nhi) if not np.isnan(nlo) else False)
    else:
        row["_nc"] = None
    return row


# ---------------------------------------------------------------- ledger


def git_commit() -> str:
    try:
        h = subprocess.check_output(["git", "rev-parse", "--short=7", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
        return h + ("+dirty" if dirty else "")
    except Exception:  # noqa: BLE001
        return "-"


def append_ledger(rows: list[dict], data_version: str, label_version: str) -> None:
    today, commit = date.today().isoformat(), git_commit()
    lines = []
    for r in rows:
        r = {**r, "date": today, "commit": commit, "data_version": data_version,
             "label_version": label_version}
        out = []
        for c in LEDGER_COLS:
            v = r.get(c, "")
            out.append(f"{v:.4f}" if isinstance(v, float) else str(v))
        lines.append("\t".join(out))
    with LEDGER.open("a") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- data


def _read_df(data: str | Path | pd.DataFrame) -> pd.DataFrame:
    return data.copy() if isinstance(data, pd.DataFrame) else pd.read_parquet(data)


def load(
    path: str | Path | pd.DataFrame,
    cohorts: set[str],
    *,
    apply_cap: bool = True,
    apply_researcher_filter: bool = True,
) -> pd.DataFrame:
    d = _read_df(path)
    mask = d["eligible"].astype(bool) & d["mature"].astype(bool)
    if apply_researcher_filter:
        mask &= d["is_researcher_post"] == True  # noqa: E712
    if apply_cap and "in_author_cap" in d.columns:
        mask &= d["in_author_cap"].astype(bool)
    if cohorts:
        mask &= d["cohort"].isin(cohorts)
    d = d[mask].dropna(subset=["impressions", "bookmarks"]).copy()
    d["impressions"] = d["impressions"].clip(lower=1)
    return d


def _first_paper_id(df: pd.DataFrame) -> pd.Series:
    if "paper_id" in df.columns:
        raw = df["paper_id"].fillna("").astype(str).str.split(";").str[0].str.strip()
    else:
        raw = pd.Series("", index=df.index)
    if "text" in df.columns:
        miss = raw == ""
        if miss.any():
            found = (
                df.loc[miss, "text"]
                .fillna("")
                .map(lambda t: (arxiv_ids({"text": t}) or [""])[0])
            )
            raw.loc[miss] = found
    return raw


def _attach_paper_meta(
    df: pd.DataFrame,
    papers_path: Path = PAPERS,
    s2_meta: pd.DataFrame | None = None,
) -> pd.DataFrame:
    out = df.copy()
    out["first_paper_id"] = _first_paper_id(out)
    if papers_path.exists():
        pm = pd.read_csv(papers_path, dtype={"paper_id": str})
        keep = [
            c for c in ("paper_id", "primary_category", "has_code", "arxiv_v1", "n_authors")
            if c in pm.columns and c not in out.columns
        ]
        if keep:
            out = out.merge(
                pm[["paper_id", *keep]],
                left_on="first_paper_id",
                right_on="paper_id",
                how="left",
                suffixes=("", "_pm"),
            )
            if "paper_id_pm" in out.columns:
                out = out.drop(columns=["paper_id_pm"])
    if s2_meta is not None and not s2_meta.empty:
        keep_s2 = [
            c for c in ("venue_accepted", "max_h_index", "median_h_index")
            if c in s2_meta.columns and c not in out.columns
        ]
        if keep_s2:
            out = out.merge(
                s2_meta[["paper_id", *keep_s2]],
                left_on="first_paper_id",
                right_on="paper_id",
                how="left",
                suffixes=("", "_s2"),
            )
            if "paper_id_s2" in out.columns:
                out = out.drop(columns=["paper_id_s2"])
    if "primary_category" not in out.columns:
        out["primary_category"] = "unknown"
    else:
        out["primary_category"] = out["primary_category"].fillna("unknown")
    return out


def _add_s_intent_num(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    bmk = out["bookmarks"].astype("float64")
    q = out["quotes"].astype("float64") if "quotes" in out.columns else 0.0
    rp = out["reposts"].astype("float64") if "reposts" in out.columns else 0.0
    rep = out["replies"].astype("float64") if "replies" in out.columns else 0.0
    lk = out["likes"].astype("float64") if "likes" in out.columns else 0.0
    out["s_intent_num"] = 3 * bmk + 2 * (q + rp) + 2 * rep + lk
    return out


def framing_proxy(text: pd.Series, has_number: pd.Series) -> pd.Series:
    """Rule proxy for `framing` until Jev labels exist (dry runs only)."""
    gap = text.str.contains(CURIOSITY_RE)
    q = text.str.contains(r"\?") & ~gap
    emp = has_number & ~gap & ~q
    return pd.Series(
        np.select([gap, q, emp], ["CURIOSITY_GAP", "OPEN_QUESTION", "DECLARATIVE_EMPIRICAL"],
                  "DECLARATIVE_OTHER"),
        index=text.index,
    )


def _label_version(df: pd.DataFrame) -> str:
    if "label_version" in df.columns and df["label_version"].notna().any():
        return str(df["label_version"].dropna().iloc[0])
    return "-"


def summary(rows: list[dict]) -> str:
    out = ["--- summary ---"]
    for r in rows:
        nc = r.pop("_nc", None)
        ci_l, ci_h = r.get("ci_low"), r.get("ci_high")
        ci_txt = (
            f"[{ci_l:.3f}, {ci_h:.3f}]"
            if isinstance(ci_l, float) and isinstance(ci_h, float)
            else "[n/a]"
        )
        est = (
            f"{r['estimate']:.3f}"
            if isinstance(r.get("estimate"), float)
            else str(r.get("estimate"))
        )
        out.append(
            f"{r['exp']} {r['test']}: est={est} ci={ci_txt} "
            f"n_posts={r['n_posts']} n_authors={r['n_authors']} "
            f"n_strata={r['n_strata']} status={r['status']}"
        )
        if nc:
            out.append(
                f"  control: est={nc[0]:.3f} ci=[{nc[1]:.3f}, {nc[2]:.3f}] "
                f"{'pass' if nc[3] else 'FAIL'}"
            )
    return "\n".join(out)


# ---------------------------------------------------------------- E1


def run_e1(
    data: str | Path | pd.DataFrame,
    status: str | None,
    cohorts: set[str],
    n_boot: int = N_BOOT,
    papers_path: Path = PAPERS,
) -> tuple[list[dict], str]:
    d = load(data, cohorts, apply_cap=False, apply_researcher_filter=False)
    d = _attach_paper_meta(d, papers_path=papers_path)
    d = d[(d["first_paper_id"] != "") & d["poster_role"].notna()].copy()
    d = d[even_author_cap(d, max_posts=10)].copy()
    d = _add_s_intent_num(d)
    d["tier_cat"] = d["follower_tier"].astype(str) + "|" + d["primary_category"].astype(str)

    researchers = {"ORIGINAL_RESEARCHER", "CREDENTIALED_RESEARCHER"}
    primary = [
        Spec("E1", "H1a", "poster_role", {"NON_RESEARCHER"}, researchers, "impressions",
             "impressions", "tier_cat", "up", cluster="author_handle", min_strata=5,
             estimator="gm"),
        Spec("E1", "H1b-O", "poster_role", {"ORIGINAL_RESEARCHER"}, {"NON_RESEARCHER"},
             "s_intent_num", "impressions", "tier_cat", "up",
             cluster="author_handle", min_strata=5),
        Spec("E1", "H1b-C", "poster_role", {"CREDENTIALED_RESEARCHER"}, {"NON_RESEARCHER"},
             "s_intent_num", "impressions", "tier_cat", "up",
             cluster="author_handle", min_strata=5),
    ]
    secondary = [
        Spec("E1", "H1a-wp", "poster_role", {"NON_RESEARCHER"}, researchers, "impressions",
             "impressions", "first_paper_id", "up", cluster="first_paper_id", min_strata=20,
             estimator="gm"),
        Spec("E1", "H1b-O-wp", "poster_role", {"ORIGINAL_RESEARCHER"}, {"NON_RESEARCHER"},
             "s_intent_num", "impressions", "first_paper_id", "up", cluster="first_paper_id",
             min_strata=20),
        Spec("E1", "H1b-C-wp", "poster_role", {"CREDENTIALED_RESEARCHER"}, {"NON_RESEARCHER"},
             "s_intent_num", "impressions", "first_paper_id", "up", cluster="first_paper_id",
             min_strata=20),
    ]
    rows = [
        run_test(d, t, status, f"cross-paper tier x category ({len(d)} posts)", n_boot=n_boot)
        for t in primary
    ]
    rows += [
        run_test(
            d, t, status or "secondary",
            f"secondary within-paper ({len(d)} posts)",
            n_boot=min(500, n_boot), with_control=False,
        )
        for t in secondary
    ]
    return rows, _label_version(d)


# ---------------------------------------------------------------- E2


def run_e2(
    data: str | Path | pd.DataFrame,
    status: str | None,
    cohorts: set[str],
    n_boot: int = N_BOOT,
    papers_path: Path = PAPERS,
) -> tuple[list[dict], str]:
    d = load(data, cohorts, apply_cap=False, apply_researcher_filter=True)
    d = _attach_paper_meta(d, papers_path=papers_path)
    d = d[d["first_paper_id"] != ""].copy()
    d = d[even_author_cap(d, max_posts=10)].copy()
    d = _add_s_intent_num(d)

    summary_hooks = (
        {"PAPER_ANNOUNCEMENT"}
        if "hook_archetype" in d.columns and (d["hook_archetype"] == "PAPER_ANNOUNCEMENT").any()
        else {"OTHER"}
    )
    t_mask = (d["visual_type"] == "PAPER_FIGURE") & (d["hook_archetype"] == "CONTESTED_CLAIM")
    c_mask = (d["visual_type"] == "NONE") & (d["hook_archetype"].isin(summary_hooks))
    d["e2_arm"] = np.select([t_mask, c_mask], ["T", "C"], default="")
    d["paper_tier"] = d["first_paper_id"].astype(str) + "|" + d["follower_tier"].astype(str)

    spec = Spec(
        "E2", "H2", "e2_arm", {"T"}, {"C"}, "s_intent_num", "impressions",
        "first_paper_id", "up", cluster="first_paper_id", min_strata=20,
    )
    row = run_test(d, spec, status, f"within-paper figure+contested vs summary ({len(d)} posts)",
                   n_boot=n_boot)
    rob = mh_rate_ratio(d, "e2_arm", {"T"}, {"C"}, "s_intent_num", "impressions", "paper_tier")
    if (
        not status
        and row["status"] in ("supported", "refuted")
        and not np.isnan(rob)
        and ((row["estimate"] > 1 and rob < 1) or (row["estimate"] < 1 and rob > 1))
    ):
        row["status"] = "inconclusive"
        row["description"] += f"; paper x tier robustness opposite ({rob:.3f})"
    return [row], _label_version(d)


# ---------------------------------------------------------------- E3


def _auc_oof(
    df: pd.DataFrame,
    y: np.ndarray,
    num_cols: list[str],
    cat_cols: list[str],
    seeds: list[int],
) -> np.ndarray:
    transformers = []
    if num_cols:
        transformers.append(
            ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]),
             num_cols)
        )
    if cat_cols:
        transformers.append(
            ("cat", Pipeline([
                ("imp", SimpleImputer(strategy="constant", fill_value="missing")),
                ("oh", OneHotEncoder(handle_unknown="ignore")),
            ]), cat_cols)
        )
    pre = ColumnTransformer(transformers)
    groups = df["author_handle"].to_numpy()
    n_splits = min(5, int(pd.Series(groups).nunique()))
    oof_sum = np.zeros(len(df), dtype="float64")
    for s in seeds:
        cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=s)
        pred = np.zeros(len(df), dtype="float64")
        for tr, va in cv.split(df, y, groups):
            if len(np.unique(y[tr])) < 2:
                pred[va] = float(np.mean(y[tr]))
                continue
            pipe = Pipeline([("pre", pre), ("clf", LogisticRegression(C=1.0, max_iter=1000))])
            pipe.fit(df.iloc[tr], y[tr])
            pred[va] = pipe.predict_proba(df.iloc[va])[:, 1]
        oof_sum += pred
    return oof_sum / len(seeds)


def _prepare_paper_model_frame(
    d: pd.DataFrame, papers_path: Path, s2_meta: pd.DataFrame | None
) -> pd.DataFrame:
    out = _attach_paper_meta(d, papers_path=papers_path, s2_meta=s2_meta)
    out["log_followers"] = np.log(out["followers_at_collection"].clip(lower=100).astype("float64"))
    if "arxiv_v1" in out.columns:
        v1 = pd.to_datetime(out["arxiv_v1"], utc=True, errors="coerce")
        cr = pd.to_datetime(out["created_at"], utc=True, errors="coerce")
        out["paper_age_days"] = (cr - v1).dt.total_seconds() / 86400
    if "hype_flags" in out.columns:
        out["has_hype"] = out["hype_flags"].fillna("").astype(str).str.strip().ne("")
    return out


def _available_cols(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in df.columns and df[c].notna().any()]


def run_e3(
    data: str | Path | pd.DataFrame,
    status: str | None,
    cohorts: set[str],
    s2_meta: pd.DataFrame | None = None,
    papers_path: Path = PAPERS,
    n_boot: int = N_BOOT,
    n_perm: int = 200,
) -> tuple[list[dict], str]:
    if s2_meta is None and papers_path == PAPERS and PAPER_S2_META.exists():
        s2_meta = pd.read_csv(PAPER_S2_META, dtype={"paper_id": str})
    d = load(data, cohorts, apply_cap=False, apply_researcher_filter=True)
    d = _prepare_paper_model_frame(d, papers_path=papers_path, s2_meta=s2_meta)
    d = d[d["first_paper_id"] != ""].copy()
    is_roster = d["cohort"] == "ROSTER"
    cap = pd.Series(False, index=d.index)
    if is_roster.any():
        cap.loc[is_roster] = even_author_cap(d[is_roster], max_posts=40)
    if (~is_roster).any():
        cap.loc[~is_roster] = even_author_cap(d[~is_roster], max_posts=10)
    d = d[cap].copy()
    if "cr_bmk_shrunk" not in d.columns or d["cr_bmk_shrunk"].isna().all():
        d["cr_bmk_shrunk"] = shrunk_bookmark_rate(d, pd.Series(True, index=d.index))
    d = d.dropna(subset=["cr_bmk_shrunk"]).copy()

    n_posts, n_authors = len(d), int(d["author_handle"].nunique()) if len(d) else 0
    if n_posts:
        tier_med = d.groupby("follower_tier")["cr_bmk_shrunk"].transform("median")
        d["top_half"] = (d["cr_bmk_shrunk"] > tier_med).astype(int)
    else:
        d["top_half"] = pd.Series(dtype=int)

    gate = n_posts >= 400 and n_authors >= 80 and d["top_half"].nunique() == 2
    if not gate and not status:
        return [dict(
            exp="E3", test="H3", estimate=float("nan"), ci_low=float("nan"), ci_high=float("nan"),
            n_posts=n_posts, n_authors=n_authors, n_strata="", status="insufficient",
            description="fewer than 400 paper-linked posts or 80 authors", _nc=None,
        )], _label_version(d)

    c_num = _available_cols(d, ["log_followers", "max_h_index"])
    c_cat = _available_cols(d, ["follower_tier", "poster_role"])
    x_paper_num = _available_cols(d, ["paper_age_days"])
    x_paper_cat = _available_cols(d, ["primary_category", "has_code", "venue_accepted"])
    x_vis_cat = _available_cols(d, ["visual_type"])
    x_copy_num = _available_cols(
        d, ["technical_rigor_score", "char_len", "thread_length", "posted_hour_utc"]
    )
    x_copy_cat = _available_cols(
        d, ["hook_archetype", "framing", "has_number", "mentions_venue", "has_hype"]
    )
    x_num = x_paper_num + x_copy_num
    x_cat = x_paper_cat + x_vis_cat + x_copy_cat

    y = d["top_half"].to_numpy()
    if n_posts < 5 or n_authors < 5 or d["top_half"].nunique() < 2 or not (x_num or x_cat):
        return [dict(
            exp="E3", test="H3", estimate=float("nan"), ci_low=float("nan"), ci_high=float("nan"),
            n_posts=n_posts, n_authors=n_authors, n_strata="",
            status=status or "insufficient",
            description="insufficient data or controllable features for E3", _nc=None,
        )], _label_version(d)

    seeds = [SEED + i for i in range(5)]
    oof_m0 = _auc_oof(d, y, c_num, c_cat, seeds)
    oof_m1 = _auc_oof(d, y, c_num + x_num, c_cat + x_cat, seeds)
    auc_m0 = float(roc_auc_score(y, oof_m0))
    auc_m1 = float(roc_auc_score(y, oof_m1))
    delta = auc_m1 - auc_m0

    rng = np.random.default_rng(SEED)
    authors = d["author_handle"].to_numpy()
    uniq_au = np.unique(authors)
    au_idx = {a: np.flatnonzero(authors == a) for a in uniq_au}
    boot_deltas = []
    for _ in range(n_boot):
        pick = rng.choice(uniq_au, size=len(uniq_au), replace=True)
        idx = np.concatenate([au_idx[a] for a in pick])
        if len(np.unique(y[idx])) < 2:
            continue
        boot_deltas.append(roc_auc_score(y[idx], oof_m1[idx]) - roc_auc_score(y[idx], oof_m0[idx]))
    ci_lo, ci_hi = (
        tuple(float(v) for v in np.nanpercentile(boot_deltas, [0.5, 99.5]))
        if boot_deltas
        else (float("nan"), float("nan"))
    )

    x_cols = x_num + x_cat
    perm_deltas = []
    for i in range(n_perm):
        dp = d.copy()
        for _, grp in dp.groupby("follower_tier"):
            perm_idx = rng.permutation(grp.index.to_numpy())
            dp.loc[grp.index, x_cols] = dp.loc[perm_idx, x_cols].to_numpy()
        oof_p = _auc_oof(dp, y, c_num + x_num, c_cat + x_cat, [SEED + 100 + i])
        perm_deltas.append(float(roc_auc_score(y, oof_p)) - auc_m0)
    null_p99 = float(np.nanpercentile(perm_deltas, 99)) if perm_deltas else float("nan")

    if status:
        v = status
    elif delta >= 0.03 and ci_lo > 0 and delta > null_p99 and auc_m1 >= 0.60:
        v = "supported"
    elif ci_hi < 0.02:
        v = "refuted"
    else:
        v = "inconclusive"

    rows = [dict(
        exp="E3", test="H3", estimate=delta, ci_low=ci_lo, ci_high=ci_hi,
        n_posts=n_posts, n_authors=n_authors, n_strata="", status=v,
        description=(
            f"delta_auc={delta:.4f} (M0={auc_m0:.3f}, M1={auc_m1:.3f}, "
            f"perm99={null_p99:.4f})" + ("" if gate else " [gate failed]")
        ),
        _nc=None,
    )]
    blocks = {
        "drop:paper": (x_paper_num, x_paper_cat),
        "drop:visual": ([], x_vis_cat),
        "drop:copy": (x_copy_num, x_copy_cat),
    }
    for bname, (bn, bc) in blocks.items():
        if not (bn or bc):
            continue
        rn = [c for c in x_num if c not in bn]
        rc = [c for c in x_cat if c not in bc]
        oof_drop = _auc_oof(d, y, c_num + rn, c_cat + rc, seeds)
        loss = auc_m1 - float(roc_auc_score(y, oof_drop))
        rows.append(dict(
            exp="E3", test=bname, estimate=loss, ci_low="", ci_high="",
            n_posts=n_posts, n_authors=n_authors, n_strata="",
            status=status or "secondary",
            description=f"AUC drop when {bname.split(':')[1]} block removed from M1",
            _nc=None,
        ))
    return rows, _label_version(d)


# ---------------------------------------------------------------- E4


def run_e4(
    data: str | Path | pd.DataFrame, status: str | None, cohorts: set[str], n_boot: int = N_BOOT
) -> tuple[list[dict], str]:
    d = load(data, cohorts)
    has_jev = "framing" in d.columns and d["framing"].notna().any()
    if not has_jev:
        d["framing"] = framing_proxy(d["text"].fillna(""), d["has_number"])

    is_opener = pd.Series(False, index=d.index)
    if "post_kind" in d.columns:
        is_opener |= d["post_kind"].astype(str).eq("thread_opener")
    if "is_thread_opener" in d.columns:
        is_opener |= d["is_thread_opener"].fillna(False).astype(bool)
    elif "text" in d.columns:
        is_opener |= d["text"].fillna("").map(lambda t: thread_cues(t)[0])
    d_no_thread = d[~is_opener].copy()

    decl = {"DECLARATIVE_EMPIRICAL", "DECLARATIVE_OTHER"}
    if "likes" in d:
        d["likes"] = d["likes"].clip(lower=0)
    if "likes" in d_no_thread:
        d_no_thread["likes"] = d_no_thread["likes"].clip(lower=0)

    specs = [
        (d_no_thread, Spec("E4", "H4a", "framing", {"OPEN_QUESTION"}, decl, "replies",
                           "impressions", "author_handle", "up")),
        (d, Spec("E4", "H4b", "framing", {"DECLARATIVE_EMPIRICAL"}, {"OPEN_QUESTION"},
                 "bookmarks", "likes", "author_handle", "up")),
        (d, Spec("E4", "H4c", "framing", {"CURIOSITY_GAP"}, {"DECLARATIVE_EMPIRICAL"},
                 "bookmarks", "impressions", "author_handle", "null")),
    ]
    prefix = "" if has_jev else "rule-proxy framing; "
    rows = [
        run_test(
            sub, t, status,
            f"{prefix}{t.name} on {len(sub)} filter-passing posts",
            n_boot=n_boot,
        )
        for sub, t in specs
    ]
    return rows, _label_version(d)


# ---------------------------------------------------------------- E5


def _oof_r2(
    df: pd.DataFrame, y: np.ndarray, num_cols: list[str], cat_cols: list[str], groups: np.ndarray
) -> float:
    if not (num_cols or cat_cols):
        return 0.0
    transformers = []
    if num_cols:
        transformers.append(
            ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]),
             num_cols)
        )
    if cat_cols:
        transformers.append(
            ("cat", Pipeline([
                ("imp", SimpleImputer(strategy="constant", fill_value="missing")),
                ("oh", OneHotEncoder(handle_unknown="ignore")),
            ]), cat_cols)
        )
    pre = ColumnTransformer(transformers)
    n_splits = min(5, int(pd.Series(groups).nunique()))
    if n_splits < 2:
        return 0.0
    cv = GroupKFold(n_splits=n_splits)
    pred = np.zeros(len(df), dtype="float64")
    for tr, va in cv.split(df, y, groups):
        pipe = Pipeline([("pre", pre), ("reg", Ridge(alpha=1.0))])
        pipe.fit(df.iloc[tr], y[tr])
        pred[va] = pipe.predict(df.iloc[va])
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    if ss_tot <= 0:
        return 0.0
    return float(1.0 - np.sum((y - pred) ** 2) / ss_tot)


def _shapley_r2(
    df: pd.DataFrame,
    y: np.ndarray,
    blocks: dict[str, tuple[list[str], list[str]]],
    groups: np.ndarray,
) -> dict[str, float]:
    names = list(blocks)
    n = len(names)
    r2_cache: dict[tuple[int, ...], float] = {(0,) * n: 0.0}
    for mask in itertools.product((0, 1), repeat=n):
        if sum(mask) == 0:
            continue
        num_c = [c for i, bit in enumerate(mask) if bit for c in blocks[names[i]][0]]
        cat_c = [c for i, bit in enumerate(mask) if bit for c in blocks[names[i]][1]]
        r2_cache[mask] = _oof_r2(df, y, num_c, cat_c, groups)

    fact = [1] * (n + 1)
    for k in range(1, n + 1):
        fact[k] = fact[k - 1] * k
    shares = {name: 0.0 for name in names}
    for i, name in enumerate(names):
        for mask in itertools.product((0, 1), repeat=n):
            if mask[i] == 1:
                continue
            s_size = sum(mask)
            weight = fact[s_size] * fact[n - s_size - 1] / fact[n]
            with_i = tuple(1 if j == i else mask[j] for j in range(n))
            shares[name] += weight * (r2_cache[with_i] - r2_cache[mask])
    return shares


def _paper_icc(y: np.ndarray, groups: np.ndarray) -> float:
    s = pd.DataFrame({"y": y, "g": groups}).groupby("g")["y"]
    sizes = s.size().to_numpy(dtype="float64")
    k = len(sizes)
    n = float(sizes.sum())
    if k < 2 or n <= k:
        return float("nan")
    grand = float(np.mean(y))
    ssb = float(sum(sz * (m - grand) ** 2 for sz, m in zip(sizes, s.mean(), strict=True)))
    ssw = float(sum(((g - m) ** 2).sum() for (_, g), m in zip(s, s.mean(), strict=True)))
    msb, msw = ssb / (k - 1), ssw / (n - k)
    k0 = (n - float(np.sum(sizes**2)) / n) / (k - 1)
    denom = msb + (k0 - 1) * msw
    if denom <= 0:
        return 0.0
    return float(np.clip((msb - msw) / denom, 0.0, 1.0))


def run_e5(
    data: str | Path | pd.DataFrame,
    status: str | None,
    cohorts: set[str],
    s2_meta: pd.DataFrame | None = None,
    papers_path: Path = PAPERS,
    n_boot: int = 200,
) -> tuple[list[dict], str]:
    if s2_meta is None and papers_path == PAPERS and PAPER_S2_META.exists():
        s2_meta = pd.read_csv(PAPER_S2_META, dtype={"paper_id": str})
    d = load(data, cohorts, apply_cap=False, apply_researcher_filter=False)
    d = _prepare_paper_model_frame(d, papers_path=papers_path, s2_meta=s2_meta)
    d = d[d["first_paper_id"] != ""].copy()
    if "cr_bmk_shrunk" not in d.columns or d["cr_bmk_shrunk"].isna().all():
        d["cr_bmk_shrunk"] = shrunk_bookmark_rate(d, pd.Series(True, index=d.index))
    posters_per_paper = d.groupby("first_paper_id")["author_handle"].nunique()
    keep_papers = posters_per_paper[posters_per_paper >= 3].index
    d = d[d["first_paper_id"].isin(keep_papers)].copy()
    d["log_impressions"] = np.log(d["impressions"].clip(lower=1).astype("float64"))
    d["log_cr_bmk_shrunk"] = np.log(d["cr_bmk_shrunk"].clip(lower=1e-3).astype("float64"))

    raw_blocks = {
        "paper_content": (["paper_age_days"], ["primary_category", "has_code", "venue_accepted"]),
        "paper_authors": (["max_h_index", "median_h_index", "n_authors"], []),
        "posting_account": (["log_followers"], ["follower_tier", "poster_role", "cohort"]),
        "visual": ([], ["visual_type"]),
        "copy": (
            ["technical_rigor_score", "char_len", "thread_length"],
            ["hook_archetype", "framing", "has_number", "hype_flags"],
        ),
    }
    blocks = {
        b: (_available_cols(d, nums), _available_cols(d, cats))
        for b, (nums, cats) in raw_blocks.items()
    }
    n_posts = len(d)
    n_authors = int(d["author_handle"].nunique()) if n_posts else 0
    n_papers = int(d["first_paper_id"].nunique()) if n_posts else 0
    if n_papers < 2 or n_posts < 5:
        return [dict(
            exp="E5", test="variance_shares", estimate=float("nan"),
            ci_low=float("nan"), ci_high=float("nan"),
            n_posts=n_posts, n_authors=n_authors, n_strata=n_papers,
            status=status or "insufficient",
            description="fewer than 2 papers with >=3 posters", _nc=None,
        )], _label_version(d)

    rows = []
    rng = np.random.default_rng(SEED)
    paper_groups = d["first_paper_id"].to_numpy()
    uniq_papers = np.unique(paper_groups)
    p_idx = {p: np.flatnonzero(paper_groups == p) for p in uniq_papers}

    for outcome in ("log_impressions", "log_cr_bmk_shrunk"):
        sub = d.dropna(subset=[outcome]).copy()
        y = sub[outcome].to_numpy(dtype="float64")
        g = sub["first_paper_id"].to_numpy()
        shares = _shapley_r2(sub, y, blocks, g)
        boot_shares: dict[str, list[float]] = {b: [] for b in blocks}
        for _ in range(n_boot):
            pick = rng.choice(uniq_papers, size=len(uniq_papers), replace=True)
            parts = [
                sub.iloc[p_idx[p]].assign(_bp=f"{p}_{i}")
                for i, p in enumerate(pick)
                if len(p_idx[p])
            ]
            if not parts:
                continue
            bdf = pd.concat(parts, ignore_index=True)
            if bdf["_bp"].nunique() < 2:
                continue
            bs = _shapley_r2(
                bdf,
                bdf[outcome].to_numpy(dtype="float64"),
                blocks,
                bdf["_bp"].to_numpy(),
            )
            for b, val in bs.items():
                boot_shares[b].append(val)

        for b, val in shares.items():
            arr = boot_shares[b]
            lo, hi = (
                tuple(float(v) for v in np.nanpercentile(arr, [2.5, 97.5]))
                if arr
                else (float("nan"), float("nan"))
            )
            rows.append(dict(
                exp="E5", test=f"{outcome}:{b}", estimate=val, ci_low=lo, ci_high=hi,
                n_posts=len(sub), n_authors=int(sub["author_handle"].nunique()),
                n_strata=int(sub["first_paper_id"].nunique()),
                status=status or "exploratory",
                description=f"Shapley OOF R2 share of {b} on {outcome} (95% paper CI)",
                _nc=None,
            ))
        total_r2 = sum(shares.values())
        rows.append(dict(
            exp="E5", test=f"{outcome}:unexplained", estimate=1.0 - total_r2,
            ci_low="", ci_high="", n_posts=len(sub),
            n_authors=int(sub["author_handle"].nunique()),
            n_strata=int(sub["first_paper_id"].nunique()),
            status=status or "exploratory",
            description=f"unexplained share (1 - R2_total) on {outcome}",
            _nc=None,
        ))
        rows.append(dict(
            exp="E5", test=f"{outcome}:paper_icc", estimate=_paper_icc(y, g),
            ci_low="", ci_high="", n_posts=len(sub),
            n_authors=int(sub["author_handle"].nunique()),
            n_strata=int(sub["first_paper_id"].nunique()),
            status=status or "exploratory",
            description=f"one-way ANOVA paper ICC upper bound on {outcome}",
            _nc=None,
        ))
    return rows, _label_version(d)


# ---------------------------------------------------------------- E6

E6_FEATURES = {
    "direct_question": r"\?",
    "do_you_know": r"\b(do|did) you know\b",
    "curiosity_gap": CURIOSITY_RE.pattern,
    "first_person_singular": r"\b(i|i'm|i've|my|me)\b",
    "first_person_plural": r"\b(we|we're|we've|our|us)\b",
    "second_person": r"\b(you|your|you're)\b",
    "paper_third_person": r"\b(the authors|this paper|the paper|they show|they find)\b",
    "imperative_opener": r"^(check|read|look|try|see|use|build|stop|ask)\b",
    "hedges": r"\b(maybe|perhaps|might|seems|i think|probably|likely)\b",
    "has_number": r"\d",
    "has_emoji": "[\U0001F300-\U0001FAFF☀-➿]",
    "has_link": r"https?://",
}


def run_e6(
    data: str | Path | pd.DataFrame, status: str | None, cohorts: set[str]
) -> tuple[list[dict], str]:
    d = load(data, cohorts)
    raw_text = d["text"].fillna("")
    t = raw_text.str.lower()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # patterns group on purpose
        for k, rx in E6_FEATURES.items():
            d[k] = t.str.contains(rx, regex=True)
    if "is_thread_opener" in d.columns:
        d["is_thread_opener"] = d["is_thread_opener"].fillna(False).astype(bool)
    else:
        d["is_thread_opener"] = raw_text.map(lambda s: thread_cues(s)[0]).astype(bool)
    if "mentions_venue" in d.columns:
        d["mentions_venue"] = d["mentions_venue"].fillna(False).astype(bool)
    else:
        d["mentions_venue"] = raw_text.str.contains(VENUE_RE).astype(bool)
    feat_cols = [*E6_FEATURES, "is_thread_opener", "mentions_venue"]

    imp = d["impressions"]
    for col, name in [("replies", "reply"), ("bookmarks", "bmk")]:
        r = d.groupby("follower_tier")[col].transform("sum") / d.groupby("follower_tier")[
            "impressions"
        ].transform("sum")
        d[f"{name}_s"] = (d[col] + r * 1000) / (imp + 1000) * 1000
    g = d.groupby("follower_tier")
    d["r_q"] = g["reply_s"].rank(pct=True)
    d["b_q"] = g["bmk_s"].rank(pct=True)
    d["lean"] = np.select(
        [(d.r_q > 0.75) & (d.b_q < 0.5), (d.b_q > 0.75) & (d.r_q < 0.5)],
        ["reply", "bookmark"], "other",
    )
    d = d[d["lean"] != "other"]
    rng = np.random.default_rng(SEED)
    authors = d["author_handle"].unique()
    disc = set(rng.permutation(authors)[: len(authors) // 2])
    d["half"] = np.where(d["author_handle"].isin(disc), "discovery", "confirm")

    def log_or(x: pd.DataFrame, f: str) -> float:
        a = x[(x.lean == "reply")][f]
        b = x[(x.lean == "bookmark")][f]
        return float(
            np.log((a.sum() + 0.5) / (len(a) - a.sum() + 0.5))
            - np.log((b.sum() + 0.5) / (len(b) - b.sum() + 0.5))
        )

    rows, lines = [], []
    disc_df = d[d.half == "discovery"]
    for f in feat_cols:
        if disc_df.empty:
            continue
        est, lo, hi = cluster_bootstrap(
            disc_df, lambda z, f=f: log_or(z, f), "author_handle", 300, percentiles=(2.5, 97.5)
        )
        lines.append((f, est, lo, hi, len(disc_df)))
    short = [(f, e, lo, hi) for f, e, lo, hi, _ in lines if lo > 0 or hi < 0]
    short = sorted(short, key=lambda r: -abs(r[1]))[:5]
    n_au = d["author_handle"].nunique()
    for f, e, lo, hi, n in lines:
        rows.append(dict(
            exp="E6", test=f"disc:{f}", estimate=e, ci_low=lo, ci_high=hi, n_posts=n,
            n_authors=int(disc_df["author_handle"].nunique()), n_strata="",
            status="dry_run" if status else "exploratory",
            description="log odds reply-leaning vs bookmark-leaning, 95% in script (99% col n/a)",
            _nc=None,
        ))
    rows.append(dict(
        exp="E6", test="shortlist", estimate=float(len(short)), ci_low="", ci_high="",
        n_posts=len(d), n_authors=n_au, n_strata="",
        status="dry_run" if status else "exploratory",
        description="shortlist: " + (", ".join(f for f, *_ in short) or "none"), _nc=None,
    ))
    conf_df = d[d.half == "confirm"]
    for f, disc_est, _, _ in short:
        if conf_df.empty:
            continue
        c_est, c_lo, c_hi = cluster_bootstrap(
            conf_df, lambda z, f=f: log_or(z, f), "author_handle", 500, percentiles=(0.5, 99.5)
        )
        confirmed = bool((c_est * disc_est > 0) and (c_lo > 0 or c_hi < 0))
        rows.append(dict(
            exp="E6", test=f"confirm:{f}", estimate=c_est, ci_low=c_lo, ci_high=c_hi,
            n_posts=len(conf_df), n_authors=int(conf_df["author_handle"].nunique()), n_strata="",
            status=status or ("confirmed" if confirmed else "unconfirmed"),
            description=(
                f"confirmation 99% log_or (disc={disc_est:.2f}); "
                f"{'confirmed' if confirmed else 'not confirmed'}"
            ),
            _nc=None,
        ))
    return rows, _label_version(d)


def summary_e6(rows: list[dict]) -> str:
    out = ["--- summary ---"]
    for r in rows:
        r.pop("_nc", None)
        if r["test"] == "shortlist":
            out.append(
                f"E6 {r['description']} (n_posts={r['n_posts']}, n_authors={r['n_authors']})"
            )
        else:
            out.append(
                f"E6 {r['test']}: log_or={r['estimate']:.2f} "
                f"ci=[{r['ci_low']:.2f}, {r['ci_high']:.2f}] n={r['n_posts']}"
            )
    return "\n".join(out)


# ---------------------------------------------------------------- E7


def run_e7(
    data: str | Path | pd.DataFrame,
    status: str | None,
    cohorts: set[str],
    *,
    widen_grounded: bool = False,
    require_breakout: bool = True,
    n_boot: int = N_BOOT,
) -> tuple[list[dict], str]:
    d = load(data, cohorts, apply_cap=False, apply_researcher_filter=True)
    is_roster = d["cohort"] == "ROSTER"
    cap = pd.Series(False, index=d.index)
    if is_roster.any():
        cap.loc[is_roster] = even_author_cap(d[is_roster], max_posts=40)
    if (~is_roster).any():
        cap.loc[~is_roster] = even_author_cap(d[~is_roster], max_posts=10)
    d = d[cap].copy()
    if "reach_vs_expected" not in d.columns or d["reach_vs_expected"].isna().all():
        m = fit_reach_model(d)
        exp_imp = (
            m.expected(d["followers_at_collection"]) if not d.empty else pd.Series(dtype=float)
        )
        d["reach_vs_expected"] = d["impressions"] / exp_imp

    base = d[(d["followers_at_collection"] < 2500) & (d["impressions"] >= 200)].copy()
    if base.empty:
        empty_rows = [
            dict(
                exp="E7", test=t, estimate=float("nan"), ci_low=float("nan"),
                ci_high=float("nan"), n_posts=0, n_authors=0, n_strata=0,
                status=status or "insufficient",
                description="no <2,500-follower posts with >=200 impressions", _nc=None,
            )
            for t in ("H5a", "H5b", "H5c")
        ]
        return empty_rows, _label_version(d)

    base["sub_tier"] = pd.cut(
        base["followers_at_collection"],
        [-1, 499, 999, 2499],
        labels=["<500", "500-999", "1000-2499"],
    ).astype(str)
    rigor = pd.to_numeric(base["technical_rigor_score"], errors="coerce")
    if widen_grounded:
        g_mask = (
            (base["visual_type"] == "PAPER_FIGURE")
            & base["hook_archetype"].isin(["CONTESTED_CLAIM", "TECHNICAL_BREAKDOWN"])
            & (rigor >= 3)
        )
    else:
        g_mask = (
            (base["visual_type"] == "PAPER_FIGURE")
            & (base["hook_archetype"] == "CONTESTED_CLAIM")
        )
    u_mask = (
        base["hook_archetype"].isin(["HOT_TAKE_CULTURE", "CONTESTED_CLAIM"])
        & base["visual_type"].isin(["NONE", "OTHER_IMAGE"])
        & (rigor <= 2)
    )
    base["e7_arm"] = np.select([g_mask, u_mask], ["G", "U"], default="")
    for col in ("quotes", "reposts", "bookmarks", "likes"):
        if col in base.columns:
            base[col] = base[col].fillna(0).clip(lower=0)

    primary_df = base[base["reach_vs_expected"] > 1.0].copy() if require_breakout else base.copy()
    u_sub = primary_df[primary_df["e7_arm"] == "U"]
    u_imp = float(u_sub["impressions"].sum()) if len(u_sub) else 0.0
    u_cr = float(u_sub["bookmarks"].sum() / u_imp * 1000.0) if u_imp > 0 else float("nan")
    u_zero = float((u_sub["bookmarks"] == 0).mean()) if len(u_sub) else float("nan")

    specs = [
        Spec("E7", "H5a", "e7_arm", {"U"}, {"G"}, "quotes", "reposts", "sub_tier", "up",
             cluster="author_handle", min_strata=2),
        Spec("E7", "H5b", "e7_arm", {"G"}, {"U"}, "bookmarks", "likes", "sub_tier", "up",
             cluster="author_handle", min_strata=2),
        Spec("E7", "H5c", "e7_arm", {"G"}, {"U"}, "bookmarks", "impressions", "sub_tier", "up",
             cluster="author_handle", min_strata=2),
    ]
    tag = "breakout" if require_breakout else "all<2500"
    if widen_grounded:
        tag += "+widened_G"
    rows = []
    for sp in specs:
        desc = f"<2.5k {tag} ({len(primary_df)} posts)"
        if sp.name == "H5c" and not np.isnan(u_cr):
            desc += f"; U cr_bmk={u_cr:.2f}, zero_bmk_share_U={u_zero:.2f}"
        rows.append(run_test(primary_df, sp, status, desc, n_boot=n_boot))

    sec_specs = [
        Spec("E7", f"{sp.name}-all", sp.arm_col, sp.a, sp.b, sp.count, sp.expo, sp.strata,
             sp.prediction, cluster=sp.cluster, min_strata=2)
        for sp in specs
    ]
    rows += [
        run_test(
            base, sp, status or "secondary",
            f"secondary all <2.5k >=200 imp ({len(base)} posts)",
            n_boot=min(500, n_boot), with_control=False,
        )
        for sp in sec_specs
    ]
    return rows, _label_version(d)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("exp", choices=["E1", "E2", "E3", "E4", "E5", "E6", "E7"])
    p.add_argument("--data", default="data/processed/posts_labelled.parquet")
    p.add_argument("--data-version", default="v1")
    p.add_argument("--status", default=None, help="override ledger status, e.g. dry_run")
    p.add_argument("--cohorts", default=None, help="comma list (defaults by experiment)")
    p.add_argument("--e7-widen", action="store_true")
    p.add_argument("--e7-no-breakout", action="store_true")
    p.add_argument("--no-ledger", action="store_true")
    a = p.parse_args()
    default_cohorts = {"ROSTER", "PANEL"} if a.exp in {"E1", "E2", "E3", "E5", "E7"} else {"ROSTER"}
    cohorts = set(a.cohorts.split(",")) if a.cohorts else default_cohorts
    runners = {
        "E1": (run_e1, summary),
        "E2": (run_e2, summary),
        "E3": (run_e3, summary),
        "E4": (run_e4, summary),
        "E5": (run_e5, summary),
        "E6": (run_e6, summary_e6),
        "E7": (
            lambda data, status, coh: run_e7(
                data,
                status,
                coh,
                widen_grounded=a.e7_widen,
                require_breakout=not a.e7_no_breakout,
            ),
            summary,
        ),
    }
    run_fn, summ = runners[a.exp]
    rows, lv = run_fn(a.data, a.status, cohorts)
    nc_rows = [dict(r) for r in rows]
    print(summ([dict(r) for r in rows]))
    if not a.no_ledger:
        for r in nc_rows:
            r.pop("_nc", None)
        ctrl = []
        for r in rows:
            nc = r.get("_nc")
            if nc:
                ctrl.append(dict(
                    exp=r["exp"], test=f"NC-{r['test']}", estimate=nc[0], ci_low=nc[1],
                    ci_high=nc[2], n_posts=r["n_posts"], n_authors=r["n_authors"],
                    n_strata=r["n_strata"], status="dry_run" if a.status else
                    ("control" if nc[3] else "error"),
                    description=f"negative control for {r['test']}: arms shuffled within strata",
                ))
        append_ledger(nc_rows + ctrl, a.data_version, lv)


if __name__ == "__main__":
    main()
