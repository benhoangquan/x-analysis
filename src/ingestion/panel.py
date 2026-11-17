"""Paper panel (plan decisions 29, 36, 39, 42): seeds, collection and a feasibility summary.

    uv run python -m src.ingestion.panel --seeds     # free: Hugging Face lists -> 200 seeds
    uv run python -m src.ingestion.panel --collect   # spends, within the panel's $1.50
    uv run python -m src.ingestion.panel --summary   # free: posters per paper, candidates
    uv run python -m src.ingestion.panel --meta      # free: arXiv authors, v1 date, category
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import time
import urllib.request
from collections import deque
from collections.abc import Callable, Iterable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import APIFY_PRICE_PER_1K_USD, MAX_QUERY_CHARS, paper_query

# An ID counts only next to an arXiv-style host or an "arXiv:" prefix, so dates and
# version numbers such as "2025.1234" are not mistaken for papers.
ARXIV_ID_RE = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf|html)/|(?:huggingface\.co|modelscope\.ai)/papers/"
    r"|alphaxiv\.org/(?:abs|overview)/"
    r"|arxiv:\s?)(\d{4}\.\d{4,5})",
    re.I,
)

HF_API = "https://huggingface.co/api/daily_papers"
HF_DIR = Path("data/raw/hf_daily")
PANEL_DIR = Path("data/raw/panel")
SEEDS = Path("data/processed/panel_seeds.csv")
LIST_START, LIST_END = date(2026, 8, 9), date(2026, 10, 7)  # decision 42
COLLECT_END = date(2026, 11, 7)  # exclusive; 7 days before collection
POST_DAYS = 30
N_SEEDS = 200
SEED = 20261114
PANEL_BUDGET_USD = 1.50  # decision 36
MAX_ITEMS = 100  # observed per-query cap
TARGET_POSTS = 70  # between the actor's 50 minimum and the 100 cap
FIRST_GUESS_POSTS_PER_PAPER = 10.0
MAX_LIST_GAP_DAYS = 14  # trust Hugging Face's publishedAt only this close to the listing
TYPICAL_LIST_GAP_DAYS = 2  # median gap between arXiv date and listing

ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_DIR = Path("data/raw/arxiv_meta")
PAPERS = Path("data/processed/panel_papers.csv")
ATOM = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}

Runner = Callable[..., Path]


# ---------------------------------------------------------------- arXiv IDs in posts


def arxiv_ids(item: dict[str, Any]) -> list[str]:
    """Sorted arXiv IDs in a post's own text and link entities (not the quoted post)."""
    parts = [item.get("text") or "", item.get("fullText") or ""]
    entities = item.get("entities") or {}
    for url in entities.get("urls") or []:
        if isinstance(url, dict):
            parts += [str(url.get("expanded_url") or ""), str(url.get("url") or "")]
    return sorted(set(ARXIV_ID_RE.findall(" ".join(parts))))


def read_items(files: Iterable[Path]) -> list[dict[str, Any]]:
    out = []
    for f in files:
        for line in f.read_text().splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and "id" in item:
                out.append(item)
    return out


def arxiv_ids_by_post(files: Iterable[Path]) -> dict[str, list[str]]:
    """post_id -> arXiv IDs, read from raw JSONL files."""
    return {str(i["id"]): ids for i in read_items(files) if (ids := arxiv_ids(i))}


# ---------------------------------------------------------------- seeds


