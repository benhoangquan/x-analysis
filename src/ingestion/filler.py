"""Filler guard (plan decision 49).

When a query matches few posts, the actor returns unrelated recent posts and charges for them.
Every run stores its queries next to its raw file (`<file>.query.json`); ingestion keeps an item
only if it matches at least one of them. Terms of one kind are OR'd (any author, any URL, any
phrase) and different kinds are AND'd, which is how this project writes its queries.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.ingestion.panel import arxiv_ids

DATE_FMT = "%a %b %d %H:%M:%S %z %Y"


@dataclass(frozen=True)
class QuerySpec:
    since: date | None
    until: date | None  # exclusive, as in X search
    authors: frozenset[str]
    urls: tuple[str, ...]
    phrases: tuple[str, ...]
    no_replies: bool
    no_reposts: bool


def parse_query(q: str) -> QuerySpec:
    def day(key: str) -> date | None:
        m = re.search(rf"\b{key}:(\d{{4}}-\d{{2}}-\d{{2}})", q)
        return date.fromisoformat(m.group(1)) if m else None

    urls = [a or b for a, b in re.findall(r'url:"([^"]+)"|url:(\S+?)(?=[\s)]|$)', q)]
    no_url = re.sub(r'url:"[^"]+"', " ", q)
    phrases = re.findall(r'"([^"]+)"', no_url)
    return QuerySpec(
        since=day("since"),
        until=day("until"),
        authors=frozenset(h.lower() for h in re.findall(r"from:(\w+)", q)),
        urls=tuple(u.lower() for u in urls),
        phrases=tuple(p.lower() for p in phrases),
        no_replies="-filter:replies" in q,
        no_reposts="-filter:retweets" in q,
    )


def _links(item: dict[str, Any]) -> str:
    urls = (item.get("entities") or {}).get("urls") or []
    parts = [str(u.get("expanded_url") or "") for u in urls if isinstance(u, dict)]
    return " ".join(parts + [item.get("text") or ""]).lower()


def matches(item: dict[str, Any], spec: QuerySpec) -> bool:
    if spec.no_replies and item.get("isReply"):
        return False
    if spec.no_reposts and (item.get("isRetweet") or item.get("retweet")):
        return False
    try:
        made = datetime.strptime(item["createdAt"], DATE_FMT).date()
    except (KeyError, ValueError):
        return False
    if (spec.since and made < spec.since) or (spec.until and made >= spec.until):
        return False
    handle = str((item.get("author") or {}).get("userName") or "").lower()
    if spec.authors and handle not in spec.authors:
        return False
    if spec.urls:
        links, ids = _links(item), set(arxiv_ids(item))
        if not any(u in links or u in ids for u in spec.urls):
            return False
    text = (item.get("text") or "").lower()
    return not spec.phrases or any(p in text for p in spec.phrases)


def sidecar(raw: Path) -> Path:
    return raw.with_name(raw.name + ".query.json")


def write_sidecar(raw: Path, queries: list[str], max_items: int, label: str) -> None:
    payload = {"queries": queries, "max_items": max_items, "label": label}
    sidecar(raw).write_text(json.dumps(payload, indent=1))


def queries_for(raw: Path) -> list[str] | None:
    s = sidecar(raw)
    return json.loads(s.read_text())["queries"] if s.exists() else None


def split_filler(
    items: list[dict[str, Any]], queries: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    specs = [parse_query(q) for q in queries]
    kept = [i for i in items if any(matches(i, s) for s in specs)]
    kept_ids = {id(i) for i in kept}
    return kept, [i for i in items if id(i) not in kept_ids]
