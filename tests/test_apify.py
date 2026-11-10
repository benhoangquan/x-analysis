import json

import pytest

from src.config import cohort_for, timeline_query
from src.ingestion.adapters import rows_to_posts
from src.ingestion.apify import build_input, run
from src.ingestion.coverage import coverage
from src.schema import Cohort

ITEM = {
    "id": "123", "url": "https://x.com/rasbt/status/123", "text": "LoRA ablation",
    "createdAt": "Tue Oct 06 07:00:30 +0000 2026", "likeCount": 5, "retweetCount": 1,
    "replyCount": 2, "quoteCount": 0, "bookmarkCount": 4, "viewCount": 900,
    "author": {"userName": "rasbt", "id": "9", "followers": 300000},
    "cohort": "BENCHMARK", "collected_at": "2026-11-10T00:00:00Z", "source": "apify",
}  # fmt: skip


def test_run_stores_raw_verbatim_and_hides_token(tmp_path):
    seen = {}

    def fake(url, payload, token):
        seen.update(url=url, payload=payload)
        return [ITEM]

    path = run(["q"], 50, "t", token="secret", transport=fake, out_dir=tmp_path)
    assert "secret" not in seen["url"]
    assert json.loads(path.read_text().splitlines()[0]) == ITEM


def test_run_requires_token(tmp_path, monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        run(["q"], 50, "t", transport=lambda *a: [], out_dir=tmp_path)


def test_input_rules():
    with pytest.raises(ValueError):
        build_input(["q"], 10)
    with pytest.raises(ValueError):
        build_input(["q"] * 6, 50)


def test_nested_author_and_twitter_date_parse():
    posts, rejected = rows_to_posts([ITEM])
    assert not rejected
    p = posts[0]
    assert (p.author_handle, p.followers_at_collection, p.impressions) == ("rasbt", 300000, 900)
    assert p.created_at.year == 2026


def test_coverage_flags_missing_impressions(tmp_path):
    item = {k: v for k, v in ITEM.items() if k != "viewCount"}
    f = tmp_path / "x.jsonl"
    f.write_text(json.dumps(item) + "\n")
    assert coverage(f)["impressions"] == 0.0


def test_cohorts_and_query():
    assert cohort_for("TiptreeSystems") == Cohort.OWN
    assert cohort_for("karpathy") == Cohort.BENCHMARK
    assert cohort_for("someone") == Cohort.DISCOVERED
    assert timeline_query("a", "2026-01-01", "2026-02-01").startswith("from:a")
