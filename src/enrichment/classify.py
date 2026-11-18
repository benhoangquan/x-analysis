"""CLI: label eligible posts with the judge. Resumable; cached by (post_id, label_version).

python -m src.enrichment.classify --model jev-latest [--limit N] [--force]
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from src.enrichment import poster_role, s2
from src.enrichment.judge import DEFAULT_MODEL, JevError, JevJudge, Judge
from src.enrichment.media import fetch_image
from src.ingestion.apify import _load_dotenv
from src.ingestion.panel import PAPERS, arxiv_ids, fetch_arxiv_meta
from src.schema import PosterRole, PostLabels

POSTS = Path("data/processed/posts_enriched.parquet")
LABELS = Path("data/processed/labels.parquet")
LABELLED = Path("data/processed/posts_labelled.parquet")
CANDIDATES = Path("data/processed/candidates.csv")


def load_cache(path: Path = LABELS) -> pd.DataFrame:
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


def _clean_str(val: object) -> str:
    return val.strip() if isinstance(val, str) else ""


def _first_paper_id(row: object) -> str | None:
    pid = _clean_str(getattr(row, "paper_id", None))
    if pid:
        return pid.split(";")[0].strip() or None
    ids = arxiv_ids({"text": _clean_str(getattr(row, "text", ""))})
    return ids[0] if ids else None


def load_author_profiles(path: Path = CANDIDATES) -> dict[str, tuple[str, str]]:
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str).fillna("")
    return {
        str(r["handle"]).lower(): (str(r.get("name") or ""), str(r.get("bio") or ""))
        for _, r in df.iterrows()
        if r.get("handle")
    }


def load_paper_meta(path: Path = PAPERS) -> dict[str, tuple[str, str]]:
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str).fillna("")
    return {
        str(r["paper_id"]): (str(r.get("title") or ""), str(r.get("authors") or ""))
        for _, r in df.iterrows()
        if r.get("paper_id")
    }


def _serialise_prob_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ("archetype_probs", "framing_probs"):
        if col in out.columns:
            out[col] = out[col].map(
                lambda v: v
                if isinstance(v, str)
                else (json.dumps(v) if isinstance(v, dict) else "{}")
            )
    return out


def _classify_one(
    p: Any,
    judge: Judge,
    has_role: bool,
    role_ver: str | None,
    profiles: dict[str, tuple[str, str]],
    papers: dict[str, tuple[str, str]],
    s2_lookup: Callable[[str], int] | None,
) -> dict[str, Any]:
    kind = None if pd.isna(p.media_kind) else p.media_kind  # Parquet gives NaN, not None
    image = None
    if kind == "photo" and len(p.media_urls):
        image = fetch_image(p.post_id, p.media_urls[0])
    try:
        lab = judge.label(p.post_id, p.text, kind, image)
        pid = _first_paper_id(p)
        if pid and has_role:
            handle = _clean_str(getattr(p, "author_handle", "")).lower()
            prof_name, prof_bio = profiles.get(handle, ("", ""))
            name = _clean_str(getattr(p, "author_name", None)) or prof_name
            bio = _clean_str(getattr(p, "author_bio", None)) or prof_bio
            title, authors = papers.get(pid, ("", ""))
            role_res = judge.label_role(p.text, name, bio, title, authors, s2_papers=None)
            if role_res["poster_role"] == poster_role.NON and s2_lookup and name:
                s2_n = s2_lookup(name)
                role_res["s2_papers"] = s2_n
                role_res["poster_role"] = poster_role.decide(
                    role_res["name_match"],
                    role_res["p_own_work"],
                    role_res["p_bio_research"],
                    s2_papers=s2_n,
                )
            lab = lab.model_copy(
                update={
                    "poster_role": PosterRole(role_res["poster_role"]),
                    "role_version": role_ver,
                    "p_own_work": role_res["p_own_work"],
                    "p_bio_research": role_res["p_bio_research"],
                    "name_match": role_res["name_match"],
                    "s2_papers": role_res.get("s2_papers"),
                }
            )
    except (JevError, KeyError, ValueError) as e:
        lab = PostLabels(post_id=p.post_id, label_version=judge.version, error=str(e)[:300])
    return lab.model_dump(mode="json")


def run(
    posts: pd.DataFrame,
    judge: Judge,
    cache: pd.DataFrame,
    force: bool = False,
    *,
    paper_meta: dict[str, tuple[str, str]] | None = None,
    author_profiles: dict[str, tuple[str, str]] | None = None,
    s2_lookup: Callable[[str], int] | None = None,
    workers: int = 1,
    checkpoint_path: Path | None = None,
    checkpoint_every: int = 200,
) -> pd.DataFrame:
    """Label every post lacking a successful label at judge.version; failures keep a reason."""
    done: set[str] = set()
    has_role = hasattr(judge, "label_role")
    role_ver = getattr(judge, "role_version", None)
    if not cache.empty and not force:
        ok = cache[(cache["label_version"] == judge.version) & cache["error"].isna()]
        if has_role and role_ver:
            post_pids = {str(r.post_id): _first_paper_id(r) for r in posts.itertuples()}
            if "role_version" in ok.columns:
                ok_ids = set(ok["post_id"])
                role_ok_ids = set(ok.loc[ok["role_version"] == role_ver, "post_id"])
                done = {
                    pid for pid in ok_ids
                    if post_pids.get(str(pid)) is None or pid in role_ok_ids
                }
            else:
                done = {pid for pid in ok["post_id"] if post_pids.get(str(pid)) is None}
        else:
            done = set(ok["post_id"])
    rows = [r for r in cache.to_dict("records")] if not cache.empty else []
    rows = [r for r in rows if r["post_id"] not in set(posts["post_id"]) - done]
    profiles = author_profiles or {}
    papers = paper_meta or {}
    todo = list(posts[~posts["post_id"].isin(done)].itertuples())
    if not todo:
        return pd.DataFrame(rows)

    def _save_ckpt() -> None:
        if checkpoint_path is not None:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            _serialise_prob_cols(pd.DataFrame(rows)).to_parquet(checkpoint_path, index=False)

    if workers <= 1:
        for idx, p in enumerate(todo, start=1):
            rows.append(
                _classify_one(p, judge, has_role, role_ver, profiles, papers, s2_lookup)
            )
            if checkpoint_path and idx % checkpoint_every == 0:
                _save_ckpt()
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [
                pool.submit(
                    _classify_one, p, judge, has_role, role_ver, profiles, papers, s2_lookup
                )
                for p in todo
            ]
            for idx, fut in enumerate(concurrent.futures.as_completed(futs), start=1):
                rows.append(fut.result())
                if checkpoint_path and idx % checkpoint_every == 0:
                    _save_ckpt()
                    tok = getattr(judge, "input_tokens", 0)
                    print(f"checkpointed {idx}/{len(todo)} posts (tokens={tok})")
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--ids", type=Path, help="CSV with a post_id column: label only these")
    ap.add_argument("--out", type=Path, help="write labels here, leaving the main cache alone")
    a = ap.parse_args()
    _load_dotenv()
    posts_all = pd.read_parquet(POSTS)
    posts = posts_all[posts_all["eligible"]]
    if a.ids:  # e.g. the pilot check (decision 41): data/gold/pilot_sheet.csv
        wanted = set(pd.read_csv(a.ids, dtype={"post_id": str})["post_id"])
        posts = posts[posts["post_id"].astype(str).isin(wanted)]
    if a.limit:
        posts = posts.head(a.limit)
    paper_meta = load_paper_meta()
    needed_pids = {pid for r in posts.itertuples() if (pid := _first_paper_id(r))}
    missing_pids = sorted(needed_pids - set(paper_meta))
    if missing_pids:
        try:
            fetched = fetch_arxiv_meta(missing_pids)
            for _, r in fetched.iterrows():
                paper_meta[str(r["paper_id"])] = (
                    str(r.get("title") or ""),
                    str(r.get("authors") or ""),
                )
        except Exception as e:  # noqa: BLE001
            print(f"warning: could not fetch {len(missing_pids)} missing arXiv records: {e}")

    s2_cache: dict[str, int] = {}
    s2_lock = threading.Lock()

    def _s2_lookup(name: str) -> int:
        with s2_lock:
            if name not in s2_cache:
                try:
                    s2_cache[name] = s2.author_ml_paper_count(name)
                except Exception:  # noqa: BLE001
                    s2_cache[name] = 0
            return s2_cache[name]

    judge = JevJudge(model=a.model)
    target = a.out or LABELS
    labels = _serialise_prob_cols(
        run(
            posts,
            judge,
            load_cache(a.out) if a.out else load_cache(),
            a.force,
            paper_meta=paper_meta,
            author_profiles=load_author_profiles(),
            s2_lookup=_s2_lookup,
            workers=a.workers,
            checkpoint_path=target,
        )
    )
    if not labels.empty and {"post_id", "label_version"} <= set(labels.columns):
        labels = labels.drop_duplicates(["post_id", "label_version"], keep="last").reset_index(
            drop=True
        )
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        labels.to_parquet(a.out, index=False)
        failed = int(labels["error"].notna().sum())
        print(f"labelled {len(labels) - failed} -> {a.out}, failed {failed}, "
              f"input tokens {judge.input_tokens}")  # fmt: skip
        return
    LABELS.parent.mkdir(parents=True, exist_ok=True)
    labels.to_parquet(LABELS, index=False)
    cur_labels = labels[
        (labels["label_version"] == judge.version) & labels["error"].isna()
    ].drop_duplicates("post_id", keep="last")
    drop_cols = [c for c in cur_labels.columns if c != "post_id" and c in posts_all.columns]
    merged = posts_all.drop(columns=drop_cols).merge(
        cur_labels.drop(columns=[c for c in ("label_rationale",) if c in cur_labels.columns]),
        on="post_id",
        how="left",
    )
    merged.to_parquet(LABELLED, index=False)
    failed = int(labels["error"].notna().sum())
    print(f"labelled {len(labels) - failed}, failed {failed}, input tokens {judge.input_tokens}")


if __name__ == "__main__":
    main()
