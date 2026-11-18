"""Map raw rows (export CSV or actor JSON) to validated Post objects, accepting field aliases."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from src.enrichment.rules import thread_cues
from src.ingestion.panel import arxiv_ids
from src.schema import Post

ALIASES: dict[str, tuple[str, ...]] = {
    "post_id": ("post_id", "id", "tweet_id"),
    "author_handle": ("author_handle", "userName", "username", "handle"),
    "author_id": ("author_id", "authorId"),
    "author_name": ("author_name", "name"),
    "author_bio": ("author_bio", "description"),
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
    "is_reply": ("is_reply", "isReply"),
    "is_retweet": ("is_retweet", "isRetweet"),
    "in_reply_to_username": ("in_reply_to_username", "inReplyToUsername"),
    "media_count": ("media_count",),
    "media_kind": ("media_kind",),
    "media_urls": ("media_urls",),
    "paper_id": ("paper_id",),
}


def _pick(row: Mapping[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        value = row.get(name)
        if value is not None and value != "":
            return value
    return None


def _flatten(row: Mapping[str, Any]) -> dict[str, Any]:
    """Lift nested actor `author` fields to the top level (without overwriting)."""
    flat = dict(row)
    author = row.get("author")
    if isinstance(author, Mapping):
        for k, v in author.items():
            flat.setdefault(k, v)
        flat.setdefault("author_id", author.get("id"))
    return flat


def _parse_dt(value: Any) -> Any:
    """Accept ISO strings or Twitter-style 'Tue Dec 10 07:00:30 +0000 2024'."""
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%a %b %d %H:%M:%S %z %Y")
        except ValueError:
            return value
    return value


def normalise_row(row: Mapping[str, Any]) -> dict[str, Any]:
    ids = arxiv_ids(dict(row))
    row = _flatten(row)
    if ids and "paper_id" not in row:
        row["paper_id"] = ";".join(ids)
    if "media_count" not in row and isinstance(row.get("media"), list):
        row["media_count"] = len(row["media"])
    ext = (row.get("extendedEntities") or {}).get("media")
    if "media_kind" not in row and isinstance(ext, list) and ext:
        row["media_kind"] = ext[0].get("type")
    if "media_urls" not in row and isinstance(row.get("media"), list):
        row["media_urls"] = [u for u in row["media"] if isinstance(u, str)]
    if not row.get("post_kind"):
        if row.get("isQuote") is True:
            row["post_kind"] = "quote"
        elif thread_cues(str(row.get("text") or row.get("fullText") or ""))[0]:
            row["post_kind"] = "thread_opener"
    out = {field: _pick(row, names) for field, names in ALIASES.items()}
    if "created_at" in out:
        out["created_at"] = _parse_dt(out["created_at"])
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
