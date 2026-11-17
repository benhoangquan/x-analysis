"""Roster candidates and admission (plan decisions 10-13, 40, 46-48).

    uv run python -m src.ingestion.roster --search          # spends, within $1.00
    uv run python -m src.ingestion.roster --pool            # free: candidates from posts in hand
    uv run python -m src.ingestion.roster --admit [--limit N --show]   # Jev, resumable
    uv run python -m src.ingestion.roster --review-sheet    # blind sheet for Ben (50 + 25)
    uv run python -m src.ingestion.roster --recent          # spends, within $0.50: borderline
    uv run python -m src.ingestion.roster --pool --rejudge  # Jev re-judges borderline accounts
    uv run python -m src.ingestion.roster --week            # spends, within $0.30: borderline
    uv run python -m src.ingestion.roster --draw            # free: draft roster, caps of 150
    uv run python -m src.ingestion.roster --score-review    # free: Ben's review vs Jev's key
    uv run python -m src.ingestion.roster --score-review --finalise  # writes configs/roster_v1.csv
    uv run python -m src.ingestion.roster --collect-roster  # spends, within $5; needs the review
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.config import (
    APIFY_PRICE_PER_1K_USD,
    BENCHMARK_HANDLES,
    MAX_QUERY_CHARS,
    OWN_HANDLES,
    ROSTER_FILE,
    ROSTER_SEED_HANDLES,
    authors_query,
    own_paper_query,
)
from src.ingestion import admission
from src.ingestion.filler import parse_query, queries_for, split_filler
from src.ingestion.panel import PANEL_DIR, SEEDS, panel_posts, read_items

CANDIDATES = Path("data/processed/candidates.csv")
ADMISSIONS = Path("data/processed/admission.csv")
REVIEW = Path("data/gold/admission_review.csv")
REVIEW_KEY = Path("data/gold/admission_review_key.csv")
V0_LABELLED = Path("data/processed/posts_labelled.parquet")
TEST_DIR = Path("data/raw/_test_2026-11-14")
TIER_EDGES = [-1, 1999, 19999, 199999, float("inf")]
TIERS = ["<2k", "2k-20k", "20k-200k", ">200k"]
SOURCE_ORDER = ["ownpaper", "panel", "seed", "v0", "recent"]  # which posts to show Jev first
RECENT_DIR = Path("data/raw/borderline")
WEEK_DIR = Path("data/raw/borderline_week")
ROSTER_DIR = Path("data/raw/roster")
ROSTER_BUDGET_USD = 5.00  # decision 56
RECENT_MAX_ITEMS = 100
RECENT_TARGET = 70
FIRST_GUESS_POSTS_PER_ACCOUNT = 8.0
ROSTER_DRAFT = Path("data/processed/roster_draft.csv")
REVIEW_DONE = Path("data/gold/admission_review_done.csv")  # decision 12 gate
ADMIT_PRECISION_BAR = 0.85  # decision 58
TIER_CAP = 150  # decision 52
ORG_CUTOFF = 0.7  # decision 53

SEARCH_DIR = Path("data/raw/ownpaper")
SEARCH_BUDGET_USD = 1.00  # decision 46
SEARCH_START, SEARCH_END = date(2026, 8, 11), date(2026, 11, 7)  # until is exclusive
SLICE_DAYS = 4
SLICE_ITEMS = 110


def slices(start: date = SEARCH_START, end: date = SEARCH_END, days: int = SLICE_DAYS):
    d = start
    while d < end:
        e = min(d + timedelta(days=days), end)
        yield d.isoformat(), e.isoformat()
        d = e


def search_spent(log: Path) -> float:
    if not log.exists():
        return 0.0
    with log.open() as f:
        rows = csv.DictReader(f)
        return sum(float(r["est_usd"]) for r in rows if r["label"].startswith("ownpaper_"))


def search(runner, spend_log: Path, out_dir: Path = SEARCH_DIR) -> list[Path]:
    worst = SLICE_ITEMS * APIFY_PRICE_PER_1K_USD / 1000
    paths = []
    for n, (since, until) in enumerate(slices(), start=1):
        if search_spent(spend_log) + worst > SEARCH_BUDGET_USD + 1e-9:
            print(f"stop before slice {n}: own-paper search cap ${SEARCH_BUDGET_USD:.2f}")
            break
        p = runner([own_paper_query(since, until)], SLICE_ITEMS, f"ownpaper_{n:03d}",
                   out_dir=out_dir, spend_log=spend_log)  # fmt: skip
        paths.append(p)
        print(n, since, until, p)
    return paths


def label_spent(log: Path, prefix: str) -> float:
    if not log.exists():
        return 0.0
    with log.open() as f:
        return sum(float(r["est_usd"]) for r in csv.DictReader(f) if r["label"].startswith(prefix))


@dataclass(frozen=True)
class Window:
    """One author-collection job: date range, spend cap, label prefix, folder."""

    since: str
    until: str  # exclusive
    budget: float
    prefix: str
    out_dir: Path
    first_guess: float  # posts per account in the range, before any are observed


MONTH_TOPUP = Window("2026-10-07", "2026-11-07", 0.50, "recent_", RECENT_DIR, 8.0)  # dec. 51
WEEK_TOPUP = Window("2026-10-31", "2026-11-07", 0.30, "week_", WEEK_DIR, 4.4)  # dec. 54
ROSTER_MONTHS = [  # decision 56: newest first, one shared $5 cap
    Window("2026-10-08", "2026-11-07", ROSTER_BUDGET_USD, "roster_", ROSTER_DIR, 12.0),
    Window("2026-09-08", "2026-10-08", ROSTER_BUDGET_USD, "roster_", ROSTER_DIR, 12.0),
    Window("2026-08-09", "2026-09-08", ROSTER_BUDGET_USD, "roster_", ROSTER_DIR, 12.0),
]


def author_groups(handles: list[str], per_account: float, w: Window) -> int:
    k = max(1, min(len(handles), round(RECENT_TARGET / max(per_account, 0.5))))
    while k > 1 and len(authors_query(handles[:k], w.since, w.until)) > MAX_QUERY_CHARS:
        k -= 1
    return k


def collect_authors(handles: list[str], runner, spend_log: Path, w: Window) -> dict:
    """Grouped `from:` queries over one window, sized from observed posts per account to aim
    at RECENT_TARGET real posts; a run that hits the cap is split in two and rerun."""
    worst = RECENT_MAX_ITEMS * APIFY_PRICE_PER_1K_USD / 1000
    rest, todo = list(handles), []
    seen_posts = seen_accounts = runs = capped = 0
    tag = w.since.replace("-", "")
    while rest or todo:
        if label_spent(spend_log, w.prefix) + worst > w.budget + 1e-9:
            break
        if todo:
            group = todo.pop(0)
        else:
            est = seen_posts / seen_accounts if seen_accounts else w.first_guess
            k = author_groups(rest, est, w)
            group, rest = rest[:k], rest[k:]
        runs += 1
        q = authors_query(group, w.since, w.until)
        path = runner([q], RECENT_MAX_ITEMS, f"{w.prefix}{tag}_{runs:03d}", out_dir=w.out_dir,
                      spend_log=spend_log)  # fmt: skip
        n = len(read_items([path]))
        if n >= RECENT_MAX_ITEMS and len(group) > 1:
            capped += 1
            half = len(group) // 2
            todo[:0] = [group[:half], group[half:]]
            continue
        seen_posts += len(guarded([path]))
        seen_accounts += len(group)
    left = len(rest) + sum(len(g) for g in todo)
    return dict(window=f"{w.since}..{w.until}", runs=runs, capped=capped,
                accounts_done=seen_accounts, accounts_left=left, posts_kept=seen_posts,
                spent=round(label_spent(spend_log, w.prefix), 4))  # fmt: skip


def collect_recent(handles: list[str], runner, spend_log: Path, out_dir: Path = RECENT_DIR) -> dict:
    """Decision 51's month top-up (kept for its tests and log)."""
    return collect_authors(handles, runner, spend_log, replace(MONTH_TOPUP, out_dir=out_dir))


