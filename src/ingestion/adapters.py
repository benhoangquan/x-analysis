"""Map raw rows (export CSV or actor JSON) to validated Post objects, accepting field aliases."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import ValidationError

from src.schema import Post

ALIASES: dict[str, tuple[str, ...]] = {
    "post_id": ("post_id", "id", "tweet_id"),
    "author_handle": ("author_handle", "userName", "username", "handle"),
    "author_id": ("author_id", "authorId"),
    "url": ("url", "twitterUrl"),
    "created_at": ("created_at", "createdAt"),
    "followers_at_collection": ("followers_at_collection", "followers", "followersCount"),
    "text": ("text", "fullText"),
    "impressions": ("impressions", "viewCount", "views"),
    "likes": ("likes", "likeCount"),
    "replies": ("replies", "replyCount"),
    "reposts": ("reposts", "retweetCount", "repostCount"),
    "quotes": ("quotes", "quoteCount"),
    "bookmarks": ("bookmarks", "bookmarkCount"),
    "cohort": ("cohort",),
    "collected_at": ("collected_at",),
    "source": ("source",),
    "post_kind": ("post_kind",),
}


def _pick(row: Mapping[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        value = row.get(name)
        if value is not None and value != "":
            return value
    return None


def normalise_row(row: Mapping[str, Any]) -> dict[str, Any]:
    out = {field: _pick(row, names) for field, names in ALIASES.items()}
    return {k: v for k, v in out.items() if v is not None}


def rows_to_posts(rows: Iterable[Mapping[str, Any]]) -> tuple[list[Post], list[tuple[int, str]]]:
    """Return (valid posts, [(row index, reason)] for rejected rows)."""
    posts: list[Post] = []
    rejected: list[tuple[int, str]] = []
    for i, row in enumerate(rows):
        try:
            posts.append(Post(**normalise_row(row)))
        except ValidationError as exc:
            fields = ",".join(str(e["loc"][0]) for e in exc.errors())
            rejected.append((i, f"invalid: {fields}"))
    return posts, rejected
