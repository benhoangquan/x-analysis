"""Static HTML overview of the labelled dataset: outputs/reports/overview.html (plotly via CDN).

Categorical colours are fixed per author (never re-ranked) and validated with the dataviz
skill's validate_palette script; marker shapes add a second encoding for colour-blind readers.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.metrics.baselines import fit_reach_model

SRC = Path("data/processed/posts_labelled.parquet")
OUT = Path("outputs/reports/overview.html")
PLOTLY = "https://cdn.plot.ly/plotly-2.35.2.min.js"

AUTHORS = ["tiptreesystems", "weights_biases", "karpathy", "elicitorg"]  # fixed order = colour slot
LOG = {"type": "log", "dtick": 1, "tickformat": "~s"}  # powers of ten only
SYMBOLS = ["circle", "square", "diamond", "triangle-up"]
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
    snip = d["text"].str.replace(r"\s+", " ", regex=True).str[:90].map(html.escape)
    return [
        f"<b>@{a}</b><br>{s}<br>views {v:,.0f} · S_intent {si:.4f} · bmk/1k {c:.2f}"
        for a, s, v, si, c in zip(
            d["author_handle"], snip, d["impressions"], d["s_intent"], d["cr_bmk"], strict=True
        )
    ]


def figures(d: pd.DataFrame, mode: str) -> list[go.Figure]:
    t = THEMES[mode]
    color = dict(zip(AUTHORS, t["series"], strict=True))
    sym = dict(zip(AUTHORS, SYMBOLS, strict=True))
    out = []

    # 1. views vs followers with the (unreliable) expected-reach fit
    f1 = go.Figure()
    for a in AUTHORS:
        g = d[d["author_handle"] == a]
        f1.add_trace(go.Scatter(
            x=g["followers_at_collection"], y=g["impressions"], mode="markers", name=f"@{a}",
            marker={"color": color[a], "symbol": sym[a], "size": 11,
                    "line": {"color": t["surface"], "width": 2}},
            hovertext=_hover(g), hoverinfo="text",
        ))  # fmt: skip
    m = fit_reach_model(d.assign(eligible=True, mature=True))
    xs = np.geomspace(50, 6e6, 40)
    f1.add_trace(go.Scatter(
        x=xs, y=np.exp(m.intercept + m.slope * np.log(np.maximum(xs, 100))), mode="lines",
        name="fitted expected reach (not reliable)", hoverinfo="skip",
        line={"color": t["muted"], "width": 2, "dash": "dot"},
    ))  # fmt: skip
    out.append(_layout(f1, t, "Views grow slower than followers", "Followers (log)",
                       "Views (log)", x=LOG, y=LOG))  # fmt: skip

    # 1b. likes vs views
    fl = go.Figure()
    for a in AUTHORS:
        g = d[d["author_handle"] == a]
        fl.add_trace(go.Scatter(
            x=g["impressions"], y=g["likes"], mode="markers", name=f"@{a}",
            marker={"color": color[a], "symbol": sym[a], "size": 11,
                    "line": {"color": t["surface"], "width": 2}},
            hovertext=_hover(g), hoverinfo="text",
        ))  # fmt: skip
    out.append(_layout(fl, t, "Likes against views (each marker is one post)", "Views (log)",
                       "Likes (log)", x=LOG, y=LOG))  # fmt: skip

    # 2. intent per post, by author
    f2 = go.Figure()
    for a in AUTHORS:
        g = d[d["author_handle"] == a]
        f2.add_trace(go.Scatter(
            x=g["s_intent"], y=[f"@{a}"] * len(g), mode="markers", name=f"@{a}",
            marker={"color": color[a], "symbol": sym[a], "size": 11,
                    "line": {"color": t["surface"], "width": 2}},
            hovertext=_hover(g), hoverinfo="text", showlegend=False,
        ))  # fmt: skip
        f2.add_vline(x=g["s_intent"].median(), line_width=0)  # keep axis stable
    out.append(_layout(f2, t, "High-intent score per post (each marker is one post)",
                       "S_intent", "", y={"autorange": "reversed"}))  # fmt: skip

    # 3. Tiptree: reach is not intent
    own = d[d["author_handle"] == "tiptreesystems"]
    f3 = go.Figure(go.Scatter(
        x=own["impressions"], y=own["s_intent"], mode="markers",
        marker={"color": color["tiptreesystems"], "size": 12,
                "line": {"color": t["surface"], "width": 2}},
        hovertext=_hover(own), hoverinfo="text", showlegend=False,
    ))  # fmt: skip
    top = own.loc[own["impressions"].idxmax()]
    f3.add_annotation(x=np.log10(top["impressions"]), y=top["s_intent"], xref="x", yref="y",
                      text="most views, lowest intent", showarrow=True, ax=-60, ay=-40,
                      font={"color": t["text"]})  # fmt: skip
    out.append(_layout(f3, t, "@tiptreesystems: more views did not mean more intent",
                       "Views (log)", "S_intent", x=LOG))  # fmt: skip
    return out


def table(d: pd.DataFrame) -> str:
    cols = ["author_handle", "text", "impressions", "s_intent", "cr_bmk", "visual_type",
            "technical_rigor_score"]  # fmt: skip
    rows = []
    for r in d.sort_values("s_intent", ascending=False)[cols].itertuples(index=False):
        txt = html.escape(" ".join(str(r.text).split())[:90])
        rows.append(
            f"<tr><td>@{r.author_handle}</td><td>{txt}</td><td>{r.impressions:,.0f}</td>"
            f"<td>{r.s_intent:.4f}</td><td>{r.cr_bmk:.2f}</td><td>{r.visual_type}</td>"
            f"<td>{r.technical_rigor_score:.0f}</td></tr>"
        )
    head = "".join(f"<th>{c}</th>" for c in cols)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


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
  margin:0 auto; max-width:900px; padding:24px 16px; }}
h1 {{ font-size:22px; margin:0 0 4px; }} p.note {{ color:var(--muted); margin:0 0 20px; }}
.chart {{ margin:0 0 24px; }} table {{ border-collapse:collapse; width:100%; font-size:13px; }}
th,td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); }}
th {{ color:var(--muted); font-weight:600; }} .scroll {{ overflow-x:auto; }}
</style></head><body>
<h1>Tiptree X post overview</h1>
<p class="note">{n} eligible posts at least 7 days old, from {a} authors. Descriptive only: this is
far below the plan's gate of 20 posts from 10 authors, so none of this is a lift estimate.</p>
<div id="c0" class="chart"></div><div id="c1" class="chart"></div>
<div id="c2" class="chart"></div><div id="c3" class="chart"></div>
<h2 style="font-size:16px">All posts</h2><div class="scroll">{table(d)}</div>
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
    d = d[d["eligible"] & d["mature"] & d["s_intent"].notna()]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page(d))
    print(f"{len(d)} posts -> {OUT}")


if __name__ == "__main__":
    main()