def collect_roster(handles: list[str], runner, spend_log: Path, out_dir: Path = ROSTER_DIR) -> list:
    """Decision 56: months newest first until the shared roster cap stops the runs."""
    out = []
    for w in ROSTER_MONTHS:
        res = collect_authors(handles, runner, spend_log, replace(w, out_dir=out_dir))
        out.append(res)
        if res["accounts_left"]:
            break
    return out


def queried_handles(folder: Path) -> set[str]:
    """Every account named in the stored queries of a folder's runs."""
    out: set[str] = set()
    for f in folder.glob("*.jsonl"):
        for q in queries_for(f) or []:
            out |= set(parse_query(q).authors)
    return out


def guarded(files: list[Path]) -> list[dict]:
    """Items from raw files, with filler dropped wherever the run stored its query."""
    out = []
    for f in files:
        items = read_items([f])
        q = queries_for(f)
        out += split_filler(items, q)[0] if q else items
    return out


def build_pool() -> pd.DataFrame:
    """One row per candidate: profile fields from the newest item, up to 3 posts in hand."""
    v0 = pd.read_parquet(V0_LABELLED)
    v0_ok = set(v0.loc[v0["is_researcher_post"] == True, "author_handle"].str.lower())  # noqa: E712
    seeds = pd.read_csv(SEEDS, dtype=str)
    panel_ids = set(panel_posts(seeds, sorted(PANEL_DIR.glob("*.jsonl")))["post_id"])
    tagged: list[tuple[str, dict]] = []
    tagged += [("ownpaper", i) for i in guarded(sorted(SEARCH_DIR.glob("*.jsonl")))]
    tagged += [("panel", i) for i in read_items(sorted(PANEL_DIR.glob("*.jsonl")))
               if str(i["id"]) in panel_ids]  # fmt: skip
    seed_set = {h.lower() for h in ROSTER_SEED_HANDLES}
    tagged += [("seed", i) for i in guarded(sorted(TEST_DIR.glob("*.jsonl")))]
    v0_items = read_items(sorted(Path("data/raw").glob("*.jsonl")))
    tagged += [("v0", i) for i in v0_items]
    recent_files = sorted(RECENT_DIR.glob("*.jsonl")) + sorted(WEEK_DIR.glob("*.jsonl"))
    tagged += [("recent", i) for i in guarded(recent_files)]
    skip = {h.lower() for h in OWN_HANDLES + BENCHMARK_HANDLES} | {"weights_biases"}
    rows: dict[str, dict] = {}
    for src, i in tagged:
        a = i.get("author") or {}
        h = str(a.get("userName") or "").lower()
        if not h or h in skip or i.get("isReply") or i.get("isRetweet"):
            continue
        if src == "v0" and h not in v0_ok | seed_set:
            continue
        if src == "seed" and h not in seed_set:
            src = "testbatch"  # authors found by the test batch's paper queries
        r = rows.setdefault(h, {"handle": h, "sources": set(), "posts": [], "_rank": 9})
        r["sources"].add(src)
        rank = SOURCE_ORDER.index(src) if src in SOURCE_ORDER else 2
        if rank < r["_rank"]:  # profile from the most recent collection
            r.update(name=a.get("name") or "", bio=a.get("description") or "",
                     followers=a.get("followers"), _rank=rank)  # fmt: skip
        text = (i.get("text") or "").strip()
        if text and text not in [t for _, t in r["posts"]]:
            r["posts"].append((rank, text))
    for h in seed_set:  # seeds stay candidates even if their posts were all replies
        rows.setdefault(h, {"handle": h, "sources": {"seed"}, "posts": [], "_rank": 9})
    out = []
    for r in rows.values():
        posts = [t for _, t in sorted(r["posts"], key=lambda x: x[0])][: admission.MAX_POSTS]
        slots = {f"post_{k + 1}": (posts[k] if k < len(posts) else "") for k in range(3)}
        out.append(
            dict(
                handle=r["handle"],
                name=r.get("name", ""),
                bio=r.get("bio", ""),
                followers=r.get("followers"),
                sources=",".join(sorted(r["sources"])),
                n_posts=len(posts),
                **slots,
            )
        )
    df = pd.DataFrame(out)
    df["tier"] = pd.cut(df["followers"].fillna(0), TIER_EDGES, labels=TIERS).astype(str)
    return df.sort_values("handle").reset_index(drop=True)


