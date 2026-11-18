import numpy as np
import pandas as pd

from src.analysis.embed_map import (
    COLOR_FIELDS,
    build_payload,
    compute_bin_skyline,
    compute_region_stats,
    embed_posts,
    project_1d,
    project_2d,
    render_html,
    render_impression_html,
)


def test_embed_map_projection_purity_and_html():
    rng = np.random.default_rng(42)
    rows = []
    hooks = ["CONTESTED_CLAIM", "PRODUCT_DEMO", "OTHER"]
    for i in range(30):
        rows.append(
            dict(
                post_id=f"p_{i}",
                author_handle="tiptreesystems" if i == 0 else (
                    "martincsweiss1" if i == 1 else f"au_{i % 10}"
                ),
                cohort="OWN" if i < 2 else "ROSTER",
                url=f"https://x.com/i/web/status/p_{i}",
                eligible=True,
                mature=True,
                is_researcher_post=i >= 2 or i == 0,
                in_author_cap=True,
                follower_tier="<2k" if i % 2 == 0 else "2k-20k",
                hook_archetype=hooks[i % 3],
                visual_type="PAPER_FIGURE" if i % 3 == 0 else "NONE",
                framing="DECLARATIVE_EMPIRICAL" if i % 2 == 0 else "OPEN_QUESTION",
                poster_role="ORIGINAL_RESEARCHER" if i % 4 == 0 else "NON_RESEARCHER",
                media_kind=None,
                impressions=1000.0 + i * 50,
                baseline_ratio=0.8 + (i % 5) * 0.2,
                reach_vs_expected=0.9 + (i % 4) * 0.25,
                bookmarks=10.0 + i,
                cr_bmk=10.0 + i,
                cr_bmk_shrunk=5.0 + i * 0.3,
                text=f"Synthetic ML post {i} about cluster {i % 3}",
            )
        )
    df = pd.DataFrame(rows)

    def dummy_embed(texts: list[str], _paths: list[object]) -> tuple[np.ndarray, np.ndarray]:
        vecs = np.zeros((len(texts), 12), dtype="float32")
        for idx in range(len(texts)):
            vecs[idx, (idx % 3) * 4 : (idx % 3) * 4 + 4] = 1.0
            vecs[idx] += rng.normal(0, 0.05, size=12).astype("float32")
        return vecs, np.zeros(len(texts), dtype=bool)

    pca_vecs, has_img = embed_posts(df, embed_fn=dummy_embed)
    umap_xy, tsne_xy = project_2d(pca_vecs)
    u1, t1 = project_1d(pca_vecs)
    assert umap_xy.shape == (30, 2) and np.isfinite(umap_xy).all()
    assert tsne_xy.shape == (30, 2) and np.isfinite(tsne_xy).all()
    assert u1.shape == (30,) and np.isfinite(u1).all()
    assert t1.shape == (30,) and np.isfinite(t1).all()

    purity_df, own_df = compute_region_stats(
        df, pca_vecs, umap_xy, tsne_xy, umap_1d=u1, tsne_1d=t1, k=5
    )
    hook_row = purity_df.set_index("field").loc["hook_archetype"]
    assert hook_row["pca_50d_purity"] > hook_row["chance_baseline"]
    assert "umap_1d_purity" in purity_df.columns and "tsne_1d_purity" in purity_df.columns
    assert set(own_df["account"]) == {"@tiptreesystems", "@martincsweiss1"}

    skyline_df = compute_bin_skyline(df, u1, n_bins=4)
    assert len(skyline_df) == 4 and skyline_df["n_posts"].sum() == 29

    payload = build_payload(df, umap_xy, tsne_xy, has_img, umap_1d=u1, tsne_1d=t1)
    html_out = render_html(payload, purity_df, own_df)
    assert "Exploratory map (Decision D9)" in html_out
    for field, _ in COLOR_FIELDS:
        assert f'value="{field}"' in html_out
    assert "@tiptreesystems" in html_out and "@martincsweiss1" in html_out
    assert "overview.html" in html_out

    imp_html = render_impression_html(payload, purity_df, skyline_df)
    assert "Exploratory map (Decision D9)" in imp_html
    for y_opt in ("impressions", "baseline_ratio", "reach_vs_expected"):
        assert f'value="{y_opt}"' in imp_html
    assert 'value="lt2k_own"' in imp_html
    assert "@tiptreesystems" in imp_html and "@martincsweiss1" in imp_html
