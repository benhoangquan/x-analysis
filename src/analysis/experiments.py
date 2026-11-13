"""Hypothesis-test harness for notes/40_experiments: stratified rate ratio, negative control,
verdict rule, ledger rows, and the E4 and E6 entry points.

Run: uv run python -m src.analysis.experiments E4 [--data PATH] [--status dry_run]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import warnings
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

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
    den = (cB * eA / (eA + eB))[ok].sum()
    return float((cA * eB / (eA + eB))[ok].sum() / den) if den > 0 else float("nan")


def cluster_bootstrap(
    df: pd.DataFrame, fn, cluster: str, n_boot: int = N_BOOT, seed: int = SEED
) -> tuple[float, float, float]:
    """Point estimate and 99% percentile interval, resampling whole clusters."""
    rng = np.random.default_rng(seed)
    groups = {k: v for k, v in df.groupby(cluster)}
    keys = np.array(list(groups))
    est = fn(df)
    draws = []
    for _ in range(n_boot):
        pick = rng.choice(keys, size=len(keys), replace=True)
        # relabel each draw so repeated clusters stay distinct strata
        parts = [groups[k].assign(_boot=i) for i, k in enumerate(pick)]
        draws.append(fn(pd.concat(parts)))
    lo, hi = np.nanpercentile(draws, [0.5, 99.5])
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


def run_test(df: pd.DataFrame, t: Spec, status_override: str | None, desc: str) -> dict:
    d = df[df[t.arm_col].isin(t.a | t.b)].copy()
    d["_arm"] = d[t.arm_col].isin(t.a)
    # evidence gate: posts and authors per arm, strata holding both arms
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
        and n_strata >= MIN_STRATA
    )

    def fn(x: pd.DataFrame) -> float:
        s = "_boot_stratum" if "_boot" in x else t.strata
        if "_boot" in x:
            x = x.assign(_boot_stratum=x[t.strata].astype(str) + "|" + x["_boot"].astype(str))
        return mh_rate_ratio(x, t.arm_col, t.a, t.b, t.count, t.expo, s)

    est, lo, hi = cluster_bootstrap(d, fn, t.cluster) if len(d) else (np.nan,) * 3
    row.update(estimate=est, ci_low=lo, ci_high=hi)
    row["status"] = status_override or (
        verdict(lo, hi, t.prediction) if gate else "insufficient"
    )
    if status_override and not gate:
        desc += " [gate failed]"
    row["description"] = desc
    # negative control: arms shuffled within strata
    nc = shuffle_within(d, t.arm_col, t.strata)
    nest, nlo, nhi = cluster_bootstrap(nc, fn, t.cluster, n_boot=500) if len(nc) else (np.nan,) * 3
    row["_nc"] = (nest, nlo, nhi, bool(nlo <= 1 <= nhi) if not np.isnan(nlo) else False)
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


def load(path: str, cohorts: set[str]) -> pd.DataFrame:
    d = pd.read_parquet(path)
    d = d[d["eligible"] & d["mature"] & (d["is_researcher_post"] == True)]  # noqa: E712
    d = d[d["cohort"].isin(cohorts)].dropna(subset=["impressions", "bookmarks"]).copy()
    d["impressions"] = d["impressions"].clip(lower=1)
    return d


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


def summary(rows: list[dict]) -> str:
    out = ["--- summary ---"]
    for r in rows:
        nc = r.pop("_nc", None)
        out.append(
            f"{r['exp']} {r['test']}: est={r['estimate']:.3f} "
            f"ci=[{r['ci_low']:.3f}, {r['ci_high']:.3f}] n_posts={r['n_posts']} "
            f"n_authors={r['n_authors']} n_strata={r['n_strata']} status={r['status']}"
        )
        if nc:
            out.append(
                f"  control: est={nc[0]:.3f} ci=[{nc[1]:.3f}, {nc[2]:.3f}] "
                f"{'pass' if nc[3] else 'FAIL'}"
            )
    return "\n".join(out)


# ---------------------------------------------------------------- E4


def run_e4(data: str, status: str | None, cohorts: set[str]) -> tuple[list[dict], str]:
    d = load(data, cohorts)
    d["framing"] = framing_proxy(d["text"].fillna(""), d["has_number"])
    decl = {"DECLARATIVE_EMPIRICAL", "DECLARATIVE_OTHER"}
    tests = [
        Spec("E4", "H4a", "framing", {"OPEN_QUESTION"}, decl, "replies", "impressions",
                 "author_handle", "up"),
        Spec("E4", "H4b", "framing", {"DECLARATIVE_EMPIRICAL"}, {"OPEN_QUESTION"},
                 "bookmarks", "likes", "author_handle", "up"),
        Spec("E4", "H4c", "framing", {"CURIOSITY_GAP"}, {"DECLARATIVE_EMPIRICAL"},
                 "bookmarks", "impressions", "author_handle", "null"),
    ]
    if "likes" in d:
        d["likes"] = d["likes"].clip(lower=0)
    note = "rule-proxy framing; replies include own thread replies; " if status else ""
    rows = [
        run_test(d, t, status, f"{note}{t.name} on {len(d)} filter-passing posts")
        for t in tests
    ]
    return rows, str(d["label_version"].iloc[0]) if len(d) else "-"


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


def run_e6(data: str, status: str | None, cohorts: set[str]) -> tuple[list[dict], str]:
    d = load(data, cohorts)
    t = d["text"].fillna("").str.lower()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # patterns group on purpose
        for k, rx in E6_FEATURES.items():
            d[k] = t.str.contains(rx, regex=True)
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
    for f in E6_FEATURES:
        x = d[d.half == "discovery"]
        if x.empty:
            continue
        est, lo, hi = cluster_bootstrap(x, lambda z, f=f: log_or(z, f), "author_handle", 300)
        lines.append((f, est, lo, hi, len(x)))
    short = [(f, e, lo, hi) for f, e, lo, hi, _ in lines if lo > 0 or hi < 0]
    short = sorted(short, key=lambda r: -abs(r[1]))[:5]
    n_au = d["author_handle"].nunique()
    for f, e, lo, hi, n in lines:
        rows.append(dict(
            exp="E6", test=f"disc:{f}", estimate=e, ci_low=lo, ci_high=hi, n_posts=n,
            n_authors=int(d[d.half == "discovery"]["author_handle"].nunique()), n_strata="",
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
    return rows, str(d["label_version"].iloc[0]) if len(d) else "-"


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


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("exp", choices=["E4", "E6"])
    p.add_argument("--data", default="data/processed/posts_labelled.parquet")
    p.add_argument("--data-version", default="v0-2026-11-11")
    p.add_argument("--status", default=None, help="override ledger status, e.g. dry_run")
    p.add_argument("--cohorts", default="DISCOVERED", help="comma list; v0 has DISCOVERED only")
    p.add_argument("--no-ledger", action="store_true")
    a = p.parse_args()
    cohorts = set(a.cohorts.split(","))
    run, summ = (run_e4, summary) if a.exp == "E4" else (run_e6, summary_e6)
    rows, lv = run(a.data, a.status, cohorts)
    nc_rows = [dict(r) for r in rows]
    print(summ([dict(r) for r in rows]))
    if not a.no_ledger:
        for r in nc_rows:
            r.pop("_nc", None)
        # one control row per E4 test
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