def run_admission(
    cands: pd.DataFrame, judge, limit: int | None, show: bool, rejudge: set[str] | None = None
) -> pd.DataFrame:
    """Resumable: rows already judged under this admission version are skipped, except the
    handles in `rejudge`, which are judged again on their current posts (decision 51)."""
    version = admission.admission_version(judge.model)
    done = pd.read_csv(ADMISSIONS, dtype={"handle": str}) if ADMISSIONS.exists() else None
    seen = set(done.loc[done["version"] == version, "handle"]) if done is not None else set()
    if rejudge is not None:
        todo = cands[cands["handle"].isin(rejudge)]
    else:
        todo = cands[~cands["handle"].isin(seen)]
    if limit:
        todo = todo.head(limit)
    for _, c in todo.iterrows():
        posts = [c[f"post_{k}"] for k in (1, 2, 3)]
        posts = [t for t in posts if isinstance(t, str) and t]
        name = c["name"] if isinstance(c["name"], str) and c["name"] else c["handle"]
        bio = c["bio"] if isinstance(c["bio"], str) else ""
        body = admission.build_request(name, bio, posts, judge.model)
        try:
            row = admission.parse(judge.ask(body)["answers"])
        except Exception as e:  # a failed call is an error, never a rejection
            row = {"decision": "error", "error": str(e)[:200]}
        row |= {"handle": c["handle"], "version": version}
        new = not ADMISSIONS.exists()
        pd.DataFrame([row]).to_csv(ADMISSIONS, mode="a", header=new, index=False)
        if show:
            print(c["handle"], c["tier"], "|", bio[:70].replace("\n", " "), "|", row)
    print(f"Jev input tokens this run: {judge.input_tokens}")
    return pd.read_csv(ADMISSIONS, dtype={"handle": str})


