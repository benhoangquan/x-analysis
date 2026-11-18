"""Static HTML overview of the v1 dataset: outputs/reports/overview.html (plotly via CDN)."""

from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.analysis.lift import analysis_corpus, lift_table
from src.analysis.swipe import OUT_CSV as SWIPE_CSV
from src.analysis.swipe import select_swipe_file
from src.config import OWN_HANDLES
from src.metrics.baselines import TIER_LABELS, fit_reach_model

SRC = Path("data/processed/posts_labelled.parquet")
OUT = Path("outputs/reports/overview.html")
PLOTLY = "https://cdn.plot.ly/plotly-2.35.2.min.js"

COHORTS = ["ROSTER", "PANEL", "BENCHMARK", "OWN"]
LOG = {"type": "log", "dtick": 1, "tickformat": "~s"}  # powers of ten only
SYMBOLS = ["circle", "square", "triangle-up", "diamond"]
THEMES = {
    "light": {
        "surface": "#fcfcfb", "text": "#0b0b0b", "muted": "#52514e", "grid": "#e4e3df",
        "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"],
    },
    "dark": {
        "surface": "#1a1a19", "text": "#f0efec", "muted": "#c3c2b7", "grid": "#383835",
        "series": ["#3987e5", "#d95926", "#199e70", "#c98500"],
    },
}  # fmt: skip


def _layout(fig: go.Figure, t: dict, title: str, xt: str, yt: str, **axes: object) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0, "font": {"size": 15, "color": t["text"]}},
        paper_bgcolor=t["surface"], plot_bgcolor=t["surface"],
        font={"color": t["muted"], "family": "system-ui, sans-serif", "size": 12},
        margin={"l": 70, "r": 20, "t": 50, "b": 95}, height=400,
        legend={"orientation": "h", "y": -0.34, "font": {"color": t["text"]}},
        hoverlabel={"bgcolor": t["surface"], "font": {"color": t["text"]}},
    )  # fmt: skip
    ax = {"gridcolor": t["grid"], "zeroline": False, "linecolor": t["grid"]}
    fig.update_xaxes(title=xt, **ax, **axes.get("x", {}))  # type: ignore[arg-type]
    fig.update_yaxes(title=yt, **ax, **axes.get("y", {}))  # type: ignore[arg-type]
    return fig


def _hover(d: pd.DataFrame) -> list[str]:
    raw_txt = d["text"] if "text" in d.columns else pd.Series("", index=d.index)
    snip = raw_txt.fillna("").str.replace(r"\s+", " ", regex=True).str[:80].map(html.escape)
    shrunk = (
        d["cr_bmk_shrunk"]
        if "cr_bmk_shrunk" in d.columns
        else d["cr_bmk"]
    )
    return [
        f"{c} · {tier}<br>{s}<br>views {v:,.0f} · CR_bmk_shrunk {cs:.2f}"
        for c, tier, s, v, cs in zip(
            d["cohort"], d["follower_tier"], snip, d["impressions"], shrunk, strict=True
        )
    ]


def _heatmap_figure(d: pd.DataFrame, t: dict) -> go.Figure:
    corpus = analysis_corpus(d)
    f = go.Figure()
    if corpus.empty or "hook_archetype" not in corpus or "visual_type" not in corpus:
        return _layout(f, t, "Archetype × Visual pooled CR_bmk (no corpus rows)", "", "")
    tbl = lift_table(corpus, ["hook_archetype", "visual_type"], n_boot=200)
    hooks = sorted(tbl["hook_archetype"].dropna().astype(str).unique())
    vis = sorted(tbl["visual_type"].dropna().astype(str).unique())
    z = np.full((len(hooks), len(vis)), np.nan)
    txt = [["" for _ in vis] for _ in hooks]
    lookup = tbl.set_index(["hook_archetype", "visual_type"])
    for i, h in enumerate(hooks):
        for j, v in enumerate(vis):
            if (h, v) not in lookup.index:
                txt[i][j] = "n=0"
                continue
            r = lookup.loc[(h, v)]
            if r["passes_gate"]:
                z[i, j] = float(r["cr_bmk"])
                txt[i][j] = (
                    f"{r['cr_bmk']:.2f} bmk/1k ({r['lift_vs_tier']:.2f}x, "
                    f"n={int(r['n_posts'])}, au={int(r['n_authors'])})"
                )
            else:
                txt[i][j] = f"insufficient data (n={int(r['n_posts'])}, au={int(r['n_authors'])})"
    f.add_trace(
        go.Heatmap(
            z=z, x=vis, y=hooks, text=txt, hoverinfo="text", colorscale="Blues",
            colorbar={"title": "CR_bmk"},
        )
    )
    return _layout(f, t, "Archetype × Visual pooled CR_bmk (cells passing gate)",
                   "Visual type", "Hook archetype")  # fmt: skip


