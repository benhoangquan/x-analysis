"""`poster_role` for paper-linked posts (plan decision 30; notes/30_concepts/poster_role.md).

A separate Jev request from the post labels: it carries the poster's bio and the paper's author
list, which should not sway the other post questions. Not run until the pilot check
(decision 41). The Semantic Scholar paper count is not wired in yet; until it is, the
credential rule rests on the bio.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from src.ingestion.admission import BIO_Q
from src.ingestion.panel import is_paper_author

ORIGINAL, CREDENTIALED, NON = "ORIGINAL_RESEARCHER", "CREDENTIALED_RESEARCHER", "NON_RESEARCHER"
JEV_CUTOFF = 0.8  # concept note: Jev probability >= 0.8 for both Jev routes
MIN_PAPERS = 3  # credential rule (Ben, 2026-11-14)

OWN_WORK_Q = {
    "type": "noul",
    "instructions": "Does `post_text` present the paper `paper_title` as the poster's own work?",
    "criteria": {
        "true": "The poster writes as an author of the paper, as in \"our paper\", \"we show\", "
        "\"my new work\", or thanks co-authors.",
        "false": "The poster shares, summarises or comments on a paper written by other people.",
    },
}


def role_version(model: str) -> str:
    return hashlib.sha256(Path(__file__).read_bytes() + model.encode()).hexdigest()[:12]


def build_request(
    post_text: str, name: str, bio: str, paper_title: str, paper_authors: str, model: str
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "post_text": post_text,
        "poster_name": name,
        "paper_title": paper_title,
        "paper_authors": paper_authors,
    }
    questions: dict[str, Any] = {"own_work": OWN_WORK_Q}
    if bio.strip():
        state["bio"] = bio
        questions["bio"] = BIO_Q
    return {"model": model, "state": state, "questions": questions}


def decide(
    name_match: bool, p_own: float, p_bio: float | None, s2_papers: int | None = None
) -> str:
    """Truth table, in precedence order."""
    if name_match or p_own >= JEV_CUTOFF:
        return ORIGINAL
    if (s2_papers is not None and s2_papers >= MIN_PAPERS) or (p_bio or 0.0) >= JEV_CUTOFF:
        return CREDENTIALED
    return NON


def parse(
    answers: dict[str, Any],
    display_name: str,
    paper_authors: str,
    s2_papers: int | None = None,
) -> dict[str, Any]:
    p_own = float(answers["own_work"]["noul"])
    p_bio = float(answers["bio"]["noul"]) if "bio" in answers else None
    match = is_paper_author(display_name, paper_authors)
    return {
        "name_match": match,
        "p_own_work": p_own,
        "p_bio_research": p_bio,
        "s2_papers": s2_papers,
        "poster_role": decide(match, p_own, p_bio, s2_papers),
    }
