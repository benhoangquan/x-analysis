"""Handles, cohorts, discovery queries and thresholds (report QUERY_VERSION in findings)."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from src.schema import Cohort

ACTOR_ID = "apidojo~tweet-scraper"
MIN_ITEMS_PER_QUERY = 50  # actor rule: every query must return at least 50 posts
MAX_QUERIES_PER_RUN = 5
APIFY_PRICE_PER_1K_USD = 0.40  # actor's listed price per 1,000 posts
APIFY_BUDGET_USD = 10.0  # hard cap on new Apify spend from 2026-11-14 (plan decision 33)
MIN_AUTHOR_FOLLOWERS = 200  # bot / empty-account floor for DISCOVERED
WINDOW_DAYS = 90  # plan decision 36
MATURITY_DAYS = 7  # the window ends this many days before collection

OWN_HANDLES = ["tiptreesystems", "martincsweiss1"]
BENCHMARK_HANDLES = ["elicitorg", "huggingface", "arxiv", "wandb"]  # decisions 14, 37
# Roster seeds: the five curators (decision 14) and Ben's item G accounts. The admitted
# roster from roster.py extends this list in milestone 1.
ROSTER_SEED_HANDLES = [
    "_akhaliq", "rasbt", "srush_nlp", "karpathy", "maximelabonne",
    "junli_r84995", "sippeyxp", "qiayuanliao",
]  # fmt: skip

ROSTER_FILE = Path("configs/roster_v1.csv")  # written by roster.py --finalise


@lru_cache(maxsize=1)
def roster_handles() -> frozenset[str]:
    """Hand-picked seeds plus the finalised roster, lower-cased."""
    out = {h.lower() for h in ROSTER_SEED_HANDLES}
    if ROSTER_FILE.exists():
        with ROSTER_FILE.open() as f:
            out |= {r["handle"].lower() for r in csv.DictReader(f)}
    return frozenset(out)


QUERY_VERSION = "v1"
LINK_DOMAINS = ["arxiv.org", "openreview.net", "github.com", "huggingface.co"]
VENUES = ["NeurIPS", "ICLR", "ICML", "ACL", "EMNLP", "CVPR", "SWE-bench"]
TOPIC_TERMS = ["ablation", "LoRA", "tokenizer", "fine-tuning", "benchmark", "reproducibility"]


def cohort_for(handle: str, default: Cohort = Cohort.DISCOVERED) -> Cohort:
    """OWN, BENCHMARK and ROSTER by handle; anyone else gets `default` (PANEL for panel files,
    DISCOVERED for v0)."""
    h = handle.lower()
    if h in {x.lower() for x in OWN_HANDLES}:
        return Cohort.OWN
    if h in {x.lower() for x in BENCHMARK_HANDLES}:
        return Cohort.BENCHMARK
    if h in roster_handles():
        return Cohort.ROSTER
    return default


EXCLUDE = "-filter:retweets -filter:replies"  # decision 36: no replies, no reposts


def timeline_query(handle: str, since: str, until: str) -> str:
    return f"from:{handle} since:{since} until:{until} {EXCLUDE}"


def authors_query(handles: list[str], since: str, until: str) -> str:
    """Several authors in one query (plan Collection design); `until` is exclusive."""
    who = " OR ".join(f"from:{h}" for h in handles)
    return f"({who}) since:{since} until:{until} {EXCLUDE}"


MAX_QUERY_CHARS = 512  # X advanced search truncates longer queries
OWN_PAPER_PHRASES = ["our paper", "our new paper", "we introduce"]  # decision 46


def own_paper_query(since: str, until: str) -> str:
    """Accounts posting their own arXiv papers: the main roster candidate source."""
    phrases = " OR ".join(f'"{p}"' for p in OWN_PAPER_PHRASES)
    return f"({phrases}) url:arxiv.org since:{since} until:{until} lang:en {EXCLUDE}"


def paper_query(
    arxiv_ids: list[str], since: str, until: str | None = None, bare: bool = False
) -> str:
    """Posts linking any of these arXiv papers (paper panel). `bare` matches the ID alone."""
    terms = [f"url:{i}" if bare else f'url:"arxiv.org/abs/{i}"' for i in arxiv_ids]
    window = f"since:{since}" + (f" until:{until}" if until else "")
    return f"({' OR '.join(terms)}) {window} {EXCLUDE}"


def discovery_queries(since: str, until: str) -> list[str]:
    """Wide-net candidate queries (stage 1). Sliced by date by the caller; sorted Latest."""
    base = f"since:{since} until:{until} lang:en -filter:retweets"
    terms = (
        [f"url:{d}" for d in LINK_DOMAINS]
        + [f'"{v}"' for v in VENUES]
        + [f'"{t}"' for t in TOPIC_TERMS]
    )
    return [f"({' OR '.join(terms)}) {base}"]
