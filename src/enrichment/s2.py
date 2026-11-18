"""Semantic Scholar lookup for poster_role credentials and paper metadata (E1, E3, E5)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.ingestion.panel import ARXIV_API, ARXIV_DIR, ATOM, _tokens, is_paper_author

S2_AUTHOR_URL = "https://api.semanticscholar.org/graph/v1/author/search"
S2_PAPER_BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
ML_CATEGORIES = frozenset({"cs.LG", "cs.CL", "cs.CV", "stat.ML"})  # decision 38
AUTHOR_CACHE_DIR = Path("data/raw/s2_authors")
PAPER_CACHE_DIR = Path("data/raw/s2_papers")
ARXIV_CAT_CACHE_DIR = Path("data/raw/s2_arxiv")
ARXIV_NUM_RE = re.compile(r"(\d{4}\.\d{4,5})")
VENUE_REJECT_RE = re.compile(r"\b(?:arxiv|corr|preprint)\b", re.I)

FetchJson = Callable[[str], dict[str, Any]]
PostJson = Callable[[str, dict[str, Any]], list[Any]]
FetchArxiv = Callable[[list[str]], dict[str, set[str]]]


def _s2_headers() -> dict[str, str]:
    headers = {"User-Agent": "research-analytics/0.1", "Accept": "application/json"}
    key = os.environ.get("S2_API_KEY")
    if key:
        headers["x-api-key"] = key
    return headers


def _request_json(url: str, payload: dict[str, Any] | None = None) -> Any:
    headers = _s2_headers()
    data = None
    method = "GET"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
        method = "POST"
    for attempt in range(4):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
                out = json.loads(resp.read())
            time.sleep(0.2 if "x-api-key" in headers else 1.0)
            return out
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(2**attempt)
                continue
            raise
    raise AssertionError("unreachable")


def _get_json(url: str) -> dict[str, Any]:
    out = _request_json(url)
    return out if isinstance(out, dict) else {}


def _post_json(url: str, payload: dict[str, Any]) -> list[Any]:
    out = _request_json(url, payload=payload)
    return out if isinstance(out, list) else []


def _parse_arxiv_categories(xml_text: str) -> dict[str, set[str]]:
    """Extract all primary and secondary category terms per paper ID from an arXiv Atom feed."""
    out: dict[str, set[str]] = {}
    for entry in ET.fromstring(xml_text).findall("a:entry", ATOM):
        m = re.search(r"abs/(\d{4}\.\d{4,5})", entry.findtext("a:id", "", ATOM))
        if not m:
            continue
        cats: set[str] = set()
        prim = entry.find("x:primary_category", ATOM)
        if prim is not None and prim.get("term"):
            cats.add(str(prim.get("term")))
        for cat in entry.findall("a:category", ATOM):
            if cat.get("term"):
                cats.add(str(cat.get("term")))
        out[m.group(1)] = cats
    return out


_ARXIV_CATS_MEM: dict[str, set[str]] | None = None
_ARXIV_CATS_DIRS: tuple[Path, Path] | None = None
_ARXIV_CATS_LOCK = threading.Lock()


def _default_fetch_arxiv(ids: list[str]) -> dict[str, set[str]]:
    """Resolve arXiv categories from local Atom caches first, then the arXiv API."""
    global _ARXIV_CATS_MEM, _ARXIV_CATS_DIRS
    dirs = (ARXIV_DIR, ARXIV_CAT_CACHE_DIR)
    with _ARXIV_CATS_LOCK:
        if _ARXIV_CATS_MEM is None or _ARXIV_CATS_DIRS != dirs:
            cats: dict[str, set[str]] = {}
            for folder in dirs:
                if folder.exists():
                    for xml_path in sorted(folder.glob("*.xml")):
                        cats.update(_parse_arxiv_categories(xml_path.read_text()))
            _ARXIV_CATS_MEM = cats
            _ARXIV_CATS_DIRS = dirs
        cats = _ARXIV_CATS_MEM
        missing = [i for i in ids if i not in cats]
        if not missing:
            return {i: cats[i] for i in ids if i in cats}
    ARXIV_CAT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fetched_cats: dict[str, set[str]] = {}
    for start in range(0, len(missing), 50):
        part = missing[start : start + 50]
        digest = hashlib.sha256(",".join(part).encode()).hexdigest()[:12]
        cache_path = ARXIV_CAT_CACHE_DIR / f"batch_{digest}.xml"
        if not cache_path.exists():
            url = f"{ARXIV_API}?id_list={','.join(part)}&max_results={len(part)}"
            req = urllib.request.Request(url, headers={"User-Agent": "research-analytics/0.1"})
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
                cache_path.write_text(resp.read().decode())
            time.sleep(3)
        fetched_cats.update(_parse_arxiv_categories(cache_path.read_text()))
    with _ARXIV_CATS_LOCK:
        if _ARXIV_CATS_MEM is not None and _ARXIV_CATS_DIRS == dirs:
            _ARXIV_CATS_MEM.update(fetched_cats)
            merged = _ARXIV_CATS_MEM
        else:
            merged = fetched_cats
        return {i: merged.get(i, set()) for i in ids}


def _author_slug(name: str) -> str:
    tokens = _tokens(name)
    stem = "_".join(tokens)[:40] or "author"
    digest = hashlib.sha256(name.strip().lower().encode()).hexdigest()[:8]
    return f"{stem}_{digest}"


def _clean_arxiv_id(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    m = ARXIV_NUM_RE.search(raw)
    return m.group(1) if m else None


def author_ml_paper_count(
    display_name: str,
    *,
    fetch_json: FetchJson = _get_json,
    fetch_arxiv: FetchArxiv = _default_fetch_arxiv,
    cache_dir: Path = AUTHOR_CACHE_DIR,
) -> int:
    """Count ML-category arXiv papers on matched Semantic Scholar author profiles."""
    if len(_tokens(display_name)) < 2:
        return 0
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{_author_slug(display_name)}.json"
    if cache_path.exists():
        data = json.loads(cache_path.read_text())
    else:
        q = urllib.parse.quote(display_name.strip())
        url = f"{S2_AUTHOR_URL}?query={q}&limit=5&fields=name,hIndex,paperCount,papers.externalIds"
        data = fetch_json(url)
        cache_path.write_text(json.dumps(data))

    matched = [
        c for c in (data.get("data") or [])
        if isinstance(c, dict) and is_paper_author(display_name, str(c.get("name") or ""))
    ]
    if not matched:
        return 0

    profile_ids: list[list[str]] = []
    all_ids: list[str] = []
    seen_all: set[str] = set()
    for cand in matched:
        ids: list[str] = []
        for p in cand.get("papers") or []:
            aid = _clean_arxiv_id(((p or {}).get("externalIds") or {}).get("ArXiv"))
            if aid and aid not in ids:
                ids.append(aid)
                if len(ids) >= 50:
                    break
        profile_ids.append(ids)
        for aid in ids:
            if aid not in seen_all:
                seen_all.add(aid)
                all_ids.append(aid)
    if not all_ids:
        return 0

    raw_cats = fetch_arxiv(all_ids)
    cats_by_id = {
        k: ({v} if isinstance(v, str) else set(v))
        for k, v in raw_cats.items()
    }
    return max(
        (
            sum(1 for aid in ids if cats_by_id.get(aid, set()) & ML_CATEGORIES)
            for ids in profile_ids
        ),
        default=0,
    )


def fetch_paper_s2_meta(
    arxiv_ids: list[str],
    *,
    post_json: PostJson = _post_json,
    cache_dir: Path = PAPER_CACHE_DIR,
) -> pd.DataFrame:
    """Batch-fetch venue and author h-index metadata for arXiv IDs from Semantic Scholar."""
    cols = ["paper_id", "s2_venue", "venue_accepted", "max_h_index", "median_h_index"]
    unique_ids = list(dict.fromkeys(pid.strip() for pid in arxiv_ids if pid and pid.strip()))
    if not unique_ids:
        return pd.DataFrame(columns=cols)

    cache_dir.mkdir(parents=True, exist_ok=True)
    records: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for pid in unique_ids:
        p = cache_dir / f"{pid}.json"
        if p.exists():
            records[pid] = json.loads(p.read_text())
        else:
            missing.append(pid)

    fields = "externalIds,venue,publicationVenue,year,authors.name,authors.hIndex"
    batch_url = f"{S2_PAPER_BATCH_URL}?fields={fields}"
    for start in range(0, len(missing), 200):
        chunk = missing[start : start + 200]
        resp = post_json(batch_url, {"ids": [f"ARXIV:{pid}" for pid in chunk]})
        for pid, rec in zip(chunk, resp, strict=False):
            clean = rec if isinstance(rec, dict) else {}
            records[pid] = clean
            (cache_dir / f"{pid}.json").write_text(json.dumps(clean))
        for pid in chunk[len(resp) :]:
            records[pid] = {}
            (cache_dir / f"{pid}.json").write_text("{}")

    rows = []
    for pid in unique_ids:
        rec = records.get(pid) or {}
        pub_venue = rec.get("publicationVenue") or {}
        venue = str(rec.get("venue") or pub_venue.get("name") or "").strip()
        pub_type = str(pub_venue.get("type") or "").strip().lower()
        accepted = bool(venue) and not VENUE_REJECT_RE.search(venue) and pub_type != "preprint"
        hs = [
            float(a["hIndex"])
            for a in (rec.get("authors") or [])
            if isinstance(a, dict) and a.get("hIndex") is not None
        ]
        rows.append(
            dict(
                paper_id=pid,
                s2_venue=venue,
                venue_accepted=accepted,
                max_h_index=float(max(hs)) if hs else float("nan"),
                median_h_index=float(np.median(hs)) if hs else float("nan"),
            )
        )
    return pd.DataFrame(rows, columns=cols)