def latest_decisions(adm: pd.DataFrame) -> pd.DataFrame:
    return adm.drop_duplicates("handle", keep="last").reset_index(drop=True)


def draw_roster(
    cands: pd.DataFrame,
    adm: pd.DataFrame,
    seed: int = 20261114,
    hand_picked: list[str] = ROSTER_SEED_HANDLES,
) -> pd.DataFrame:
    """Decisions 52, 53, 55: admitted people, at most TIER_CAP per tier (random above the cap),
    plus the hand-picked accounts outside the cap."""
    a = latest_decisions(adm)
    a = a[(a["decision"] == admission.ADMIT) & (pd.to_numeric(a["p_org"]) < ORG_CUTOFF)]
    pool = cands.merge(a[["handle", "p_bio_research", "p_posts", "p_org"]], on="handle")
    hand = {h.lower() for h in hand_picked}
    pool = pool[~pool["handle"].isin(hand)]
    parts = []
    for _, g in pool.groupby("tier"):
        parts.append(g.sample(min(len(g), TIER_CAP), random_state=seed))
    picked = cands[cands["handle"].isin(hand)]  # decision 55: in whatever Jev decided
    latest = latest_decisions(adm).set_index("handle")
    picked = picked.assign(**{c: picked["handle"].map(latest[c]) for c in
                              ["p_bio_research", "p_posts", "p_org"]})  # fmt: skip
    out = pd.concat(parts + [picked.assign(hand_picked=True)])
    out["hand_picked"] = out["hand_picked"].fillna(False).astype(bool)
    cols = ["handle", "tier", "followers", "sources", "p_bio_research", "p_posts", "p_org",
            "hand_picked"]  # fmt: skip
    return out[cols].sort_values(["tier", "handle"]).reset_index(drop=True)


