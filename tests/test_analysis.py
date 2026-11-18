import pandas as pd
import pytest

from src.analysis.lift import lift_table, pooled_cr_bmk
from src.analysis.report import check_label_gate, generate_findings
from src.analysis.swipe import select_swipe_file


def _corpus_df() -> pd.DataFrame:
    rows = []
    # 22 posts from 11 authors in <2k with CONTESTED_CLAIM (high bmk) and 22 with OTHER (low bmk)
    for i in range(22):
        rows.append(dict(
            post_id=f"c_{i}", author_handle=f"au_{i % 11}", cohort="ROSTER",
            url=f"https://x.com/i/web/status/c_{i}",
            eligible=True, mature=True, is_researcher_post=True, in_author_cap=True,
            follower_tier="<2k", hook_archetype="CONTESTED_CLAIM", visual_type="PAPER_FIGURE",
            framing="DECLARATIVE_EMPIRICAL", technical_rigor_score=4, hype_flags="",
            baseline_ratio=1.5, impressions=1000.0, bookmarks=40.0, cr_bmk=40.0,
            cr_bmk_shrunk=30.0, label_version="v2",
        ))
        rows.append(dict(
            post_id=f"o_{i}", author_handle=f"au_{100 + (i % 11)}", cohort="ROSTER",
            url=f"https://x.com/i/web/status/o_{i}",
            eligible=True, mature=True, is_researcher_post=True, in_author_cap=True,
            follower_tier="<2k", hook_archetype="OTHER", visual_type="NONE",
            framing="DECLARATIVE_OTHER", technical_rigor_score=2, hype_flags="",
            baseline_ratio=1.2, impressions=1000.0, bookmarks=2.0, cr_bmk=2.0,
            cr_bmk_shrunk=6.0, label_version="v2",
        ))
    # Thin cell: only 5 posts from 5 authors
    for i in range(5):
        rows.append(dict(
            post_id=f"t_{i}", author_handle=f"thin_{i}", cohort="ROSTER",
            url=f"https://x.com/i/web/status/t_{i}",
            eligible=True, mature=True, is_researcher_post=True, in_author_cap=True,
            follower_tier="<2k", hook_archetype="PRODUCT_DEMO", visual_type="VIDEO_DEMO",
            framing="DECLARATIVE_OTHER", technical_rigor_score=3, hype_flags="",
            baseline_ratio=1.1, impressions=1000.0, bookmarks=50.0, cr_bmk=50.0,
            cr_bmk_shrunk=35.0, label_version="v2",
        ))
    return pd.DataFrame(rows)


def test_pooled_cr_bmk_and_lift_table_gate():
    df = _corpus_df()
    assert pooled_cr_bmk(df.head(2)) == pytest.approx(21.0)
    tbl = lift_table(df, ["follower_tier", "hook_archetype"], n_boot=200).set_index(
        ["follower_tier", "hook_archetype"]
    )
    cc = tbl.loc[("<2k", "CONTESTED_CLAIM")]
    assert cc["cr_bmk"] == pytest.approx(40.0)
    assert bool(cc["passes_gate"]) is True and cc["evidence"] == "ok"
    assert cc["lift_ci_low"] > 1.0

    thin = tbl.loc[("<2k", "PRODUCT_DEMO")]
    assert bool(thin["passes_gate"]) is False and thin["evidence"] == "insufficient data"


def test_swipe_file_excludes_hype_rigor1_low_baseline_and_enforces_author_cap():
    rows = []
    # 40 passing posts -> target 2 posts; add 30 from one author so cap limits them
    for i in range(40):
        rows.append(dict(
            post_id=f"p_{i}", author_handle="prolific" if i < 20 else f"au_{i}",
            eligible=True, mature=True, is_researcher_post=True,
            follower_tier="<2k", baseline_ratio=1.5, hype_flags="",
            technical_rigor_score=4, cr_bmk_shrunk=100.0 - i,
        ))
    # Should all be filtered out by swipe eligibility rules
    rows += [
        dict(post_id="bad_hype", author_handle="x1", eligible=True, mature=True,
             is_researcher_post=True, follower_tier="<2k", baseline_ratio=5.0,
             hype_flags="clickbait", technical_rigor_score=4, cr_bmk_shrunk=999.0),
        dict(post_id="bad_rigor", author_handle="x2", eligible=True, mature=True,
             is_researcher_post=True, follower_tier="<2k", baseline_ratio=5.0,
             hype_flags="", technical_rigor_score=1, cr_bmk_shrunk=999.0),
        dict(post_id="bad_base", author_handle="x3", eligible=True, mature=True,
             is_researcher_post=True, follower_tier="<2k", baseline_ratio=0.9,
             hype_flags="", technical_rigor_score=4, cr_bmk_shrunk=999.0),
    ]
    df = pd.DataFrame(rows)
    curation = pd.DataFrame({"post_id": ["p_0"], "drop": ["yes"]})
    swipe = select_swipe_file(df, curation)
    assert "p_0" not in set(swipe["post_id"])
    assert not {"bad_hype", "bad_rigor", "bad_base"} & set(swipe["post_id"])
    assert len(swipe) == 3  # ceil(0.05 * 43) = 3
    assert swipe["author_handle"].value_counts().max() == 1


def test_findings_enforces_validation_gate_and_builds_templates(tmp_path):
    df = _corpus_df()
    # Add own account posts for scorecard check
    own = pd.DataFrame([dict(
        post_id="own_1", author_handle="tiptreesystems", cohort="OWN",
        url="https://x.com/tiptreesystems/status/own_1",
        eligible=True, mature=True, is_researcher_post=False, in_author_cap=True,
        follower_tier="<2k", hook_archetype="OTHER", visual_type="NONE",
        framing="DECLARATIVE_OTHER", technical_rigor_score=2, hype_flags="",
        baseline_ratio=1.0, impressions=200.0, bookmarks=1.0, cr_bmk=5.0,
        cr_bmk_shrunk=8.0, label_version="v2",
    )])
    full = pd.concat([df, own], ignore_index=True)

    unval = generate_findings(full, validated=False, dropped_filler=12, n_boot=100)
    assert "Withheld (Decision 19 gate)" in unval
    assert "### Template:" not in unval
    assert "Filler items dropped at ingestion:** 12" in unval

    trusted = generate_findings(
        full, validated=False, trust_jev=True, dropped_filler=12, n_boot=100
    )
    assert "Decision 60" in trusted
    assert "### Template: `<2k` × `hook_archetype=CONTESTED_CLAIM`" in trusted

    val = generate_findings(full, validated=True, n_boot=100)
    assert "### Template: `<2k` × `hook_archetype=CONTESTED_CLAIM`" in val
    assert "insufficient data" in val
    assert "@tiptreesystems" in val
    assert "au_0" not in val  # no inline roster author handles

    # check_label_gate fails cleanly when files are missing
    ok, _ = check_label_gate(tmp_path / "missing.csv", tmp_path / "missing.parquet")
    assert not ok


def test_charts_page_handles_v1_and_empty_own():
    from src.analysis.charts import page

    df = _corpus_df().assign(followers_at_collection=500, text="sample post")
    html_out = page(df)
    assert "Tiptree X post overview" in html_out and "Plotly.react" in html_out
