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


def test_e1_cross_paper_gate_and_estimators():
    from src.analysis.experiments import gm_ratio_within_strata, run_e1

    rows = []
    tiers = ["<2k", "2k-20k", "20k-200k"]
    cats = ["cs.LG", "cs.CL"]
    for ti, tier in enumerate(tiers):
        for ci, cat in enumerate(cats):
            for k in range(5):
                idx = ti * 10 + ci * 5 + k
                rows.append(dict(
                    post_id=f"nr_{idx}", author_handle=f"nr_au_{idx % 12}", cohort="PANEL",
                    eligible=True, mature=True, is_researcher_post=False,
                    follower_tier=tier, followers_at_collection=500, primary_category=cat,
                    paper_id=f"2608.{idx:05d}", poster_role="NON_RESEARCHER",
                    impressions=4000.0, bookmarks=4.0, quotes=0.0, reposts=0.0, replies=0.0,
                    likes=40.0, created_at="2026-10-01T00:00:00Z", label_version="v2",
                ))
                rows.append(dict(
                    post_id=f"or_{idx}", author_handle=f"or_au_{idx % 12}", cohort="ROSTER",
                    eligible=True, mature=True, is_researcher_post=True,
                    follower_tier=tier, followers_at_collection=500, primary_category=cat,
                    paper_id=f"2608.{idx:05d}", poster_role="ORIGINAL_RESEARCHER",
                    impressions=1000.0, bookmarks=20.0, quotes=0.0, reposts=0.0, replies=0.0,
                    likes=10.0, created_at="2026-10-01T00:00:00Z", label_version="v2",
                ))
    df = pd.DataFrame(rows)
    assert np.isclose(
        gm_ratio_within_strata(df, "poster_role", {"NON_RESEARCHER"}, {"ORIGINAL_RESEARCHER"},
                               "impressions", "follower_tier"),
        4.0,
    )
    rows_out, lv = run_e1(df, None, {"ROSTER", "PANEL"}, n_boot=100, papers_path=df_none())
    assert lv == "v2"
    by_test = {r["test"]: r for r in rows_out}
    assert by_test["H1a"]["status"] == "supported" and np.isclose(by_test["H1a"]["estimate"], 4.0)
    assert by_test["H1b-O"]["status"] == "supported" and by_test["H1b-O"]["estimate"] > 1.0
    assert by_test["H1b-C"]["status"] == "insufficient"


def df_none():
    from pathlib import Path

    return Path("/nonexistent_papers_file.csv")


def test_e2_within_paper_and_robustness():
    from src.analysis.experiments import run_e2

    rows = []
    for p in range(25):
        tier = "<2k" if p % 2 == 0 else "2k-20k"
        rows.append(dict(
            post_id=f"t_{p}", author_handle=f"au_t_{p}", cohort="PANEL",
            eligible=True, mature=True, is_researcher_post=True, follower_tier=tier,
            followers_at_collection=500, paper_id=f"2608.{p:05d}",
            visual_type="PAPER_FIGURE", hook_archetype="CONTESTED_CLAIM",
            impressions=1000.0, bookmarks=30.0, quotes=1.0, reposts=1.0, replies=1.0, likes=5.0,
            created_at="2026-10-01T00:00:00Z", label_version="v2",
        ))
        rows.append(dict(
            post_id=f"c_{p}", author_handle=f"au_c_{p}", cohort="PANEL",
            eligible=True, mature=True, is_researcher_post=True, follower_tier=tier,
            followers_at_collection=500, paper_id=f"2608.{p:05d}",
            visual_type="NONE", hook_archetype="OTHER",
            impressions=1000.0, bookmarks=2.0, quotes=0.0, reposts=0.0, replies=0.0, likes=2.0,
            created_at="2026-10-01T00:00:00Z", label_version="v2",
        ))
    out, _ = run_e2(pd.DataFrame(rows), None, {"PANEL"}, n_boot=100, papers_path=df_none())
    assert out[0]["test"] == "H2" and out[0]["status"] == "supported" and out[0]["estimate"] > 5