def score_review(done: pd.DataFrame, key: pd.DataFrame) -> dict:
    """Decision 58: how many of Jev's admits and rejects Ben confirms."""
    m = key.merge(done[["handle", "ben_admit"]], on="handle", how="left")
    said = m["ben_admit"].fillna("").astype(str).str.strip().str.lower()
    m = m.assign(ben_yes=said.isin(["yes", "y", "true", "1"]), filled=said.isin(
        ["yes", "y", "true", "1", "no", "n", "false", "0"]))  # fmt: skip
    adm, rej = m[m["decision"] == admission.ADMIT], m[m["decision"] == admission.REJECT]
    precision = float(adm["ben_yes"].mean()) if len(adm) else float("nan")
    return {
        "filled": int(m["filled"].sum()),
        "rows": len(m),
        "admits_confirmed": int(adm["ben_yes"].sum()),
        "admits": len(adm),
        "admit_precision": round(precision, 3),
        "rejects_confirmed": int((~rej["ben_yes"] & rej["filled"]).sum()),
        "rejects": len(rej),
        "passes": bool(m["filled"].all() and precision >= ADMIT_PRECISION_BAR),
    }


def _yes(v: object) -> bool | None:
    s = str(v).strip().lower() if isinstance(v, str) else ""
    if s in {"yes", "y", "true", "1"}:
        return True
    return False if s in {"no", "n", "false", "0"} else None


def finalise(draft: pd.DataFrame, done: pd.DataFrame, cands: pd.DataFrame) -> pd.DataFrame:
    """Ben's verdict overrides Jev for the reviewed accounts; hand-picked accounts stay."""
    verdict = {h: _yes(v) for h, v in zip(done["handle"], done["ben_admit"], strict=True)}
    hand = draft["hand_picked"].astype(str).str.lower().eq("true")
    keep = draft[hand | draft["handle"].map(lambda h: verdict.get(h) is not False)]
    added = [h for h, v in verdict.items() if v and h not in set(keep["handle"])]
    extra = cands[cands["handle"].isin(added)][["handle", "tier", "followers", "sources"]]
    out = pd.concat([keep, extra.assign(hand_picked=False)], ignore_index=True)
    out["review"] = out["handle"].map(
        lambda h: {True: "ben_yes", False: "ben_no"}.get(verdict.get(h), "not_reviewed")
    )
    cols = ["handle", "tier", "followers", "hand_picked", "review"]
    return out[cols].sort_values(["tier", "handle"]).reset_index(drop=True)


