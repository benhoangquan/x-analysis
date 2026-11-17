import json

import pytest

from src.config import authors_query, cohort_for, paper_query, timeline_query
from src.ingestion.adapters import rows_to_posts
from src.ingestion.apify import (
    BudgetExceededError,
    build_input,
    check_budget,
    record_spend,
    run,
    spent_usd,
)
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

    log = tmp_path / "spend.csv"
    path = run(["q"], 50, "t", token="secret", transport=fake, out_dir=tmp_path, spend_log=log)
    assert "secret" not in seen["url"]
    assert "maxItems=50" in seen["url"]
    assert abs(spent_usd(log) - 0.0004) < 1e-9  # one item at $0.40 per 1k
    assert json.loads(path.read_text().splitlines()[0]) == ITEM


def test_run_requires_token(tmp_path, monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        run(["q"], 50, "t", transport=lambda *a: [], out_dir=tmp_path, spend_log=tmp_path / "s.csv")


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
    assert cohort_for("karpathy") == Cohort.ROSTER
    assert cohort_for("wandb") == Cohort.BENCHMARK
    assert cohort_for("weights_biases") == Cohort.DISCOVERED
    assert cohort_for("someone") == Cohort.DISCOVERED
    assert timeline_query("a", "2026-01-01", "2026-02-01").startswith("from:a")


def test_queries_drop_replies_and_reposts():
    q = authors_query(["a", "b"], "2026-10-01", "2026-11-01")
    assert q.startswith("(from:a OR from:b) since:2026-10-01 until:2026-11-01")
    assert q.endswith("-filter:retweets -filter:replies")
    p = paper_query(["2609.04963", "2610.08144"], "2026-06-01")
    assert p.startswith('(url:"arxiv.org/abs/2609.04963" OR url:"arxiv.org/abs/2610.08144")')
    assert "url:2609.04963" in paper_query(["2609.04963"], "2026-06-01", bare=True)


def test_budget_blocks_worst_case_over_cap(tmp_path):
    log = tmp_path / "spend.csv"
    record_spend("earlier", 1, 50, 24_000, log)  # $9.60 of $10
    assert check_budget(1, 1000, log) == 1000  # $0.40 worst case fits exactly
    with pytest.raises(BudgetExceededError):
        check_budget(2, 1000, log)  # $0.80 worst case would reach $10.40


def test_budget_refusal_happens_before_any_request(tmp_path):
    log = tmp_path / "spend.csv"
    record_spend("earlier", 1, 50, 25_000, log)  # budget used up
    called = []
    with pytest.raises(BudgetExceededError):
        run(["q"], 50, "t", token="x", transport=lambda *a: called.append(a) or [],
            out_dir=tmp_path, spend_log=log)
    assert not called