def test_e4_uses_real_framing_and_excludes_thread_openers():
    from src.analysis.experiments import run_e4

    rows = []
    for a in range(22):
        # Thread opener question with 0 replies should be excluded from H4a
        rows.append(dict(
            post_id=f"op_{a}", author_handle=f"u{a}", cohort="ROSTER", eligible=True, mature=True,
            is_researcher_post=True, in_author_cap=True, post_kind="thread_opener",
            text="Why does this happen? 1/5", has_number=False, framing="OPEN_QUESTION",
            impressions=1000.0, replies=0.0, bookmarks=1.0, likes=5.0, label_version="v2",
        ))
        # Non-thread question with high replies
        rows.append(dict(
            post_id=f"q_{a}", author_handle=f"u{a}", cohort="ROSTER", eligible=True, mature=True,
            is_researcher_post=True, in_author_cap=True, post_kind="original",
            text="Why does LoRA saturate?", has_number=False, framing="OPEN_QUESTION",
            impressions=1000.0, replies=40.0, bookmarks=1.0, likes=5.0, label_version="v2",
        ))
        # Empirical claim with high bookmarks/like
        rows.append(dict(
            post_id=f"e_{a}", author_handle=f"u{a}", cohort="ROSTER", eligible=True, mature=True,
            is_researcher_post=True, in_author_cap=True, post_kind="original",
            text="Rank 8 drops loss by 12%", has_number=True, framing="DECLARATIVE_EMPIRICAL",
            impressions=1000.0, replies=2.0, bookmarks=25.0, likes=5.0, label_version="v2",
        ))
    rows_out, lv = run_e4(pd.DataFrame(rows), None, {"ROSTER"}, n_boot=100)
    assert lv == "v2"
    by_test = {r["test"]: r for r in rows_out}
    assert by_test["H4a"]["n_posts"] == 44  # the 22 thread openers excluded from H4a
    assert by_test["H4a"]["status"] == "supported"
    assert by_test["H4b"]["status"] == "supported"
    assert by_test["H4c"]["status"] == "insufficient"


