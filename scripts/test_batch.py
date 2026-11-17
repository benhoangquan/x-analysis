"""Plan decision 35: the test batch before any roster spend (cap $0.50).

Four one-query runs, at most 100 posts each (worst case 400 posts = $0.16):
  E      `OR` joins return posts from several authors, and only from them (item E);
         includes Ben's three item G seeds.
  F      an older fortnight for two prolific authors, compared with v0 (item F).
  PQ/PB  `url:` search for 13 arXiv IDs, quoted-path form vs bare-ID form (paper panel).

    uv run python scripts/test_batch.py --run     # spends money; refuses past the cap
    uv run python scripts/test_batch.py --check   # free; re-reads the stored files
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import authors_query, paper_query  # noqa: E402
from src.ingestion.apify import _load_dotenv, run, spent_usd  # noqa: E402
from src.ingestion.panel import arxiv_ids  # noqa: E402

OUT = Path("data/raw/_test_2026-11-14")
SEEDS = ["junli_r84995", "sippeyxp", "qiayuanliao"]
E_AUTHORS = [*SEEDS, "rasbt", "srush_nlp", "maximelabonne"]
F_AUTHORS = ["maximelabonne", "_akhaliq"]
F_V0_ORIGINALS = 3  # v0 had 3 original posts from F_AUTHORS on 2026-06-01..14
PAPER_IDS = [
    "2611.11440", "2606.18043", "2606.07352", "2606.07229", "2611.12289", "2610.20424",
    "2610.34662", "2607.20709", "2606.24597", "2611.12156", "2606.06624", "2609.36322",
    "2609.28473",
]  # fmt: skip  (seeded random draw from v0's 2606-2611 IDs; 13 keeps the query < 512 chars)
RUNS = {
    "E": authors_query(E_AUTHORS, "2026-10-01", "2026-11-07"),
    "F": authors_query(F_AUTHORS, "2026-06-01", "2026-06-15"),
    "PQ": paper_query(PAPER_IDS, "2026-06-01"),
    "PB": paper_query(PAPER_IDS, "2026-06-01", bare=True),
}
MAX_ITEMS = 100


def load(tag: str) -> list[dict]:
    files = sorted(OUT.glob(f"test_{tag}_*.jsonl"))
    if not files:
        return []
    items = [json.loads(x) for x in files[-1].read_text().splitlines() if x.strip()]
    return [i for i in items if isinstance(i, dict) and "id" in i]


def handle(item: dict) -> str:
    return str((item.get("author") or {}).get("userName") or "").lower()


def common(items: list[dict]) -> list[str]:
    n = len(items)
    replies = sum(bool(i.get("isReply")) for i in items)
    retweets = sum(bool(i.get("isRetweet") or i.get("retweet")) for i in items)
    views = sum(i.get("viewCount") is not None for i in items)
    bmk = sum(i.get("bookmarkCount") is not None for i in items)
    return [
        f"items={n} replies={replies} reposts={retweets} hit_cap={n == MAX_ITEMS}",
        f"viewCount present {views}/{n}, bookmarkCount present {bmk}/{n}",
    ]


def check() -> None:
    e = load("E")
    got = Counter(handle(i) for i in e)
    asked = {h.lower() for h in E_AUTHORS}
    print("== E: OR join ==", *common(e), sep="\n  ")
    print(f"  authors returned {dict(got)}")
    print(f"  outside the query: {sorted(set(got) - asked) or 'none'}")
    print(f"  E verdict: {'PASS' if len(got) >= 2 and set(got) <= asked else 'FAIL'}")
    for s in SEEDS:
        a = next((i.get("author") or {} for i in e if handle(i) == s.lower()), None)
        if a:
            desc = (a.get("description") or "").replace("\n", " ")[:100]
            print(f"  seed {s}: followers={a.get('followers')} posts={got[s.lower()]} bio={desc!r}")
        else:
            print(f"  seed {s}: no posts in 2026-10-01..11-06")

    f = load("F")
    print("== F: older weeks ==", *common(f), sep="\n  ")
    print(f"  by author {dict(Counter(handle(i) for i in f))}; v0 had {F_V0_ORIGINALS} originals")
    print(f"  F reading: {'v0 dropped older posts' if len(f) > F_V0_ORIGINALS else 'no loss seen'}")

    for tag in ["PQ", "PB"]:
        p = load(tag)
        asked_ids = set(PAPER_IDS)
        hits = [set(arxiv_ids(i)) & asked_ids for i in p]
        matched = sum(bool(h) for h in hits)
        posters: dict[str, set[str]] = {}
        for i, h in zip(p, hits, strict=True):
            for pid in h:
                posters.setdefault(pid, set()).add(handle(i))
        counts = sorted((len(v) for v in posters.values()), reverse=True)
        print(f"== {tag}: url: search ({'quoted' if tag == 'PQ' else 'bare'}) ==", *common(p),
              sep="\n  ")
        print(f"  posts linking a queried ID: {matched}/{len(p)}")
        print(f"  papers found {len(posters)}/{len(PAPER_IDS)}; posters per found paper {counts}")
    print(f"== spend: ${spent_usd():.4f} of $10 (test batch cap $0.50)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.run:
        _load_dotenv()
        for tag, q in RUNS.items():
            if spent_usd() + MAX_ITEMS * 0.40 / 1000 > 0.50:
                print(f"skip {tag}: would pass the $0.50 test-batch cap")
                continue
            print(tag, q)
            print("  ->", run([q], MAX_ITEMS, f"test_{tag}", out_dir=OUT))
    if a.check or a.run:
        check()


if __name__ == "__main__":
    main()