def review_sheet(
    cands: pd.DataFrame, adm: pd.DataFrame, seed: int = 20261114, key_path: Path = REVIEW_KEY
) -> pd.DataFrame:
    """50 admitted and 25 rejected, shuffled together, Jev's decision hidden from Ben."""
    adm = adm.drop_duplicates("handle", keep="last")
    admitted = adm[adm["decision"] == admission.ADMIT].sample(50, random_state=seed)
    rejected = adm[adm["decision"] == admission.REJECT].sample(25, random_state=seed)
    pick = pd.concat([admitted, rejected])
    pick = pick.sample(frac=1, random_state=seed)
    key = ["handle", "decision", "p_bio_research", "p_posts", "p_org"]
    pick[key].to_csv(key_path, index=False)
    sheet = cands.set_index("handle").loc[pick["handle"]].reset_index()
    sheet.insert(1, "profile", "https://x.com/" + sheet["handle"])
    sheet = sheet[["handle", "profile", "name", "tier", "followers", "bio",
                   "post_1", "post_2", "post_3"]]  # fmt: skip
    sheet["ben_admit"] = ""
    sheet["ben_note"] = ""
    return sheet


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", action="store_true")
    ap.add_argument("--pool", action="store_true")
    ap.add_argument("--admit", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--review-sheet", action="store_true")
    ap.add_argument("--recent", action="store_true")
    ap.add_argument("--rejudge", action="store_true")
    ap.add_argument("--draw", action="store_true")
    ap.add_argument("--week", action="store_true")
    ap.add_argument("--collect-roster", action="store_true")
    ap.add_argument("--score-review", action="store_true")
    ap.add_argument("--finalise", action="store_true")
    a = ap.parse_args()
    from src.ingestion.apify import SPEND_LOG, _load_dotenv, run

    _load_dotenv()
    if a.search:
        search(run, SPEND_LOG)
    if a.pool:
        pool = build_pool()
        CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
        pool.to_csv(CANDIDATES, index=False)
        print(f"{len(pool)} candidates -> {CANDIDATES}")
        print(pool.groupby("tier").size().to_string())
        print(pool["sources"].value_counts().head(8).to_string())
    if a.recent:
        adm = latest_decisions(pd.read_csv(ADMISSIONS, dtype=str))
        border = sorted(adm.loc[adm["decision"] == admission.BORDERLINE, "handle"])
        print(f"{len(border)} borderline accounts")
        print(collect_recent(border, run, SPEND_LOG))
    if a.rejudge:
        from src.enrichment.judge import JevJudge

        adm = latest_decisions(pd.read_csv(ADMISSIONS, dtype=str))
        border = set(adm.loc[adm["decision"] == admission.BORDERLINE, "handle"])
        cands = pd.read_csv(CANDIDATES, dtype=str)
        fresh = set(cands.loc[cands["sources"].str.contains("recent", na=False), "handle"])
        counts = pd.read_csv(ADMISSIONS, dtype=str)["handle"].value_counts()
        once = set(counts[counts == 1].index)
        border &= fresh & once  # evidence changed since the only judgment
        print(f"re-judging {len(border)} borderline accounts with recent posts")
        adm = run_admission(cands, JevJudge(), None, False, rejudge=border)
        new = latest_decisions(adm)
        print(new[new["handle"].isin(border)]["decision"].value_counts().to_string())
    if a.week:
        adm = latest_decisions(pd.read_csv(ADMISSIONS, dtype=str))
        border = set(adm.loc[adm["decision"] == admission.BORDERLINE, "handle"])
        targets = sorted(border - queried_handles(RECENT_DIR))
        print(f"{len(targets)} borderline accounts without a month of posts")
        print(collect_authors(targets, run, SPEND_LOG, WEEK_TOPUP))
    score: dict = {}
    if a.score_review or a.collect_roster or a.finalise:
        if not REVIEW_DONE.exists():
            raise SystemExit(f"decision 12: roster collection waits for {REVIEW_DONE}")
        done, key = pd.read_csv(REVIEW_DONE, dtype=str), pd.read_csv(REVIEW_KEY, dtype=str)
        score = score_review(done, key)
        print(score)
        if a.collect_roster and not score["passes"]:
            raise SystemExit("decision 58: review not complete or admits below 85%; revise first")
    if a.finalise:
        if not (a.score_review or a.collect_roster) or not score["passes"]:
            raise SystemExit("run --finalise together with --score-review once the review passes")
        draft, cands = pd.read_csv(ROSTER_DRAFT, dtype=str), pd.read_csv(CANDIDATES, dtype=str)
        final = finalise(draft, done, cands)
        ROSTER_FILE.parent.mkdir(parents=True, exist_ok=True)
        final.to_csv(ROSTER_FILE, index=False)
        print(f"{len(final)} accounts -> {ROSTER_FILE}")
        print(final.groupby("tier").size().to_string())
    if a.collect_roster:
        if not ROSTER_FILE.exists():
            raise SystemExit(f"finalise the roster first: {ROSTER_FILE}")
        roster = pd.read_csv(ROSTER_FILE, dtype=str)
        handles = list(roster["handle"]) + OWN_HANDLES + BENCHMARK_HANDLES  # decision 57
        for res in collect_roster(handles, run, SPEND_LOG):
            print(res)
    if a.draw:
        roster = draw_roster(pd.read_csv(CANDIDATES, dtype=str), pd.read_csv(ADMISSIONS, dtype=str))
        roster.to_csv(ROSTER_DRAFT, index=False)
        print(f"{len(roster)} accounts -> {ROSTER_DRAFT}")
        print(roster.groupby("tier").size().to_string())
    if a.admit:
        from src.enrichment.judge import JevJudge

        adm = run_admission(pd.read_csv(CANDIDATES, dtype=str), JevJudge(), a.limit, a.show)
        print(adm.drop_duplicates("handle", keep="last")["decision"].value_counts().to_string())
    if a.review_sheet:
        cands = pd.read_csv(CANDIDATES, dtype=str)
        sheet = review_sheet(cands, pd.read_csv(ADMISSIONS, dtype=str))
        REVIEW.parent.mkdir(parents=True, exist_ok=True)
        sheet.to_csv(REVIEW, index=False)
        print(f"{len(sheet)} candidates -> {REVIEW} (key: {REVIEW_KEY})")


if __name__ == "__main__":
    main()