def test_e3_decision_model_detects_signal_and_checks_gate():
    from src.analysis.experiments import run_e3

    rng = np.random.default_rng(42)
    rows = []
    for i in range(440):
        au = f"au_{i % 88}"
        tier = "<2k" if i % 2 == 0 else "2k-20k"
        sig = (i // 2) % 2 == 0
        bmk = int(30 + rng.integers(0, 10)) if sig else int(2 + rng.integers(0, 4))
        rows.append(dict(
            post_id=str(i), author_handle=au, cohort="ROSTER", eligible=True, mature=True,
            is_researcher_post=True, follower_tier=tier,
            followers_at_collection=500 if tier == "<2k" else 5000,
            paper_id=f"2608.{i % 50:05d}", poster_role="ORIGINAL_RESEARCHER",
            primary_category="cs.LG" if sig else "cs.CV",
            visual_type="PAPER_FIGURE" if sig else "NONE",
            hook_archetype="CONTESTED_CLAIM" if sig else "OTHER",
            framing="DECLARATIVE_EMPIRICAL" if sig else "DECLARATIVE_OTHER",
            technical_rigor_score=5 if sig else 2,
            char_len=240 if sig else 80, thread_length=1, posted_hour_utc=14,
            has_number=sig, mentions_venue=sig, hype_flags="",
            impressions=1000.0, bookmarks=float(bmk),
            created_at="2026-10-01T00:00:00Z", label_version="v2",
        ))
    df = pd.DataFrame(rows)
    out, _ = run_e3(df, None, {"ROSTER"}, papers_path=df_none(), n_boot=50, n_perm=15)
    h3 = out[0]
    assert h3["test"] == "H3" and h3["status"] == "supported" and h3["estimate"] >= 0.03
    small_out, _ = run_e3(df.head(50), None, {"ROSTER"}, papers_path=df_none(), n_boot=10, n_perm=5)
    assert small_out[0]["status"] == "insufficient"


def test_e5_shapley_shares_sum_to_total_r2():
    from src.analysis.experiments import _oof_r2, _shapley_r2, run_e5

    rng = np.random.default_rng(7)
    rows = []
    for p in range(6):
        for k in range(5):
            idx = p * 5 + k
            rig = float(1 + (idx % 5))
            rows.append(dict(
                post_id=str(idx), author_handle=f"u_{idx}", cohort="PANEL",
                eligible=True, mature=True, is_researcher_post=True,
                follower_tier="<2k", followers_at_collection=400 + 50 * k,
                paper_id=f"2608.{p:05d}", poster_role="ORIGINAL_RESEARCHER",
                primary_category="cs.LG", visual_type="PAPER_FIGURE",
                hook_archetype="CONTESTED_CLAIM", framing="DECLARATIVE_EMPIRICAL",
                technical_rigor_score=rig, char_len=100 + 20 * rig,
                thread_length=1, has_number=True, hype_flags="",
                impressions=float(1000 * np.exp(0.2 * rig + rng.normal(0, 0.05))),
                bookmarks=float(10 * rig), created_at="2026-10-01T00:00:00Z", label_version="v2",
            ))
    df = pd.DataFrame(rows)
    blocks = {"b1": (["technical_rigor_score"], []), "b2": (["char_len"], [])}
    y = np.log(df["impressions"].to_numpy())
    g = df["paper_id"].to_numpy()
    shares = _shapley_r2(df, y, blocks, g)
    total = _oof_r2(df, y, ["technical_rigor_score", "char_len"], [], g)
    assert np.isclose(sum(shares.values()), total, atol=1e-9)

    out, _ = run_e5(df, None, {"PANEL"}, papers_path=df_none(), n_boot=20)
    assert all(r["status"] == "exploratory" for r in out)
    assert any(r["test"] == "log_impressions:paper_icc" for r in out)


def test_e6_emits_confirmation_and_new_features():
    from src.analysis.experiments import run_e6

    rows = []
    for i in range(40):
        is_reply_lean = i % 2 == 0
        rows.append(dict(
            post_id=str(i), author_handle=f"u_{i}", cohort="ROSTER",
            eligible=True, mature=True, is_researcher_post=True, in_author_cap=True,
            follower_tier="<2k",
            text="Why does rank 8 work? ICLR" if is_reply_lean else "Benchmark summary",
            impressions=1000.0,
            replies=50.0 if is_reply_lean else 1.0,
            bookmarks=1.0 if is_reply_lean else 50.0,
            label_version="v2",
        ))
    out, _ = run_e6(pd.DataFrame(rows), None, {"ROSTER"})
    tests = {r["test"] for r in out}
    assert "disc:is_thread_opener" in tests and "disc:mentions_venue" in tests
    assert any(t.startswith("confirm:") for t in tests)


def test_e7_small_account_breakout_vs_polarization():
    from src.analysis.experiments import run_e7

    rows = []
    for i in range(44):
        au = f"sm_{i % 24}"
        fol = 300 if i % 2 == 0 else 1200
        grounded = i < 22
        rows.append(dict(
            post_id=str(i), author_handle=au, cohort="ROSTER",
            eligible=True, mature=True, is_researcher_post=True,
            follower_tier="<2k", followers_at_collection=fol,
            impressions=600.0, reach_vs_expected=2.0,
            hook_archetype="CONTESTED_CLAIM" if grounded else "HOT_TAKE_CULTURE",
            visual_type="PAPER_FIGURE" if grounded else "NONE",
            technical_rigor_score=4 if grounded else 1,
            quotes=1.0 if grounded else 20.0,
            reposts=20.0 if grounded else 2.0,
            bookmarks=30.0 if grounded else 0.0,
            likes=10.0 if grounded else 40.0,
            created_at="2026-10-01T00:00:00Z", label_version="v2",
        ))
    out, _ = run_e7(pd.DataFrame(rows), None, {"ROSTER"}, n_boot=100)
    by_test = {r["test"]: r for r in out}
    assert by_test["H5a"]["status"] == "supported" and by_test["H5a"]["estimate"] > 10
    assert by_test["H5b"]["status"] == "supported" and by_test["H5b"]["estimate"] > 10
    assert by_test["H5c"]["status"] == "supported"
    assert "zero_bmk_share_U=1.00" in by_test["H5c"]["description"]
    assert all(r["_nc"][3] for r in out if r.get("_nc"))
