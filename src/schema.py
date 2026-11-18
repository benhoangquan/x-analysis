"""Single data contract: enums and pydantic models for posts and accounts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Cohort(StrEnum):
    OWN = "OWN"
    BENCHMARK = "BENCHMARK"
    ROSTER = "ROSTER"
    PANEL = "PANEL"
    DISCOVERED = "DISCOVERED"  # v0 keyword discovery only (superseded by ROSTER)


class HookArchetype(StrEnum):
    CONTESTED_CLAIM = "CONTESTED_CLAIM"
    LITERATURE_SYNTHESIS = "LITERATURE_SYNTHESIS"
    VISUAL_MAP = "VISUAL_MAP"
    PRODUCT_DEMO = "PRODUCT_DEMO"
    TECHNICAL_BREAKDOWN = "TECHNICAL_BREAKDOWN"
    HOT_TAKE_CULTURE = "HOT_TAKE_CULTURE"
    OTHER = "OTHER"


class VisualType(StrEnum):
    NONE = "NONE"
    LACUNA_MAP = "LACUNA_MAP"
    PAPER_FIGURE = "PAPER_FIGURE"
    CODE_TERMINAL = "CODE_TERMINAL"
    VIDEO_DEMO = "VIDEO_DEMO"
    OTHER_IMAGE = "OTHER_IMAGE"


class Framing(StrEnum):
    """notes/30_concepts/framing.md; precedence in this order."""

    CURIOSITY_GAP = "CURIOSITY_GAP"
    OPEN_QUESTION = "OPEN_QUESTION"
    DECLARATIVE_EMPIRICAL = "DECLARATIVE_EMPIRICAL"
    DECLARATIVE_OTHER = "DECLARATIVE_OTHER"


class PosterRole(StrEnum):
    """notes/30_concepts/poster_role.md; precedence in this order."""

    ORIGINAL_RESEARCHER = "ORIGINAL_RESEARCHER"
    CREDENTIALED_RESEARCHER = "CREDENTIALED_RESEARCHER"
    NON_RESEARCHER = "NON_RESEARCHER"


class PostKind(StrEnum):
    ORIGINAL = "original"
    QUOTE = "quote"
    THREAD_OPENER = "thread_opener"


class Post(BaseModel):
    """One X post. `followers_at_collection` is required: posts without it are rejected."""

    post_id: str
    author_handle: str
    author_id: str | None = None
    author_name: str | None = None
    author_bio: str | None = None
    cohort: Cohort
    url: str | None = None
    created_at: datetime
    collected_at: datetime
    source: str

    followers_at_collection: int = Field(ge=0)

    text: str
    post_kind: PostKind = PostKind.ORIGINAL

    impressions: int | None = Field(default=None, ge=0)
    likes: int = Field(ge=0)
    replies: int = Field(ge=0)
    reposts: int = Field(ge=0)
    quotes: int = Field(ge=0)
    bookmarks: int | None = Field(default=None, ge=0)

    is_reply: bool = False
    is_retweet: bool = False
    in_reply_to_username: str | None = None
    media_count: int = Field(default=0, ge=0)
    media_kind: str | None = None  # photo | video | animated_gif (first attachment)
    media_urls: list[str] = Field(default_factory=list)
    paper_id: str | None = None  # arXiv IDs the post links to, ";"-joined (decision 29)


class AccountSnapshot(BaseModel):
    author_handle: str
    followers: int = Field(ge=0)
    collected_at: datetime


class PostLabels(BaseModel):
    """Classifier output for one post, cached by (post_id, label_version)."""

    post_id: str
    label_version: str
    is_researcher_post: bool | None = None
    researcher_prob: float | None = None
    hook_archetype: HookArchetype | None = None
    archetype_probs: dict[str, float] = Field(default_factory=dict)
    visual_type: VisualType | None = None
    visual_source: str | None = None  # "jev" | "rule"
    technical_rigor_score: int | None = Field(default=None, ge=1, le=5)
    rigor_prob: float | None = None
    framing: Framing | None = None  # None on v1 labels, which did not ask
    framing_probs: dict[str, float] = Field(default_factory=dict)
    poster_role: PosterRole | None = None
    role_version: str | None = None
    p_own_work: float | None = None
    p_bio_research: float | None = None
    name_match: bool | None = None
    s2_papers: int | None = None
    label_confidence: float | None = None  # min over the label confidences
    label_rationale: str | None = None  # Jev returns probabilities, not rationales
    image_used: bool = False
    error: str | None = None
