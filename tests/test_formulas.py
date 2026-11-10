import numpy as np
import pandas as pd
import pytest

from src.metrics.formulas import (
    add_metrics,
    bookmark_conversion_rate,
    high_intent_score,
    outperformance_ratio,
)


def s(*v):
    return pd.Series(v, dtype="float64")


def test_r_out_basic_and_follower_floor():
    r = outperformance_ratio(s(50000, 2000), s(1000, 50))
    assert r.tolist() == [50.0, 20.0]  # 2000 / max(50, 100) = 20


def test_s_intent_hand_computed():
    # (3*100 + 2*(10+30) + 2*20 + 400) / 50000 = 820 / 50000
    v = high_intent_score(s(100), s(10), s(30), s(20), s(400), s(50000))
    assert v.iloc[0] == pytest.approx(0.0164)


def test_impression_floor_avoids_div_zero():
    assert bookmark_conversion_rate(s(0), s(0)).iloc[0] == 0.0
    assert high_intent_score(s(1), s(0), s(0), s(0), s(0), s(0)).iloc[0] == 3.0


def test_cr_bmk_per_thousand():
    assert bookmark_conversion_rate(s(100), s(50000)).iloc[0] == pytest.approx(2.0)


def test_add_metrics_missing_impressions_is_nan():
    df = pd.DataFrame(
        {
            "impressions": [None],
            "bookmarks": [1],
            "followers_at_collection": [500],
            "quotes": [0],
            "reposts": [0],
            "replies": [0],
            "likes": [3],
        }
    )
    out = add_metrics(df)
    assert np.isnan(out.loc[0, "r_out"]) and np.isnan(out.loc[0, "cr_bmk"])