def _http_get(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "research-analytics/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        return json.loads(resp.read())


def fetch_daily(day: date, fetch: Callable[[str], Any] = _http_get, cache: Path = HF_DIR) -> list:
    """One Hugging Face daily list, cached verbatim under data/raw/hf_daily/."""
    path = cache / f"{day.isoformat()}.json"
    if path.exists():
        return json.loads(path.read_text())
    data = fetch(f"{HF_API}?date={day.isoformat()}")
    cache.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    time.sleep(0.5)
    return data


def seed_pool(lists: dict[date, list]) -> pd.DataFrame:
    """One row per paper: arXiv ID, arXiv date, first list date, upvotes, title."""
    rows = []
    for day, items in sorted(lists.items()):
        for x in items:
            p = x.get("paper") or {}
            pid = str(p.get("id") or "")
            if not re.fullmatch(r"\d{4}\.\d{4,5}", pid):
                continue
            pub = str(p.get("publishedAt") or x.get("publishedAt") or day.isoformat())[:10]
            rows.append(
                dict(paper_id=pid, published=pub, listed=day.isoformat(),
                     upvotes=p.get("upvotes"), title=x.get("title") or p.get("title") or "")
            )  # fmt: skip
    pool = pd.DataFrame(rows, columns=["paper_id", "published", "listed", "upvotes", "title"])
    pool = pool.sort_values("listed").drop_duplicates("paper_id").reset_index(drop=True)
    pairs = zip(pool["published"], pool["listed"], strict=True)
    return pool.assign(start=[window_start(pub, listed) for pub, listed in pairs])


def window_start(published: str, listed: str) -> str:
    """The paper's date for its 30-day post window.

    Hugging Face's publishedAt is used when it falls 0-14 days before the listing (194 of the
    200 seeds); otherwise it is implausible and the listing date minus 2 days is used.
    """
    gap = (date.fromisoformat(listed) - date.fromisoformat(published)).days
    if 0 <= gap <= MAX_LIST_GAP_DAYS:
        return published
    return (date.fromisoformat(listed) - timedelta(days=TYPICAL_LIST_GAP_DAYS)).isoformat()


def draw_seeds(pool: pd.DataFrame, n: int = N_SEEDS, seed: int = SEED) -> pd.DataFrame:
    """Uniform random draw, independent of upvotes and of the order the pool came in."""
    ids = sorted(pool["paper_id"])
    pick = set(random.Random(seed).sample(ids, min(n, len(ids))))
    out = pool[pool["paper_id"].isin(pick)]
    return out.sort_values(["start", "paper_id"]).reset_index(drop=True)


# ---------------------------------------------------------------- arXiv metadata


def parse_arxiv_atom(xml: str) -> list[dict[str, Any]]:
    """Paper rows from an arXiv API Atom feed: ID, v1 date, authors, category, code link."""
    import xml.etree.ElementTree as ET  # stdlib parser does not resolve external entities

    rows = []
    for e in ET.fromstring(xml).findall("a:entry", ATOM):
        m = re.search(r"abs/(\d{4}\.\d{4,5})", e.findtext("a:id", "", ATOM))
        if not m:
            continue
        comment = e.findtext("x:comment", "", ATOM) or ""
        cat = e.find("x:primary_category", ATOM)
        names = [a.findtext("a:name", "", ATOM) for a in e.findall("a:author", ATOM)]
        rows.append(
            dict(
                paper_id=m.group(1),
                arxiv_v1=e.findtext("a:published", "", ATOM)[:10],
                title=" ".join(e.findtext("a:title", "", ATOM).split()),
                authors="; ".join(names),
                n_authors=len(names),
                primary_category=cat.get("term") if cat is not None else "",
                has_code=bool(re.search(r"github\.com|huggingface\.co", comment, re.I)),
            )
        )
    return rows


def fetch_arxiv_meta(
    ids: list[str], fetch: Callable[[str], str] | None = None, batch: int = 50
) -> pd.DataFrame:
    """arXiv metadata for `ids`, raw Atom cached under data/raw/arxiv_meta/."""

    def _get(url: str) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": "research-analytics/0.1"})
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            return resp.read().decode()

    fetch = fetch or _get
    rows = []
    ARXIV_DIR.mkdir(parents=True, exist_ok=True)
    for n in range(0, len(ids), batch):
        part = ids[n : n + batch]
        path = ARXIV_DIR / f"batch_{n // batch:03d}_{part[0]}.xml"
        if not path.exists():
            path.write_text(fetch(f"{ARXIV_API}?id_list={','.join(part)}&max_results={batch}"))
            time.sleep(3)  # arXiv asks for one request every 3 seconds
        rows += parse_arxiv_atom(path.read_text())
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- collection


def window(group: pd.DataFrame) -> tuple[str, str]:
    since = min(group["start"])
    last = date.fromisoformat(max(group["start"])) + timedelta(days=POST_DAYS)
    return since, min(last, COLLECT_END).isoformat()


def query_for(group: pd.DataFrame) -> str:
    since, until = window(group)
    return paper_query(list(group["paper_id"]), since, until, bare=True)


def group_size(remaining: pd.DataFrame, posts_per_paper: float) -> int:
    k = max(1, min(len(remaining), round(TARGET_POSTS / max(posts_per_paper, 0.5))))
    while k > 1 and len(query_for(remaining.iloc[:k])) > MAX_QUERY_CHARS:
        k -= 1
    return k


def panel_spent(log: Path) -> float:
    if not log.exists():
        return 0.0
    with log.open() as f:
        rows = csv.DictReader(f)
        return sum(float(r["est_usd"]) for r in rows if r["label"].startswith("panel_"))


def collect(
    seeds: pd.DataFrame,
    runner: Runner,
    spend_log: Path,
    out_dir: Path = PANEL_DIR,
    budget: float = PANEL_BUDGET_USD,
) -> dict[str, Any]:
    """Adaptive groups; a run that hits the cap is split in two and rerun."""
    worst = MAX_ITEMS * APIFY_PRICE_PER_1K_USD / 1000
    todo: deque[pd.DataFrame] = deque()
    rest = seeds.copy()
    seen_posts, seen_papers, n_run, capped, stopped = 0, 0, 0, 0, False
    while len(rest) or todo:
        if panel_spent(spend_log) + worst > budget + 1e-9:
            stopped = True
            break
        if todo:
            group = todo.popleft()
        else:
            est = seen_posts / seen_papers if seen_papers else FIRST_GUESS_POSTS_PER_PAPER
            k = group_size(rest, est)
            group, rest = rest.iloc[:k], rest.iloc[k:]
        n_run += 1
        path = runner([query_for(group)], MAX_ITEMS, f"panel_{n_run:03d}",
                      out_dir=out_dir, spend_log=spend_log)  # fmt: skip
        n_items = len(read_items([path]))
        if n_items >= MAX_ITEMS and len(group) > 1:
            capped += 1
            half = len(group) // 2
            todo.appendleft(group.iloc[half:])
            todo.appendleft(group.iloc[:half])
            continue
        seen_posts += n_items
        seen_papers += len(group)
    left = len(rest) + sum(len(g) for g in todo)
    return dict(runs=n_run, capped=capped, papers_done=seen_papers, papers_left=left,
                stopped_by_budget=stopped, spent=panel_spent(spend_log))  # fmt: skip


# ---------------------------------------------------------------- summary


def _created(item: dict[str, Any]) -> date | None:
    try:
        return datetime.strptime(item["createdAt"], "%a %b %d %H:%M:%S %z %Y").date()
    except (KeyError, ValueError):
        return None


def panel_posts(seeds: pd.DataFrame, files: Iterable[Path]) -> pd.DataFrame:
    """One row per (post, seed paper) inside that paper's 30-day window, deduped by post."""
    pub = dict(zip(seeds["paper_id"], seeds["start"], strict=True))
    rows, seen = [], set()
    for i in read_items(files):
        if i["id"] in seen:
            continue
        seen.add(i["id"])
        made = _created(i)
        a = i.get("author") or {}
        for pid in set(arxiv_ids(i)) & set(pub):
            start = date.fromisoformat(pub[pid])
            if made and start <= made < start + timedelta(days=POST_DAYS):
                rows.append(
                    dict(
                        post_id=str(i["id"]),
                        paper_id=pid,
                        handle=str(a.get("userName") or "").lower(),
                        name=str(a.get("name") or ""),
                        followers=a.get("followers"),
                        bio=a.get("description") or "",
                        views=i.get("viewCount"),
                        bookmarks=i.get("bookmarkCount"),
                    )
                )
    return pd.DataFrame(rows)


def _tokens(name: str) -> list[str]:
    import unicodedata

    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z]+", plain)


