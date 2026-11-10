"""Deterministic features and the hype lint. No model calls."""

from __future__ import annotations

import re

import pandas as pd

from src.config import LINK_DOMAINS, VENUES

URL_RE = re.compile(r"https?://\S+")
NUMBER_RE = re.compile(r"\d")
ARXIV_RE = re.compile(r"\b\d{4}\.\d{4,5}\b")
HYPE_PATTERNS = {
    "listicle": re.compile(r"\b(top\s*\d+|\d+\s+(ai\s+)?tools?\b|\d+\s+ways\b)", re.I),
    "clickbait": re.compile(
        r"(you won'?t believe|game[- ]?changer|changes everything|🧵\s*$)", re.I
    ),
    "replace_claim": re.compile(r"\breplace[sd]?\s+(researchers|scientists|phds?)\b", re.I),
}
VENUE_RE = re.compile(r"\b(?:" + "|".join(re.escape(v) for v in VENUES) + r")\b", re.I)


def hype_flags(text: str) -> list[str]:
    return [name for name, rx in HYPE_PATTERNS.items() if rx.search(text)]


def add_rule_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    t = out["text"].fillna("")
    out["has_media"] = out["media_count"] > 0
    out["has_link"] = t.str.contains(URL_RE)
    out["links_research_host"] = t.apply(lambda x: any(d in x for d in LINK_DOMAINS))
    out["char_len"] = t.str.len()
    out["has_number"] = t.str.contains(NUMBER_RE)
    out["mentions_venue"] = t.str.contains(VENUE_RE)
    out["has_arxiv_id"] = t.str.contains(ARXIV_RE)
    out["is_question"] = t.str.contains(r"\?")
    out["hype_flags"] = t.apply(lambda x: ",".join(hype_flags(x)))
    out["posted_hour_utc"] = pd.to_datetime(out["created_at"], utc=True).dt.hour
    return out
