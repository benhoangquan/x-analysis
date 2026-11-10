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