def is_paper_author(display_name: str, authors: str) -> bool:
    """Rule half of ORIGINAL_RESEARCHER: an arXiv author's first and last name both appear."""
    shown = set(_tokens(display_name))
    for author in authors.split(";"):
        t = _tokens(author)
        if len(t) >= 2 and t[0] in shown and t[-1] in shown:
            return True
    return False


def summary(seeds: pd.DataFrame, posts: pd.DataFrame, papers: pd.DataFrame | None = None) -> str:
    per = posts.groupby("paper_id")["handle"].nunique().reindex(seeds["paper_id"], fill_value=0)
    acc = posts.drop_duplicates("handle")
    edges = [-1, 1999, 19999, 199999, float("inf")]
    labels = ["<2k", "2k-20k", "20k-200k", ">200k"]
    tiers = pd.cut(acc["followers"].fillna(0), edges, labels=labels).value_counts().sort_index()
    return "\n".join([
        f"seed papers: {len(seeds)}; papers with any post: {int((per > 0).sum())}",
        f"posts in window: {len(posts)} ({posts['post_id'].nunique()} unique)",
        f"posters per paper: median {per.median():.0f}, mean {per.mean():.1f}, max {per.max()}",
        f"papers with >= 3 posters (analysis set): {int((per >= 3).sum())}",
        f"papers with >= 5 posters: {int((per >= 5).sum())}",
        f"distinct accounts (candidate pool): {len(acc)}",
        "accounts by follower tier: " + ", ".join(f"{k} {v}" for k, v in tiers.items()),
        *_author_lines(posts, papers, per),
    ])  # fmt: skip


