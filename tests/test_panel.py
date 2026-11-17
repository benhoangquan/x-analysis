import json
from datetime import date
from pathlib import Path

import pandas as pd

from src.config import MAX_QUERY_CHARS
from src.ingestion.apify import record_spend
from src.ingestion.panel import (
    collect,
    draw_seeds,
    group_size,
    panel_posts,
    query_for,
    seed_pool,
    window_start,
)


def _lists():
    return {
        date(2026, 8, 10): [{"paper": {"id": "2608.00001", "publishedAt": "2026-08-08T00:00Z",
                                       "upvotes": 90}, "title": "A"},
                            {"paper": {"id": "not-an-id"}}],
        date(2026, 8, 11): [{"paper": {"id": "2608.00001", "upvotes": 95}, "title": "A"},
                            {"paper": {"id": "2608.00002", "upvotes": 1}, "title": "B"}],
    }  # fmt: skip


def test_seed_pool_dedupes_and_keeps_first_listing():
    pool = seed_pool(_lists())
    assert list(pool["paper_id"]) == ["2608.00001", "2608.00002"]
    assert pool.loc[0, "listed"] == "2026-08-10" and pool.loc[0, "published"] == "2026-08-08"


def _seeds(n):
    return pd.DataFrame({"paper_id": [f"2608.{i:05d}" for i in range(n)],
                         "published": ["2026-08-10"] * n, "start": ["2026-08-10"] * n})  # fmt: skip


def test_draw_is_uniform_and_ignores_pool_order():
    pool = _seeds(50).assign(upvotes=range(50))
    a = draw_seeds(pool, 10, seed=1)
    b = draw_seeds(pool.sort_values("upvotes", ascending=False), 10, seed=1)
    assert list(a["paper_id"]) == list(b["paper_id"]) and len(a) == 10


def test_groups_respect_query_length_and_target():
    seeds = _seeds(40)
    k = group_size(seeds, posts_per_paper=1.0)  # wants 70 papers, length allows fewer
    assert len(query_for(seeds.iloc[:k])) <= MAX_QUERY_CHARS
    assert group_size(seeds, posts_per_paper=35.0) == 2


def _fake_runner(posts_per_paper):
    def run(queries, max_items, label, out_dir, spend_log):
        n_ids = queries[0].count("url:")
        n = min(max_items, n_ids * posts_per_paper)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = Path(out_dir) / f"{label}.jsonl"
        path.write_text("".join(json.dumps({"id": f"{label}-{i}"}) + "\n" for i in range(n)))
        record_spend(label, 1, max_items, n, spend_log)
        return path
    return run


def test_collect_splits_capped_runs_and_finishes(tmp_path):
    out = collect(_seeds(12), _fake_runner(20), tmp_path / "s.csv", out_dir=tmp_path / "p")
    assert out["papers_done"] == 12 and out["papers_left"] == 0
    assert out["capped"] >= 1  # first guess (7 papers x 20 posts) hits the cap


def test_collect_stops_at_panel_budget(tmp_path):
    log = tmp_path / "s.csv"
    record_spend("panel_000", 1, 100, 3700, log)  # $1.48 of the panel's $1.50
    record_spend("roster_x", 1, 100, 10_000, log)  # other spend does not count here
    out = collect(_seeds(5), _fake_runner(5), log, out_dir=tmp_path / "p")
    assert out["stopped_by_budget"] and out["runs"] == 0


LINK = "arxiv.org/abs/2608.00001"


def test_panel_posts_keep_30_day_window(tmp_path):
    seeds = pd.DataFrame({"paper_id": ["2608.00001"], "start": ["2026-08-10"]})
    items = [
        {"id": "1", "createdAt": "Wed Aug 12 10:00:00 +0000 2026", "text": LINK,
         "author": {"userName": "A", "followers": 10}},
        {"id": "2", "createdAt": "Fri Sep 18 10:00:00 +0000 2026", "text": LINK,
         "author": {"userName": "B", "followers": 10}},
    ]  # fmt: skip
    f = tmp_path / "x.jsonl"
    f.write_text("".join(json.dumps(i) + "\n" for i in items))
    posts = panel_posts(seeds, [f])
    assert list(posts["post_id"]) == ["1"] and posts.loc[0, "handle"] == "a"


def test_window_start_falls_back_to_listing_when_date_is_implausible():
    assert window_start("2026-08-08", "2026-08-10") == "2026-08-08"
    assert window_start("2026-06-18", "2026-08-24") == "2026-08-22"  # 67 days early
    assert window_start("2026-11-03", "2026-10-07") == "2026-10-05"  # after the listing


ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2608.00677v2</id>
    <published>2026-08-01T17:59:00Z</published>
    <title>OpenART:  Scaling
      Agent Red Teaming</title>
    <author><name>Ada Lovelace</name></author>
    <author><name>Alan Turing</name></author>
    <arxiv:comment>Code at https://github.com/x/openart</arxiv:comment>
    <arxiv:primary_category term="cs.LG"/>
  </entry>
</feed>"""


def test_parse_arxiv_atom():
    from src.ingestion.panel import parse_arxiv_atom

    (row,) = parse_arxiv_atom(ATOM_FEED)
    assert row["paper_id"] == "2608.00677" and row["arxiv_v1"] == "2026-08-01"
    assert row["authors"] == "Ada Lovelace; Alan Turing" and row["n_authors"] == 2
    assert row["title"] == "OpenART: Scaling Agent Red Teaming"
    assert row["primary_category"] == "cs.LG" and row["has_code"]


def test_author_name_match():
    from src.ingestion.panel import is_paper_author

    authors = "José Álvarez; Wei Chen; Ada Lovelace"
    assert is_paper_author("Jose Alvarez (at NeurIPS)", authors)
    assert is_paper_author("Wei Chen 陈伟", authors)
    assert not is_paper_author("Wei Zhang", authors)
    assert not is_paper_author("AK", authors)
