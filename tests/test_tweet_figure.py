import pandas as pd
from PIL import Image

from src.analysis.tweet_figure import compute_ablation_stats, render_ablation_figure


def test_compute_ablation_stats_and_render_2400x1350(tmp_path):
    rows = []
    formats = [
        ("NONE", False),
        ("NONE", True),
        ("OTHER_IMAGE", True),
        ("VIDEO_DEMO", False),
        ("PAPER_FIGURE", True),
    ]
    for i in range(50):
        vis, has_link = formats[i % 5]
        bmk = 3 if vis == "NONE" and not has_link else (12 if vis == "PAPER_FIGURE" else 7)
        rows.append(
            dict(
                post_id=f"p_{i}",
                author_handle=f"au_{i % 12}",
                cohort="ROSTER",
                eligible=True,
                mature=True,
                is_researcher_post=True,
                in_author_cap=True,
                follower_tier="<2k" if i % 2 == 0 else "2k-20k",
                visual_type=vis,
                has_link=has_link,
                impressions=1000.0,
                bookmarks=float(bmk),
            )
        )
    rows.append(
        dict(
            post_id="sparse_map",
            author_handle="au_0",
            cohort="ROSTER",
            eligible=True,
            mature=True,
            is_researcher_post=True,
            in_author_cap=True,
            follower_tier="<2k",
            visual_type="LACUNA_MAP",
            has_link=True,
            impressions=1000.0,
            bookmarks=5.0,
        )
    )
    df = pd.DataFrame(rows)

    stats, meta = compute_ablation_stats(df, n_boot=50)
    assert len(stats) == 5
    assert meta["n_posts_all"] == 50 and meta["omitted_n"] == 1
    by_key = stats.set_index("key")
    assert by_key.loc["paper_figure", "cr_bmk"] > by_key.loc["plain_no_link", "cr_bmk"]

    png_path = tmp_path / "ablation.png"
    pdf_path = tmp_path / "ablation.pdf"
    render_ablation_figure(stats, meta, png_path, pdf_path)
    assert png_path.exists() and pdf_path.exists()
    with Image.open(png_path) as im:
        assert im.size == (2400, 1350)