def _author_lines(posts: pd.DataFrame, papers: pd.DataFrame | None, per: pd.Series) -> list[str]:
    if papers is None or posts.empty:
        return []
    authors = dict(zip(papers["paper_id"], papers["authors"].fillna(""), strict=True))
    own = posts.apply(lambda r: is_paper_author(r["name"], authors.get(r["paper_id"], "")), axis=1)
    with_author = set(posts.loc[own, "paper_id"])
    mixed = {p for p in with_author if posts.loc[posts.paper_id == p, "handle"].nunique() >= 2}
    big = set(per[per >= 3].index)
    return [
        f"posts by a paper author (name match): {int(own.sum())} on {len(with_author)} papers",
        f"papers with an author post and another poster: {len(mixed)}"
        f" ({len(mixed & big)} in the >= 3-poster set)",
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", action="store_true")
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--meta", action="store_true", help="free: arXiv metadata for the seeds")
    a = ap.parse_args()
    if a.meta:
        seeds = pd.read_csv(SEEDS, dtype=str)
        meta = fetch_arxiv_meta(list(seeds["paper_id"]))
        meta.to_csv(PAPERS, index=False)
        print(f"arXiv metadata for {len(meta)} of {len(seeds)} seeds -> {PAPERS}")
    if a.seeds:
        days = [LIST_START + timedelta(d) for d in range((LIST_END - LIST_START).days + 1)]
        pool = seed_pool({d: fetch_daily(d) for d in days})
        seeds = draw_seeds(pool)
        SEEDS.parent.mkdir(parents=True, exist_ok=True)
        seeds.to_csv(SEEDS, index=False)
        print(f"pool {len(pool)} papers from {len(days)} lists; drew {len(seeds)} -> {SEEDS}")
    if a.collect:
        from src.ingestion.apify import SPEND_LOG, _load_dotenv, run

        _load_dotenv()
        print(collect(pd.read_csv(SEEDS, dtype=str), run, SPEND_LOG))
    if a.summary or a.collect:
        seeds = pd.read_csv(SEEDS, dtype=str)
        papers = pd.read_csv(PAPERS, dtype=str) if PAPERS.exists() else None
        print(summary(seeds, panel_posts(seeds, sorted(PANEL_DIR.glob("*.jsonl"))), papers))


if __name__ == "__main__":
    main()
