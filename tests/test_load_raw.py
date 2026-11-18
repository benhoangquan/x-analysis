from pathlib import Path

import pytest

from src.ingestion.load_raw import load

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_posts.csv"


def test_load_fixture_validates_dedupes_and_computes_metrics():
    df, rejected = load(FIXTURE)
    # Row 5 has no follower count -> rejected; duplicate id 1 -> deduped.
    assert [r[0] for r in rejected] == [5]
    assert sorted(df["post_id"]) == ["1", "2", "3", "4"]

    p1 = df.set_index("post_id").loc["1"]
    assert p1["r_out"] == pytest.approx(50.0)  # 50000 / 1000
    assert p1["s_intent"] == pytest.approx(820 / 50000)
    assert p1["cr_bmk"] == pytest.approx(2.0)

    p2 = df.set_index("post_id").loc["2"]
    assert p2["r_out"] == pytest.approx(20.0)  # follower floor: 2000 / 100
    assert p2["cr_bmk"] == pytest.approx(2.5)

    p3 = df.set_index("post_id").loc["3"]
    assert p3["r_out"] == 0.0 and p3["s_intent"] == 0.0  # impression floor

    p4 = df.set_index("post_id").loc["4"]
    assert p4["r_out"] != p4["r_out"]  # NaN: impressions missing


def test_load_panel_drops_filler_and_parses_filename_timestamp(tmp_path, monkeypatch):
    import json

    import pandas as pd

    from src.ingestion import load_raw

    seeds_path = tmp_path / "seeds.csv"
    pd.DataFrame({"paper_id": ["2608.00001"], "start": ["2026-08-10"]}).to_csv(
        seeds_path, index=False
    )
    monkeypatch.setattr(load_raw, "SEEDS", seeds_path)

    panel_dir = tmp_path / "panel"
    panel_dir.mkdir()
    pfile = panel_dir / "panel_001_20261114T060737Z.jsonl"
    items = [
        {
            "id": "10",
            "createdAt": "Wed Aug 12 10:00:00 +0000 2026",
            "text": "See https://arxiv.org/abs/2608.00001",
            "author": {"userName": "x1", "followers": 100},
            "likeCount": 1, "replyCount": 0, "retweetCount": 0, "quoteCount": 0,
        },
        {
            "id": "11",
            "createdAt": "Sat Nov 14 10:00:00 +0000 2026",
            "text": "Unrelated filler post",
            "author": {"userName": "spam", "followers": 100},
            "likeCount": 1, "replyCount": 0, "retweetCount": 0, "quoteCount": 0,
        },
    ]
    pfile.write_text("".join(json.dumps(i) + "\n" for i in items))
    df, rejected = load_raw.load(pfile)
    assert list(df["post_id"]) == ["10"]
    assert df.loc[0, "collected_at"].strftime("%Y-%m-%dT%H:%M:%S") == "2026-11-14T06:07:37"
    assert len(rejected) == 1 and "filler" in rejected[0][1]