def figures(d: pd.DataFrame, mode: str) -> list[go.Figure]:
    t = THEMES[mode]
    color = dict(zip(COHORTS, t["series"], strict=True))
    sym = dict(zip(COHORTS, SYMBOLS, strict=True))
    out = []

    # 1. Views vs followers with ROSTER expected-reach fit
    f1 = go.Figure()
    pos = d[d["impressions"] > 0]
    for c in COHORTS:
        g = pos[pos["cohort"] == c]
        if g.empty:
            continue
        f1.add_trace(go.Scatter(
            x=g["followers_at_collection"].clip(lower=10), y=g["impressions"], mode="markers",
            name=c, opacity=0.45 if c in ("ROSTER", "PANEL") else 0.9,
            marker={"color": color[c], "symbol": sym[c], "size": 9 if c == "OWN" else 7,
                    "line": {"color": t["surface"], "width": 1}},
            hovertext=_hover(g), hoverinfo="text",
        ))  # fmt: skip
    m = fit_reach_model(d)
    if not np.isnan(m.slope):
        xs = np.geomspace(50, 6e6, 40)
        lbl = "ROSTER expected reach" if m.reliable else "expected reach (below gate)"
        f1.add_trace(go.Scatter(
            x=xs, y=np.exp(m.intercept + m.slope * np.log(np.maximum(xs, 100))), mode="lines",
            name=lbl, hoverinfo="skip", line={"color": t["text"], "width": 2, "dash": "dot"},
        ))
    out.append(_layout(f1, t, "Views vs followers across cohorts", "Followers (log)",
                       "Views (log)", x=LOG, y=LOG))  # fmt: skip

    # 2. Shrunk bookmark rate by follower tier + OWN markers
    f2 = go.Figure()
    rate_col = "cr_bmk_shrunk" if "cr_bmk_shrunk" in d else "cr_bmk"
    ros = d[(d["cohort"] == "ROSTER") & d[rate_col].notna()]
    for tier in TIER_LABELS:
        g = ros[ros["follower_tier"] == tier]
        if g.empty:
            continue
        f2.add_trace(go.Box(
            x=[tier] * len(g), y=g[rate_col], name=tier, boxpoints="outliers",
            marker={"color": color["ROSTER"]}, showlegend=False,
        ))
    own = d[(d["cohort"] == "OWN") & d[rate_col].notna()]
    if not own.empty:
        f2.add_trace(go.Scatter(
            x=own["follower_tier"], y=own[rate_col], mode="markers",
            name="OWN (@tiptree / @martin)",
            marker={"color": color["OWN"], "symbol": "diamond", "size": 11,
                    "line": {"color": t["surface"], "width": 1.5}},
            hovertext=_hover(own), hoverinfo="text",
        ))  # fmt: skip
    out.append(_layout(f2, t, "Shrunk bookmark rate by follower tier (ROSTER + OWN)",
                       "Follower tier", "CR_bmk_shrunk (bookmarks / 1k views)"))  # fmt: skip

    # 3. Archetype x visual pooled CR_bmk heatmap
    out.append(_heatmap_figure(d, t))

    # 4. Tiptree own accounts: Views vs CR_bmk_shrunk
    f4 = go.Figure()
    if not own.empty:
        for h in OWN_HANDLES:
            g = own[own["author_handle"].str.lower() == h]
            if g.empty:
                continue
            f4.add_trace(go.Scatter(
                x=g["impressions"].clip(lower=1), y=g[rate_col], mode="markers", name=f"@{h}",
                marker={"size": 11, "line": {"color": t["surface"], "width": 1.5}},
                hovertext=_hover(g), hoverinfo="text",
            ))
        out.append(_layout(f4, t, "Tiptree own accounts: views vs shrunk bookmark rate",
                           "Views (log)", "CR_bmk_shrunk", x=LOG))
    else:
        f4.add_annotation(text="No mature eligible OWN posts in this snapshot",
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        out.append(_layout(f4, t, "Tiptree own accounts", "Views", "CR_bmk_shrunk"))
    return out


def swipe_table(d: pd.DataFrame) -> str:
    swipe = pd.read_csv(SWIPE_CSV) if SWIPE_CSV.exists() else select_swipe_file(d)
    if swipe.empty:
        return "<p>No posts cleared the swipe-file bar yet.</p>"
    cols = [
        c for c in (
            "follower_tier", "hook_archetype", "visual_type", "technical_rigor_score",
            "impressions", "cr_bmk_shrunk", "baseline_ratio", "text", "url",
        )
        if c in swipe.columns
    ]
    rows = []
    for r in swipe.head(40).itertuples(index=False):
        cells = []
        for c in cols:
            v = getattr(r, c)
            if c == "text":
                cells.append(f"<td>{html.escape(' '.join(str(v).split())[:90])}</td>")
            elif c == "url":
                u = html.escape(str(v))
                cells.append(f'<td><a href="{u}" target="_blank">post</a></td>')
            elif isinstance(v, float):
                cells.append(f"<td>{v:.2f}</td>")
            else:
                cells.append(f"<td>{html.escape(str(v))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    head = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def scorecard_html(d: pd.DataFrame) -> str:
    small = d[d["follower_tier"] == "<2k"]
    rate_col = "cr_bmk_shrunk" if "cr_bmk_shrunk" in d else "cr_bmk"
    own = d[d["author_handle"].str.lower().isin(OWN_HANDLES)]
    if small.empty or own.empty:
        return "<p>Tiptree scorecard unavailable (missing &lt;2k or OWN mature posts).</p>"
    dist = small[rate_col].dropna()
    rows = []
    for h in OWN_HANDLES:
        g = own[own["author_handle"].str.lower() == h]
        if g.empty:
            continue
        med = float(g[rate_col].median())
        pct = float((dist <= med).mean() * 100) if len(dist) else float("nan")
        rows.append(
            f"<tr><td>@{h}</td><td>{len(g)}</td><td>{g['impressions'].median():,.0f}</td>"
            f"<td>{g['cr_bmk'].median():.2f}</td><td>{med:.2f}</td><td>{pct:.0f}%</td></tr>"
        )
    return (
        "<table><thead><tr><th>account</th><th>mature_posts</th><th>median_views</th>"
        "<th>median_cr_bmk</th><th>median_cr_bmk_shrunk</th><th>pctile_in_under_2k</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def page(d: pd.DataFrame) -> str:
    payload = {mode: [json.loads(f.to_json()) for f in figures(d, mode)] for mode in THEMES}
    n, a = len(d), d["author_handle"].nunique()
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tiptree X post overview</title>
<script src="{PLOTLY}"></script>
<style>
:root {{ --bg:#fcfcfb; --fg:#0b0b0b; --muted:#52514e; --line:#e4e3df; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#1a1a19; --fg:#f0efec; --muted:#c3c2b7; --line:#383835; }}
}}
body {{ background:var(--bg); color:var(--fg); font:15px/1.5 system-ui,sans-serif;
  margin:0 auto; max-width:980px; padding:24px 16px; }}
h1 {{ font-size:22px; margin:0 0 4px; }} h2 {{ font-size:17px; margin:24px 0 8px; }}
p.note {{ color:var(--muted); margin:0 0 20px; }}
.chart {{ margin:0 0 24px; }} table {{ border-collapse:collapse; width:100%; font-size:13px; }}
th,td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); }}
th {{ color:var(--muted); font-weight:600; }} .scroll {{ overflow-x:auto; }}
</style></head><body>
<h1>Tiptree X post overview</h1>
<p class="note">{n} eligible mature posts across {a} authors. Jev rubric v2 labels used under
Decision 60; lift cells show "insufficient data" below 20 posts / 10 authors.</p>
<div id="c0" class="chart"></div><div id="c1" class="chart"></div>
<div id="c2" class="chart"></div><div id="c3" class="chart"></div>
<h2>Tiptree scorecard (&lt;2k distribution)</h2><div class="scroll">{scorecard_html(d)}</div>
<h2>Swipe file (top posts)</h2><div class="scroll">{swipe_table(d)}</div>
<script>
const FIGS = {json.dumps(payload)};
const mq = matchMedia("(prefers-color-scheme: dark)");
function draw() {{
  const set = FIGS[mq.matches ? "dark" : "light"];
  set.forEach((f, i) => Plotly.react("c" + i, f.data, f.layout, {{responsive: true,
    displayModeBar: false}}));
}}
draw(); mq.addEventListener("change", draw);
</script></body></html>"""


def main() -> None:
    d = pd.read_parquet(SRC)
    d = d[d["eligible"].astype(bool) & d["mature"].astype(bool) & d["impressions"].notna()]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page(d))
    print(f"{len(d)} posts -> {OUT}")


if __name__ == "__main__":
    main()
