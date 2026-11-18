"""Publication-grade 2-panel ablation figure on ML researcher post visuals and save rate."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from src.analysis.lift import analysis_corpus, lift_table  # noqa: E402

SRC = Path("data/processed/posts_labelled.parquet")
OUT_PNG = Path("outputs/reports/researcher_post_ablation.png")
OUT_PDF = Path("outputs/reports/researcher_post_ablation.pdf")

ROW_SPECS: list[tuple[str, str]] = [
    ("plain_no_link", "Plain text\n(no link)"),
    ("text_link", "Plain text + link\n(92% include numbers)"),
    ("generic_image", "Generic image\n(title card, photo, screenshot)"),
    ("video_demo", "Video / UI demo"),
    ("paper_figure", "Paper figure /\nablation table"),
]


def _assign_format_row(df: pd.DataFrame) -> pd.Series:
    vis = df["visual_type"].astype(str)
    has_link = df["has_link"].fillna(False).astype(bool)
    return pd.Series(
        np.select(
            [
                (vis == "NONE") & (~has_link),
                (vis == "NONE") & has_link,
                vis == "OTHER_IMAGE",
                vis == "VIDEO_DEMO",
                vis == "PAPER_FIGURE",
            ],
            [k for k, _ in ROW_SPECS],
            default="omitted",
        ),
        index=df.index,
    )


def compute_ablation_stats(
    df: pd.DataFrame, *, n_boot: int = 2000, seed: int = 20261112
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Compute share and pooled CR_bmk + 95% author-clustered CIs for the 5 format rows."""
    corp = analysis_corpus(df).copy()
    corp["_fmt"] = _assign_format_row(corp)
    omitted_n = int((corp["_fmt"] == "omitted").sum())
    sub = corp[corp["_fmt"] != "omitted"].copy()
    lt2k = sub[sub["follower_tier"] == "<2k"].copy()

    t_all = lift_table(sub, "_fmt", n_boot=n_boot, seed=seed).set_index("_fmt")
    t_small = (
        lift_table(lt2k, "_fmt", n_boot=min(1000, n_boot), seed=seed).set_index("_fmt")
        if not lt2k.empty
        else pd.DataFrame()
    )

    total_n = max(len(sub), 1)
    rows = []
    for key, label in ROW_SPECS:
        if key not in t_all.index:
            continue
        r = t_all.loc[key]
        s_ok = not t_small.empty and key in t_small.index
        sr = t_small.loc[key] if s_ok else None
        rows.append(
            dict(
                key=key,
                label=label,
                n_posts=int(r["n_posts"]),
                n_authors=int(r["n_authors"]),
                share_pct=float(r["n_posts"]) / total_n * 100.0,
                cr_bmk=float(r["cr_bmk"]),
                ci_low=float(r["ci_low"]),
                ci_high=float(r["ci_high"]),
                lt2k_n_posts=int(sr["n_posts"]) if sr is not None else 0,
                lt2k_n_authors=int(sr["n_authors"]) if sr is not None else 0,
                lt2k_cr_bmk=float(sr["cr_bmk"]) if sr is not None else float("nan"),
            )
        )

    meta = {
        "n_posts_all": len(sub),
        "n_authors_all": int(sub["author_handle"].nunique()),
        "n_posts_lt2k": len(lt2k),
        "n_authors_lt2k": int(lt2k["author_handle"].nunique()),
        "omitted_n": omitted_n,
    }
    return pd.DataFrame(rows), meta


