"""Roster admission (plan decisions 12, 47, 48): Jev judgments, decision in code.

All admission question wording lives here. Editing it changes ADMISSION_VERSION.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from statistics import mean
from typing import Any

ADMIT, REJECT, BORDERLINE = "admit", "reject", "borderline"
YES, NO = 0.7, 0.3  # Noul thresholds; between them the judgment is unsettled
MAX_POSTS = 3

BIO_Q = {
    "type": "noul",
    "instructions": "Does `bio` say that this account's holder works in machine learning or AI "
    "research?",
    "criteria": {
        "true": "The bio names a research role in ML or AI, such as professor, PhD student, "
        "postdoc, research scientist or research engineer, or names an ML research lab.",
        "false": "The bio describes a non-research job, a product or company, an investor, a "
        "news or meme account, or says nothing about the holder's work.",
    },
}


def post_q(key: str) -> dict[str, Any]:
    return {
        "type": "noul",
        "instructions": f"Is `posts.{key}` written for people who read or write ML research "
        "papers?",
        "criteria": {
            "true": "It is written for ML researchers or practitioners who follow papers: "
            "faculty, PhD students, research scientists and engineers, or people sharing "
            "training or fine-tuning detail. Product posts aimed at these readers count.",
            "false": "It is written for app developers, people shopping for AI tools, investors "
            "or the general public, or it is not about machine learning.",
        },
    }


ORG_Q = {
    "type": "noul",
    "instructions": "Is this account run by an organisation rather than by one person?",
    "criteria": {
        "true": "`display_name` or `bio` presents a company, lab, journal, newsletter, "
        "conference or community.",
        "false": "`display_name` and `bio` present one person.",
    },
}


def admission_version(model: str) -> str:
    return hashlib.sha256(Path(__file__).read_bytes() + model.encode()).hexdigest()[:12]


def build_request(name: str, bio: str, posts: list[str], model: str) -> dict[str, Any]:
    keys = [f"post_{i + 1}" for i in range(min(len(posts), MAX_POSTS))]
    state: dict[str, Any] = {"display_name": name, "posts": dict(zip(keys, posts, strict=False))}
    questions: dict[str, Any] = {"org": ORG_Q} | {f"aud_{k}": post_q(k) for k in keys}
    if bio.strip():  # an empty bio is left out, not judged
        state["bio"] = bio
        questions["bio"] = BIO_Q
    return {"model": model, "state": state, "questions": questions}


def decide(bio: float | None, posts: list[float]) -> str:
    """Truth table. `bio` is None when the account has no bio (treated as unsettled)."""
    if not posts:
        return BORDERLINE
    top = max(posts)
    b = 0.5 if bio is None else bio
    if (b >= YES and top >= YES) or (len(posts) >= 2 and mean(posts) >= YES):
        return ADMIT
    if top < NO or (b < NO and top < YES):
        return REJECT
    return BORDERLINE


def parse(answers: dict[str, Any]) -> dict[str, Any]:
    bio = float(answers["bio"]["noul"]) if "bio" in answers else None
    posts = [float(v["noul"]) for k, v in sorted(answers.items()) if k.startswith("aud_")]
    return {
        "p_bio_research": bio,
        "p_posts": ";".join(f"{p:.2f}" for p in posts),
        "p_org": float(answers["org"]["noul"]),
        "decision": decide(bio, posts),
    }
