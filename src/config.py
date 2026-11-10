"""Handles, cohorts, discovery queries and thresholds (report QUERY_VERSION in findings)."""

from __future__ import annotations

from src.schema import Cohort

ACTOR_ID = "apidojo~tweet-scraper"
MIN_ITEMS_PER_QUERY = 50  # actor rule: every query must return at least 50 posts
MAX_QUERIES_PER_RUN = 5
MIN_AUTHOR_FOLLOWERS = 200  # bot / empty-account floor for DISCOVERED
WINDOW_DAYS = 180

OWN_HANDLES = ["tiptreesystems", "martincsweiss1"]
BENCHMARK_HANDLES = [
    "elicitorg", "weights_biases", "huggingface", "arxiv", "PapersWithCode", "OpenReviewNET",
    "_akhaliq", "rasbt", "srush_nlp", "karpathy", "maximelabonne",
]  # fmt: skip

QUERY_VERSION = "v0"
LINK_DOMAINS = ["arxiv.org", "openreview.net", "github.com", "huggingface.co"]
VENUES = ["NeurIPS", "ICLR", "ICML", "ACL", "EMNLP", "CVPR", "SWE-bench"]
TOPIC_TERMS = ["ablation", "LoRA", "tokenizer", "fine-tuning", "benchmark", "reproducibility"]


def cohort_for(handle: str) -> Cohort:
    h = handle.lower()
    if h in {x.lower() for x in OWN_HANDLES}:
        return Cohort.OWN
    if h in {x.lower() for x in BENCHMARK_HANDLES}:
        return Cohort.BENCHMARK
    return Cohort.DISCOVERED


def timeline_query(handle: str, since: str, until: str) -> str:
    return f"from:{handle} since:{since} until:{until} -filter:retweets"


def discovery_queries(since: str, until: str) -> list[str]:
    """Wide-net candidate queries (stage 1). Sliced by date by the caller; sorted Latest."""
    base = f"since:{since} until:{until} lang:en -filter:retweets"
    terms = (
        [f"url:{d}" for d in LINK_DOMAINS]
        + [f'"{v}"' for v in VENUES]
        + [f'"{t}"' for t in TOPIC_TERMS]
    )
    return [f"({' OR '.join(terms)}) {base}"]
