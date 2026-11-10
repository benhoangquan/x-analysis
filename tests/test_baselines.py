import numpy as np
import pandas as pd
import pytest

from src.metrics.baselines import (
    add_baselines,
    add_eligibility,
    fit_reach_model,
    follower_tier,
    trailing_baseline,
)


def make(rows):
    base = {
        "post_id": "x", "author_handle": "a", "cohort": "OWN", "followers_at_collection": 1000,
        "created_at": "2026-10-01T00:00:00Z", "collected_at": "2026-11-10T00:00:00Z",
        "impressions": 100, "is_reply": False, "is_retweet": False, "in_reply_to_username": None,
        "r_out": 0.1, "s_intent": 0.01, "cr_bmk": 0.0,
    }  # fmt: skip
    return pd.DataFrame([{**base, **r, "post_id": str(i)} for i, r in enumerate(rows)])


def test_tier_boundaries():
    t = follower_tier(pd.Series([0, 1999, 2000, 19999, 20000, 200000, 5_000_000]))
    assert t.tolist() == ["<2k", "<2k", "2k-20k", "2k-20k", "20k-200k", ">200k", ">200k"]


def test_maturity_and_eligibility():
    df = make([
        {},
        {"created_at": "2026-11-08T00:00:00Z"},
        {"is_reply": True, "in_reply_to_username": "A"},
        {"is_reply": True, "in_reply_to_username": "other"},
        {"is_retweet": True},
    ])  # fmt: skip
    e = add_eligibility(df)
    assert e["mature"].tolist() == [True, False, True, True, True]
    assert e["eligible"].tolist() == [True, True, False, False, False]
    assert e["is_self_reply"].tolist() == [False, False, True, False, False]


def test_fit_recovers_known_power_law():
    f = np.array([200, 1000, 5000, 20000, 100000, 500000])
    imp = (3 * f**0.8).round().astype(int)
    df = make(
        [
            {"followers_at_collection": int(a), "impressions": int(b)}
            for a, b in zip(f, imp, strict=True)
        ]
    )
    m = fit_reach_model(add_eligibility(df))
    assert m.slope == pytest.approx(0.8, abs=0.01)
    assert not m.reliable  # 6 posts, 1 author: below the evidence gate


def test_reach_vs_expected_is_one_on_the_fit_line():
    f = [200, 1000, 5000, 20000]
    df = make([{"followers_at_collection": a, "impressions": round(3 * a**0.8)} for a in f])
    out, _ = add_baselines(df)
    assert out["reach_vs_expected"].between(0.99, 1.01).all()


def test_trailing_baseline_hand_computed():
    days = ["2026-09-20", "2026-09-25", "2026-10-01", "2026-10-05", "2026-10-10"]
    imps = [100, 300, 200, 1000, 50]
    df = add_eligibility(make([{"created_at": f"{d}T00:00:00Z", "impressions": i}
                               for d, i in zip(days, imps, strict=True)]))  # fmt: skip
    b = trailing_baseline(df)
    assert b.iloc[:3].isna().all()  # fewer than 3 prior posts
    assert b.iloc[3] == 200  # median(100, 300, 200)
    assert b.iloc[4] == 250  # prior 30 days: 100, 300, 200, 1000 -> (200 + 300) / 2
