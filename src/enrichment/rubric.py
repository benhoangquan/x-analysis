"""Labelling rubric: the questions asked of Jev and the code that turns answers into labels.

All question wording lives here (and only here). Jev answers atomic judgments; the decisions
(archetype precedence, rigor level, researcher filter) are made in code below.
Editing this file changes LABEL_VERSION, so cached labels are recomputed.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from src.schema import HookArchetype, PostLabels, VisualType

IMAGE_KEY = "attached_image"
RESEARCHER_THRESHOLD = 0.5
ARCHETYPE_MIN_PROB = 0.5  # below this on every archetype question -> OTHER
TIE_BAND = 0.10  # archetypes within this of the top are resolved by PRECEDENCE
# Overlap rule: a visual map is the most specific claim, a culture take the most generic.
PRECEDENCE = [
    HookArchetype.VISUAL_MAP,
    HookArchetype.PRODUCT_DEMO,
    HookArchetype.TECHNICAL_BREAKDOWN,
    HookArchetype.LITERATURE_SYNTHESIS,
    HookArchetype.CONTESTED_CLAIM,
    HookArchetype.HOT_TAKE_CULTURE,
]

RESEARCHER_Q = {
    "type": "noul",
    "instructions": (
        "Is `post_text` written for people who publish, read, replicate or stress-test "
        "peer-reviewed research or empirical machine learning research, as informed peers?"
    ),
    "criteria": {
        "true": (
            "The post engages with methodological detail, empirical verification, a contested "
            "claim, or a synthesis of the literature."
        ),
        "false": (
            "The post is high-level commentary, a broad tutorial, a company or product "
            "announcement, a joke, or aimed at general enthusiasts or consumers."
        ),
    },
}

ARCHETYPE_QS: dict[HookArchetype, dict[str, Any]] = {
    HookArchetype.CONTESTED_CLAIM: {
        "type": "noul",
        "instructions": (
            "Does `post_text` challenge a prevailing view or point to an empirical contradiction?"
        ),
    },
    HookArchetype.LITERATURE_SYNTHESIS: {
        "type": "noul",
        "instructions": (
            "Does `post_text` connect three or more different papers to show a gap in the "
            "literature?"
        ),
    },
    HookArchetype.VISUAL_MAP: {
        "type": "noul",
        "instructions": (
            "Is `attached_image` a map, graph or visualization of a research area or a cluster "
            "of papers?"
        ),
    },
    HookArchetype.PRODUCT_DEMO: {
        "type": "noul",
        "instructions": (
            "Does `post_text` show a tool solving a tedious task that researchers have?"
        ),
    },
    HookArchetype.TECHNICAL_BREAKDOWN: {
        "type": "noul",
        "instructions": (
            "Does `post_text` examine a paper's figure, an ablation, or a model architecture "
            "in detail?"
        ),
    },
    HookArchetype.HOT_TAKE_CULTURE: {
        "type": "noul",
        "instructions": (
            "Does `post_text` give an opinion on peer review, access to GPUs, or how research "
            "labs work?"
        ),
    },
}

RIGOR_Q = {
    "type": "score",
    "instructions": "How technically rigorous is `post_text`?",
    "criteria": [
        "Introductory or promotional: general claims with no technical specifics.",
        "Informal technical remark: names a method or model but gives no numbers or evidence.",
        "Specific claim: cites a paper, a result or a concrete number without saying how it "
        "was measured.",
        "Detailed empirical discussion: compares methods or settings with measurements, "
        "baselines or ablations.",
        "Formal or benchmark-level: formal mathematics, results on a named benchmark or "
        "venue such as NeurIPS, ICLR or SWE-bench, or concrete hyperparameters.",
    ],
}

VISUAL_Q = {
    "type": "choice",
    "instructions": "What kind of image is `attached_image`?",
    "criteria": {
        "lacuna_map": "A map or network graph of a cluster of research papers or topics.",
        "paper_figure": "A figure or table from a paper, such as an ablation table, a loss "
        "curve or an architecture diagram.",
        "code_terminal": "A screenshot of a terminal, a command line or a code snippet.",
        "other_image": "Any other image, such as a photo, a meme, a product screenshot or a logo.",
    },
}
VISUAL_MAP = {
    "lacuna_map": VisualType.LACUNA_MAP,
    "paper_figure": VisualType.PAPER_FIGURE,
    "code_terminal": VisualType.CODE_TERMINAL,
    "other_image": VisualType.OTHER_IMAGE,
}


def label_version(model: str) -> str:
    h = hashlib.sha256(Path(__file__).read_bytes() + model.encode()).hexdigest()
    return h[:12]


def build_request(
    text: str,
    model: str,
    image_ref: str | None = None,
    image_b64: str | None = None,
    image_format: str = "jpg",
) -> dict[str, Any]:
    state: dict[str, Any] = {"post_text": text}
    questions: dict[str, Any] = {"researcher": RESEARCHER_Q, "rigor": RIGOR_Q}
    for arch, q in ARCHETYPE_QS.items():
        if arch is HookArchetype.VISUAL_MAP and image_ref is None:
            continue  # the question is about the image; code sets its probability to 0
        questions[f"arch_{arch.value}"] = q
    body: dict[str, Any] = {"model": model, "state": state, "questions": questions}
    if image_ref is not None and image_b64 is not None:
        state[IMAGE_KEY] = image_ref
        body["assets"] = {
            image_ref: {"type": "image", "format": image_format, "data_base64": image_b64}
        }
        questions["visual"] = VISUAL_Q
    return body


def _rigor(answer: Mapping[str, Any]) -> tuple[int, float]:
    probs = {int(k): float(v) for k, v in answer["probabilities"].items()}
    base = min(probs)  # the API may number levels from 0 or 1
    top = max(probs, key=lambda k: probs[k])
    return top - base + 1, probs[top]


def pick_archetype(probs: Mapping[str, float]) -> tuple[HookArchetype, float]:
    """Truth table: highest-probability archetype; near-ties resolved by PRECEDENCE."""
    best = max(probs.values(), default=0.0)
    if best < ARCHETYPE_MIN_PROB:
        return HookArchetype.OTHER, 1 - best
    for arch in PRECEDENCE:
        if probs.get(arch.value, 0.0) >= best - TIE_BAND and probs.get(arch.value, 0) >= 0.5:
            return arch, probs[arch.value]
    return HookArchetype.OTHER, 1 - best  # unreachable; keeps the function total


def parse_answers(
    post_id: str,
    version: str,
    answers: Mapping[str, Any],
    media_kind: str | None,
    image_used: bool,
) -> PostLabels:
    r = float(answers["researcher"]["noul"])
    probs = {
        a.value: float(answers[f"arch_{a.value}"]["noul"])
        for a in ARCHETYPE_QS
        if f"arch_{a.value}" in answers
    }
    probs.setdefault(HookArchetype.VISUAL_MAP.value, 0.0)
    archetype, arch_conf = pick_archetype(probs)
    rigor, rigor_p = _rigor(answers["rigor"])

    if media_kind is None:
        vis, src, vis_conf = VisualType.NONE, "rule", 1.0
    elif media_kind in ("video", "animated_gif"):
        vis, src, vis_conf = VisualType.VIDEO_DEMO, "rule", 0.5  # Jev does not read video
    elif "visual" in answers:
        v = answers["visual"]
        vis, src, vis_conf = VISUAL_MAP[v["choice"]], "jev", float(v["probabilities"][v["choice"]])
    else:
        vis, src, vis_conf = VisualType.OTHER_IMAGE, "rule", 0.0  # image could not be read

    return PostLabels(
        post_id=post_id,
        label_version=version,
        is_researcher_post=r >= RESEARCHER_THRESHOLD,
        researcher_prob=r,
        hook_archetype=archetype,
        archetype_probs=probs,
        visual_type=vis,
        visual_source=src,
        technical_rigor_score=rigor,
        rigor_prob=rigor_p,
        label_confidence=min(max(r, 1 - r), arch_conf, rigor_p, vis_conf),
        image_used=image_used,
    )
