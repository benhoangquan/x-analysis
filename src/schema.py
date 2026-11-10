"""Single data contract: enums and pydantic models for posts and accounts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Cohort(StrEnum):
    OWN = "OWN"
    BENCHMARK = "BENCHMARK"
    DISCOVERED = "DISCOVERED"


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


class PostKind(StrEnum):
    ORIGINAL = "original"
    QUOTE = "quote"
    THREAD_OPENER = "thread_opener"


class Post(BaseModel):
    """One X post. `followers_at_collection` is required: posts without it are rejected."""

    post_id: str
    author_handle: str
    author_id: str | None = None
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


class AccountSnapshot(BaseModel):
    author_handle: str
    followers: int = Field(ge=0)
    collected_at: datetime
