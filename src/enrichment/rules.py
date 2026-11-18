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
THREAD_START_RE = re.compile(r"^\s*(?:\(|\[)?1/([2-9]|\d{2})(?:\)|\])?(?:\s|:|$)")
THREAD_END_RE = re.compile(r"(?:\s|\(|\[)1/([2-9]|\d{2})(?:\)|\])?\s*$")
THREAD_CUE_RE = re.compile(r"🧵|^\s*1/\s+\S|\ba thread\b|\bthread\s*[:👇⬇️]", re.I)


def thread_cues(text: str) -> tuple[bool, int]:
    """Detect thread openers and length from text cues (decision 36)."""
    for rx in (THREAD_START_RE, THREAD_END_RE):
        m = rx.search(text)
        if m and int(m.group(1)) >= 2:
            return True, int(m.group(1))
    if THREAD_CUE_RE.search(text):
        return True, 2
    return False, 1


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
    cues = t.map(thread_cues)
    out["is_thread_opener"] = cues.map(lambda c: c[0]).astype(bool)
    out["thread_length"] = cues.map(lambda c: c[1]).astype(int)
    if "post_kind" in out.columns:
        mask = out["post_kind"].astype(str).eq("original") & out["is_thread_opener"]
        out.loc[mask, "post_kind"] = "thread_opener"
    return out