def render_ablation_figure(
    stats: pd.DataFrame,
    meta: dict[str, int],
    out_png: Path,
    out_pdf: Path | None = None,
) -> None:
    """Render 2400x1350 (16:9) academic 2-panel supply-vs-saves figure to PNG and optional PDF."""
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Liberation Sans", "Noto Sans", "DejaVu Sans"],
            "axes.edgecolor": "#d4d2c9",
            "axes.linewidth": 0.9,
        }
    )
    bg = "#fcfcfb"
    ink = "#181816"
    muted = "#5e5c57"
    slate_bar = "#c7ccd4"
    slate_vid = "#9aa4b2"
    accent = "#1d5fbf"
    accent_dark = "#16468f"
    small_col = "#d95926"
    grid_col = "#e5e3dc"

    fig = plt.figure(figsize=(10.0, 5.625), dpi=240, facecolor=bg)
    gs = fig.add_gridspec(
        1, 2, width_ratios=[0.40, 0.60],
        left=0.205, right=0.965, top=0.755, bottom=0.165, wspace=0.07,
    )
    ax_left = fig.add_subplot(gs[0, 0], facecolor=bg)
    ax_right = fig.add_subplot(gs[0, 1], sharey=ax_left, facecolor=bg)

    y = np.arange(len(stats))
    keys = stats["key"].tolist()

    for ax in (ax_left, ax_right):
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(axis="both", labelsize=9.2, colors=ink)
        for yi in y:
            ax.axhline(yi, color="#efede7", lw=0.8, zorder=0)
        ax.axhspan(3.54, 4.46, color="#eef4fd", zorder=0)

    # Panel (a): What ML researchers post (% of posts)
    bar_colors = [
        accent if k == "paper_figure" else (slate_vid if k == "video_demo" else slate_bar)
        for k in keys
    ]
    edge_colors = [accent_dark if k == "paper_figure" else "#8f98a6" for k in keys]
    ax_left.barh(
        y,
        stats["share_pct"],
        height=0.56,
        color=bar_colors,
        edgecolor=edge_colors,
        linewidth=0.7,
        zorder=3,
    )
    for yi, row in zip(y, stats.itertuples(), strict=True):
        is_top = row.key == "paper_figure"
        ax_left.text(
            row.share_pct + 0.9,
            yi,
            f"{row.share_pct:.1f}% (n={row.n_posts})",
            va="center",
            ha="left",
            fontsize=8.6,
            fontweight="bold" if is_top else "normal",
            color=accent_dark if is_top else ink,
            zorder=4,
        )

    # Bracket over rows 0 and 1 (no-visual rows)
    no_vis_pct = float(
        stats.loc[stats["key"].isin(["plain_no_link", "text_link"]), "share_pct"].sum()
    )
    if len(stats) >= 2 and {"plain_no_link", "text_link"} <= set(keys):
        bx = 43.2
        ax_left.plot(
            [bx - 1.2, bx, bx, bx - 1.2], [0.0, 0.0, 1.0, 1.0], color=ink, lw=1.2, zorder=4
        )
        ax_left.text(
            bx + 1.1,
            0.5,
            f"{no_vis_pct:.1f}% post\nno visual",
            va="center",
            ha="left",
            fontsize=8.8,
            fontweight="bold",
            color=ink,
            zorder=4,
        )

    ax_left.set_xlim(0, 59.0)
    ax_left.set_xticks([0, 10, 20, 30, 40])
    ax_left.set_xticklabels(["0%", "10%", "20%", "30%", "40%"])
    ax_left.grid(axis="x", linestyle=":", color=grid_col, zorder=0)
    ax_left.set_yticks(y)
    ax_left.set_yticklabels(stats["label"].tolist())
    for tick_lbl, k in zip(ax_left.get_yticklabels(), keys, strict=True):
        tick_lbl.set_fontsize(9.2)
        if k == "paper_figure":
            tick_lbl.set_fontweight("bold")
            tick_lbl.set_color(accent_dark)
        else:
            tick_lbl.set_color(ink)
    ax_left.set_title(
        "(a) Format share in researcher corpus",
        loc="left",
        fontsize=10.5,
        fontweight="bold",
        color=ink,
        pad=10,
    )
    ax_left.set_xlabel("% of posts", fontsize=9.2, color=muted, labelpad=5)

    # Panel (b): Researcher save rate (Bookmarks per 1,000 views)
    ax_right.grid(axis="x", linestyle=":", color=grid_col, zorder=0)
    ax_right.tick_params(axis="y", left=False, labelleft=False)
    ax_right.set_ylim(-0.55, len(stats) - 0.45)

    for yi, row in zip(y, stats.itertuples(), strict=True):
        is_top = row.key == "paper_figure"
        main_col = accent if is_top else "#334155"
        lw = 2.6 if is_top else 1.9
        y_main = yi + 0.11
        ax_right.hlines(
            y_main, row.ci_low, row.ci_high,
            color=main_col, linewidth=lw, capstyle="round", zorder=3,
        )
        ax_right.scatter(
            [row.cr_bmk],
            [y_main],
            s=95 if is_top else 62,
            color=main_col,
            edgecolor=bg,
            linewidth=0.8,
            zorder=4,
        )
        ax_right.text(
            row.cr_bmk,
            y_main + 0.14,
            f"{row.cr_bmk:.2f} [{row.ci_low:.2f}, {row.ci_high:.2f}]",
            va="bottom",
            ha="center",
            fontsize=8.2,
            fontweight="bold" if is_top else "normal",
            color=accent_dark if is_top else ink,
            zorder=5,
        )

        if np.isfinite(row.lt2k_cr_bmk):
            y_small = yi - 0.15
            ax_right.scatter(
                [row.lt2k_cr_bmk],
                [y_small],
                marker="D",
                s=48,
                facecolor=bg,
                edgecolor=small_col,
                linewidth=1.8,
                zorder=5,
            )
            lbl_small = f"{row.lt2k_cr_bmk:.2f}"
            if row.key == "plain_no_link" and "paper_figure" in keys:
                lbl_small += "  (<2k buried)"
            elif row.key == "paper_figure":
                no_link_lt2k = stats.loc[stats["key"] == "plain_no_link", "lt2k_cr_bmk"].iloc[0]
                mult = row.lt2k_cr_bmk / no_link_lt2k if no_link_lt2k > 0 else float("nan")
                if np.isfinite(mult):
                    lbl_small += f"  ({mult:.1f}x unlinked text in <2k)"
            ax_right.text(
                row.lt2k_cr_bmk + 0.20,
                y_small - 0.01,
                lbl_small,
                va="center",
                ha="left",
                fontsize=8.1,
                fontweight="bold" if is_top else "normal",
                color=small_col,
                zorder=5,
            )

    max_ci = float(stats["ci_high"].max()) if len(stats) else 10.0
    ax_right.set_xlim(0, max(11.4, max_ci + 2.0))
    ax_right.set_xticks([0, 2, 4, 6, 8, 10])
    ax_right.set_title(
        "(b) Researcher save rate (bookmarks per 1,000 views)",
        loc="left",
        fontsize=10.5,
        fontweight="bold",
        color=ink,
        pad=10,
    )
    ax_right.set_xlabel("Pooled bookmarks / 1,000 views", fontsize=9.2, color=muted, labelpad=5)

    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="#334155",
            lw=2.0,
            markersize=6.5,
            label=(
                f"All tiers (N={meta['n_posts_all']:,}, {meta['n_authors_all']} authors; "
                "95% author-bootstrapped CI)"
            ),
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            linestyle="None",
            markerfacecolor=bg,
            markeredgecolor=small_col,
            markeredgewidth=1.8,
            markersize=6.0,
            label=f"<2k followers (n={meta['n_posts_lt2k']:,}, {meta['n_authors_lt2k']} authors)",
        ),
    ]
    fig.legend(
        handles=handles,
        ncol=2,
        loc="upper right",
        bbox_to_anchor=(0.968, 0.858),
        frameon=True,
        facecolor=bg,
        edgecolor=grid_col,
        fontsize=8.1,
        handletextpad=0.5,
        columnspacing=1.4,
    )

    by_key = stats.set_index("key")
    sub_txt = f"{no_vis_pct:.0f}% of ML researcher posts include no visual"
    if {"paper_figure", "plain_no_link"} <= set(by_key.index):
        r_all = by_key.loc["paper_figure", "cr_bmk"] / max(
            by_key.loc["plain_no_link", "cr_bmk"], 1e-6
        )
        r_lt2k = by_key.loc["paper_figure", "lt2k_cr_bmk"] / max(
            by_key.loc["plain_no_link", "lt2k_cr_bmk"], 1e-6
        )
        if np.isfinite(r_all) and np.isfinite(r_lt2k):
            sub_txt += (
                f", yet paper figures/tables earn {r_all:.1f}× higher save rates "
                f"than unlinked text ({r_lt2k:.1f}× under 2k followers)."
            )
    fig.suptitle(
        "Visual Assets & Researcher Save Rates on X: Supply vs. Bookmark Conversion",
        x=0.035,
        y=0.955,
        ha="left",
        fontsize=13.2,
        fontweight="bold",
        color=ink,
    )
    fig.text(
        0.035,
        0.892,
        sub_txt,
        ha="left",
        fontsize=9.6,
        color=muted,
    )
    fig.text(
        0.035,
        0.028,
        f"Observational corpus: N = {meta['n_posts_all']:,} mature original, quote, and "
        f"thread-opener posts across {meta['n_authors_all']} ML researcher accounts "
        f"(Aug–Nov 2026, ≤40 posts/author; {meta['omitted_n']} sparse code/map posts omitted "
        "below n ≥ 20 gate).\nPooled CR_bmk = total bookmarks / total impressions × 1,000; "
        "error bars show 95% author-clustered bootstrap CIs (2,000 resamples). "
        "Associational, not causal.",
        ha="left",
        va="bottom",
        fontsize=7.6,
        color=muted,
        linespacing=1.35,
    )

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=240, facecolor=bg)
    if out_pdf is not None:
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_pdf, facecolor=bg)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=SRC)
    ap.add_argument("--png", type=Path, default=OUT_PNG)
    ap.add_argument("--pdf", type=Path, default=OUT_PDF)
    a = ap.parse_args()

    df = pd.read_parquet(a.src)
    stats, meta = compute_ablation_stats(df)
    render_ablation_figure(stats, meta, a.png, a.pdf)
    print(f"wrote {a.png} & {a.pdf} ({meta})")
    print(stats.to_string(index=False))


if __name__ == "__main__":
    main()
