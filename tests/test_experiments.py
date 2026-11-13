import numpy as np
import pandas as pd

from src.analysis.experiments import (
    Spec,
    cluster_bootstrap,
    framing_proxy,
    mh_rate_ratio,
    run_test,
    shuffle_within,
    verdict,
)


def _frame(rr: float, n_strata: int = 30) -> pd.DataFrame:
    rows = []
    for s in range(n_strata):
        for arm, rate in (("A", 0.01 * rr), ("B", 0.01)):
            for k in range(2):
                rows.append(dict(post_id=f"{s}{arm}{k}", author_handle=f"u{s}{arm}{k}",
                                 s=f"p{s}", arm=arm, imp=1000.0, bmk=1000.0 * rate))
    return pd.DataFrame(rows)


def test_mh_recovers_known_ratio():
    assert abs(mh_rate_ratio(_frame(2.0), "arm", {"A"}, {"B"}, "bmk", "imp", "s") - 2.0) < 1e-9


def test_mh_ignores_strata_missing_an_arm():
    d = _frame(2.0)
    extra = pd.DataFrame(
        [dict(post_id="x", author_handle="x", s="solo", arm="A", imp=1e6, bmk=1e5)]
    )
    d = pd.concat([d, extra])
    assert abs(mh_rate_ratio(d, "arm", {"A"}, {"B"}, "bmk", "imp", "s") - 2.0) < 1e-9


def test_verdict_rule():
    assert verdict(1.1, 1.9, "up") == "supported"
    assert verdict(0.5, 0.9, "up") == "refuted"
    assert verdict(0.9, 1.1, "up") == "refuted"  # inside [0.83, 1.2]
    assert verdict(0.8, 1.6, "up") == "inconclusive"
    assert verdict(0.9, 1.1, "null") == "supported"
    assert verdict(1.3, 2.0, "null") == "refuted"


def test_negative_control_covers_one_and_real_effect_detected():
    d = _frame(2.0)
    t = Spec("T", "t", "arm", {"A"}, {"B"}, "bmk", "imp", "s", "up", cluster="s")
    row = run_test(d, t, None, "synthetic")
    assert row["status"] == "supported"
    assert row["_nc"][3]  # shuffled-arm interval contains 1


def test_gate_fails_on_few_strata():
    d = _frame(2.0, n_strata=5)
    t = Spec("T", "t", "arm", {"A"}, {"B"}, "bmk", "imp", "s", "up", cluster="s")
    assert run_test(d, t, None, "x")["status"] == "insufficient"


def test_shuffle_preserves_counts_within_strata():
    d = _frame(1.0)
    sh = shuffle_within(d, "arm", "s")
    assert sh.groupby("s")["arm"].value_counts().sort_index().equals(
        d.groupby("s")["arm"].value_counts().sort_index()
    )


def test_framing_proxy_precedence():
    t = pd.Series(["Do you know why?", "Why does LoRA saturate?", "Rank 8 hits 71.2", "New paper"])
    n = pd.Series([False, False, True, False])
    assert framing_proxy(t, n).tolist() == [
        "CURIOSITY_GAP", "OPEN_QUESTION", "DECLARATIVE_EMPIRICAL", "DECLARATIVE_OTHER",
    ]


def test_bootstrap_interval_contains_estimate():
    d = _frame(1.5)
    f = lambda x: mh_rate_ratio(x, "arm", {"A"}, {"B"}, "bmk", "imp", "s")  # noqa: E731
    est, lo, hi = cluster_bootstrap(d.assign(s=d["s"]), f, "s", n_boot=50)
    assert np.isclose(est, 1.5) and lo <= est <= hi
