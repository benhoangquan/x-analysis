"""Exploratory 2D UMAP + t-SNE multimodal post embedding map (After V0 / Decision D9).

Embeds post text (`BAAI/bge-small-en-v1.5`) plus cached post photos (`Qdrant/clip-ViT-B-32-*`
blended with text) when available, reduces to 50D PCA, projects with UMAP and t-SNE,
computes k-NN label purity and OWN neighborhood diagnostics, and writes an interactive HTML
view (`outputs/reports/embedding_map.html`). Exploratory hypothesis generator only (D9).
"""

from __future__ import annotations

import argparse
import html
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import umap
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.neighbors import NearestNeighbors

from src.config import OWN_HANDLES

SRC = Path("data/processed/posts_labelled.parquet")
MEDIA_DIR = Path("data/raw/media")
CACHE = Path("data/processed/post_embeddings.parquet")
STATS_OUT = Path("data/processed/embedding_stats.json")
OUT = Path("outputs/reports/embedding_map.html")
OUT_IMP = Path("outputs/reports/embedding_impression_map.html")
PLOTLY = "https://cdn.plot.ly/plotly-2.35.2.min.js"

TEXT_MODEL = "BAAI/bge-small-en-v1.5"
CLIP_TEXT_MODEL = "Qdrant/clip-ViT-B-32-text"
CLIP_IMG_MODEL = "Qdrant/clip-ViT-B-32-vision"
SEED = 20261112
PCA_DIMS = 50
KNN_K = 15

COLOR_FIELDS: tuple[tuple[str, str], ...] = (
    ("hook_archetype", "Hook archetype"),
    ("framing", "Framing"),
    ("poster_role", "Poster role"),
    ("follower_tier", "Follower tier"),
    ("cr_bmk_shrunk", "Bookmark rate (cr_bmk_shrunk)"),
    ("visual_type", "Visual type"),
)

EmbedFn = Callable[[list[str], list[Path | None]], tuple[np.ndarray, np.ndarray]]


def _l2_norm(arr: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    return arr / np.maximum(norms, 1e-12)


def load_eligible(src: Path = SRC) -> pd.DataFrame:
    df = pd.read_parquet(src)
    mask = df["eligible"].astype(bool) & df["mature"].astype(bool) & df["impressions"].notna()
    return df[mask].sort_values("post_id").reset_index(drop=True)


def default_embed_posts(
    texts: list[str], image_paths: list[Path | None]
) -> tuple[np.ndarray, np.ndarray]:
    """Compute fused L2-normalized BGE-small text + CLIP text/image vectors."""
    from fastembed import ImageEmbedding, TextEmbedding
    from PIL import Image

    txt_emb = TextEmbedding(model_name=TEXT_MODEL)
    e_txt = _l2_norm(np.asarray(list(txt_emb.embed(texts, batch_size=128)), dtype="float32"))

    clip_txt_emb = TextEmbedding(model_name=CLIP_TEXT_MODEL)
    c_txt = _l2_norm(np.asarray(list(clip_txt_emb.embed(texts, batch_size=128)), dtype="float32"))
    c_mm = c_txt.copy()

    valid_idx: list[int] = []
    pil_imgs: list[Any] = []
    for idx, p in enumerate(image_paths):
        if p is None or not p.exists():
            continue
        try:
            with Image.open(p) as im:
                pil_imgs.append(im.convert("RGB"))
            valid_idx.append(idx)
        except Exception:  # noqa: BLE001
            continue

    has_img = np.zeros(len(texts), dtype=bool)
    if pil_imgs:
        clip_img_emb = ImageEmbedding(model_name=CLIP_IMG_MODEL)
        img_vecs = _l2_norm(
            np.asarray(list(clip_img_emb.embed(pil_imgs, batch_size=64)), dtype="float32")
        )
        c_mm[valid_idx] = _l2_norm(0.5 * c_txt[valid_idx] + 0.5 * img_vecs)
        has_img[valid_idx] = True

    fused = np.hstack([np.sqrt(0.65) * e_txt, np.sqrt(0.35) * c_mm]).astype("float32")
    return fused, has_img


def embed_posts(
    df: pd.DataFrame,
    *,
    media_dir: Path = MEDIA_DIR,
    embed_fn: EmbedFn | None = None,
    seed: int = SEED,
) -> tuple[np.ndarray, np.ndarray]:
    """Return 50D PCA vectors and boolean mask of posts whose cached photo was embedded."""
    texts = df["text"].fillna("").astype(str).tolist()
    kinds = df["media_kind"] if "media_kind" in df.columns else pd.Series(None, index=df.index)
    img_paths: list[Path | None] = []
    for pid, kind in zip(df["post_id"].astype(str), kinds, strict=True):
        if kind == "photo":
            candidate = media_dir / f"{pid}.img"
            img_paths.append(candidate if candidate.exists() else None)
        else:
            img_paths.append(None)

    raw, has_img = (embed_fn or default_embed_posts)(texts, img_paths)
    n, d = raw.shape
    n_comp = min(PCA_DIMS, max(1, n - 1), d)
    if n < 2 or d == 0:
        return np.zeros((n, 2), dtype="float32"), has_img
    pca_vecs = PCA(n_components=n_comp, random_state=seed).fit_transform(raw)
    return np.asarray(pca_vecs, dtype="float32"), has_img


def project_2d(
    pca_vecs: np.ndarray, *, seed: int = SEED
) -> tuple[np.ndarray, np.ndarray]:
    """Compute UMAP and t-SNE 2D coordinates from PCA vectors."""
    n = len(pca_vecs)
    if n <= 3:
        pad = np.zeros((n, 2), dtype="float32")
        return pad, pad.copy()

    n_neighbors = min(25, max(2, n - 1))
    umap_xy = umap.UMAP(
        n_neighbors=n_neighbors,
        min_dist=0.12,
        metric="cosine",
        random_state=seed,
        n_jobs=1,
        compatibility_layout=False,
    ).fit_transform(pca_vecs)

    perp = min(35.0, max(2.0, (n - 1) / 3.0))
    init_mode = "pca" if pca_vecs.shape[1] >= 2 else "random"
    tsne_xy = TSNE(
        n_components=2,
        perplexity=perp,
        init=init_mode,
        learning_rate="auto",
        random_state=seed,
    ).fit_transform(pca_vecs)

    return np.asarray(umap_xy, dtype="float32"), np.asarray(tsne_xy, dtype="float32")


def project_1d(
    pca_vecs: np.ndarray, *, seed: int = SEED
) -> tuple[np.ndarray, np.ndarray]:
    """Compute 1D UMAP and 1D t-SNE coordinates from PCA vectors."""
    n = len(pca_vecs)
    if n <= 3:
        zeros = np.zeros(n, dtype="float32")
        return zeros, zeros.copy()

    n_neighbors = min(25, max(2, n - 1))
    u1 = umap.UMAP(
        n_components=1,
        n_neighbors=n_neighbors,
        min_dist=0.12,
        metric="cosine",
        random_state=seed,
        n_jobs=1,
        compatibility_layout=False,
    ).fit_transform(pca_vecs).ravel()

    perp = min(35.0, max(2.0, (n - 1) / 3.0))
    init_mode = "pca" if pca_vecs.shape[1] >= 1 else "random"
    t1 = TSNE(
        n_components=1,
        perplexity=perp,
        init=init_mode,
        learning_rate="auto",
        random_state=seed,
    ).fit_transform(pca_vecs).ravel()

    return np.asarray(u1, dtype="float32"), np.asarray(t1, dtype="float32")


def _knn_purity(coords: np.ndarray, labels: np.ndarray, metric: str, k: int) -> tuple[float, float]:
    n = len(coords)
    k_eff = min(k, n - 1)
    if k_eff < 1:
        return float("nan"), float("nan")
    nn = NearestNeighbors(n_neighbors=k_eff + 1, metric=metric).fit(coords)
    idx = nn.kneighbors(coords, return_distance=False)[:, 1:]
    purity = float(np.mean(labels[idx] == labels[:, None]))
    _, counts = np.unique(labels, return_counts=True)
    probs = counts / counts.sum()
    chance = float(np.sum(probs**2))
    return purity, chance


def compute_region_stats(
    df: pd.DataFrame,
    pca_vecs: np.ndarray,
    umap_xy: np.ndarray,
    tsne_xy: np.ndarray,
    *,
    umap_1d: np.ndarray | None = None,
    tsne_1d: np.ndarray | None = None,
    k: int = KNN_K,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Measure k-NN label agreement across 50D/2D/1D maps and summarize OWN neighborhoods."""
    res_mask = (df["is_researcher_post"] == True).to_numpy()  # noqa: E712
    cols = ["hook_archetype", "visual_type", "framing", "poster_role", "follower_tier"]
    purity_rows: list[dict[str, Any]] = []

    for col in cols:
        if col not in df.columns:
            continue
        sub_mask = res_mask & df[col].notna().to_numpy() & (df[col].astype(str) != "").to_numpy()
        n_sub = int(sub_mask.sum())
        if n_sub < 5:
            continue
        labs = df.loc[sub_mask, col].astype(str).to_numpy()
        p_pca, chance = _knn_purity(pca_vecs[sub_mask], labs, "cosine", k)
        p_umap, _ = _knn_purity(umap_xy[sub_mask], labs, "euclidean", k)
        p_tsne, _ = _knn_purity(tsne_xy[sub_mask], labs, "euclidean", k)
        row = dict(
            field=col,
            n_posts=n_sub,
            n_classes=int(len(np.unique(labs))),
            chance_baseline=round(chance, 4),
            pca_50d_purity=round(p_pca, 4),
            umap_2d_purity=round(p_umap, 4),
            tsne_2d_purity=round(p_tsne, 4),
        )
        if umap_1d is not None:
            row["umap_1d_purity"] = round(
                _knn_purity(umap_1d[sub_mask, None], labs, "euclidean", k)[0], 4
            )
        if tsne_1d is not None:
            row["tsne_1d_purity"] = round(
                _knn_purity(tsne_1d[sub_mask, None], labs, "euclidean", k)[0], 4
            )
        purity_rows.append(row)

    own_rows: list[dict[str, Any]] = []
    pool_mask = res_mask & (df["cohort"].astype(str) != "OWN").to_numpy()
    if pool_mask.sum() >= 3 and len(pca_vecs):
        k_own = min(k, int(pool_mask.sum()))
        pool_df = df.loc[pool_mask].reset_index(drop=True)
        nn_pool = NearestNeighbors(n_neighbors=k_own, metric="cosine").fit(pca_vecs[pool_mask])
        for h in OWN_HANDLES:
            own_mask = (df["author_handle"].str.lower() == h).to_numpy()
            if not own_mask.any():
                continue
            nbr_idx = nn_pool.kneighbors(pca_vecs[own_mask], return_distance=False).ravel()
            nbrs = pool_df.iloc[nbr_idx]
            rate_col = "cr_bmk_shrunk" if "cr_bmk_shrunk" in nbrs else "cr_bmk"
            mean_cr = float(nbrs[rate_col].mean())
            top_hook = (
                str(nbrs["hook_archetype"].mode().iloc[0])
                if "hook_archetype" in nbrs and nbrs["hook_archetype"].notna().any()
                else "-"
            )
            top_vis = (
                str(nbrs["visual_type"].mode().iloc[0])
                if "visual_type" in nbrs and nbrs["visual_type"].notna().any()
                else "-"
            )
            own_rows.append(
                dict(
                    account=f"@{h}",
                    own_posts=int(own_mask.sum()),
                    mean_own_cr_shrunk=round(float(df.loc[own_mask, rate_col].mean()), 2),
                    knn_mean_cr_shrunk=round(mean_cr, 2),
                    nearest_hook_mode=top_hook,
                    nearest_visual_mode=top_vis,
                )
            )

    return pd.DataFrame(purity_rows), pd.DataFrame(own_rows)


def _str_col(df: pd.DataFrame, col: str, default: str = "missing") -> list[str]:
    if col not in df.columns:
        return [default] * len(df)
    return [default if pd.isna(v) or str(v).strip() == "" else str(v) for v in df[col]]


def compute_bin_skyline(
    df: pd.DataFrame, umap_1d: np.ndarray, *, n_bins: int = 8
) -> pd.DataFrame:
    """Summarize researcher post composition and reach across quantile bins along 1D UMAP."""
    res = df[df["is_researcher_post"] == True].copy()  # noqa: E712
    if res.empty:
        return pd.DataFrame()
    res["_u1"] = umap_1d[(df["is_researcher_post"] == True).to_numpy()]  # noqa: E712
    q_n = min(n_bins, max(1, int(res["_u1"].nunique())))
    if q_n == 1:
        res["_bin"] = 0
    else:
        res["_bin"] = pd.qcut(res["_u1"], q=q_n, labels=False, duplicates="drop")
    rows = []
    for b, g in res.groupby("_bin", sort=True):
        imp_sum = float(g["impressions"].sum())
        bmk_sum = float(g["bookmarks"].fillna(0).sum()) if "bookmarks" in g else 0.0
        base_med = (
            round(float(g["baseline_ratio"].median()), 2)
            if "baseline_ratio" in g and g["baseline_ratio"].notna().any()
            else float("nan")
        )
        rows.append(
            dict(
                bin=f"B{int(b) + 1}",
                umap_1d_range=f"[{g['_u1'].min():.2f}, {g['_u1'].max():.2f}]",
                n_posts=len(g),
                n_authors=int(g["author_handle"].nunique()),
                top_hook=str(g["hook_archetype"].mode().iloc[0])
                if "hook_archetype" in g and g["hook_archetype"].notna().any()
                else "-",
                top_visual=str(g["visual_type"].mode().iloc[0])
                if "visual_type" in g and g["visual_type"].notna().any()
                else "-",
                median_views=int(round(float(g["impressions"].median()))),
                median_baseline=base_med,
                pooled_cr_bmk=round(bmk_sum / max(imp_sum, 1.0) * 1000.0, 2),
            )
        )
    return pd.DataFrame(rows)


def _pos_float_col(df: pd.DataFrame, col: str) -> list[float | None]:
    if col not in df.columns:
        return [None] * len(df)
    return [
        round(float(v), 3) if pd.notna(v) and float(v) > 0 else None
        for v in df[col]
    ]


def build_payload(
    df: pd.DataFrame,
    umap_xy: np.ndarray,
    tsne_xy: np.ndarray,
    has_img: np.ndarray,
    *,
    umap_1d: np.ndarray | None = None,
    tsne_1d: np.ndarray | None = None,
) -> dict[str, Any]:
    """Build compact columnar JSON payload consumed by the interactive HTML maps."""
    rate_col = "cr_bmk_shrunk" if "cr_bmk_shrunk" in df.columns else "cr_bmk"
    raw_txt = df["text"] if "text" in df.columns else pd.Series("", index=df.index)
    snips = [
        html.escape(" ".join(str(t).split())[:90])
        for t in raw_txt.fillna("")
    ]
    urls = [
        str(u) if pd.notna(u) and str(u).strip() else f"https://x.com/i/web/status/{pid}"
        for pid, u in zip(
            df["post_id"].astype(str),
            df["url"] if "url" in df.columns else pd.Series("", index=df.index),
            strict=True,
        )
    ]
    own_mask = df["cohort"].astype(str) == "OWN"
    own_handles = [
        f"@{h.lower()}" if is_own else ""
        for h, is_own in zip(df["author_handle"].astype(str), own_mask, strict=True)
    ]
    in_cap = (
        df["in_author_cap"].fillna(False).astype(bool).tolist()
        if "in_author_cap" in df.columns
        else [True] * len(df)
    )
    bmk = (
        df["bookmarks"].fillna(0).astype(int).tolist()
        if "bookmarks" in df.columns
        else [0] * len(df)
    )
    u1_vals = umap_1d if umap_1d is not None else umap_xy[:, 0]
    t1_vals = tsne_1d if tsne_1d is not None else tsne_xy[:, 0]
    return {
        "x_u": [round(float(v), 3) for v in umap_xy[:, 0]],
        "y_u": [round(float(v), 3) for v in umap_xy[:, 1]],
        "x_t": [round(float(v), 3) for v in tsne_xy[:, 0]],
        "y_t": [round(float(v), 3) for v in tsne_xy[:, 1]],
        "u1": [round(float(v), 3) for v in u1_vals],
        "t1": [round(float(v), 3) for v in t1_vals],
        "base": _pos_float_col(df, "baseline_ratio"),
        "rve": _pos_float_col(df, "reach_vs_expected"),
        "cohort": _str_col(df, "cohort", "ROSTER"),
        "own": own_handles,
        "is_res": (df["is_researcher_post"] == True).tolist(),  # noqa: E712
        "in_cap": in_cap,
        "hook": _str_col(df, "hook_archetype", "OTHER"),
        "framing": _str_col(df, "framing", "DECLARATIVE_OTHER"),
        "role": _str_col(df, "poster_role", "none"),
        "tier": _str_col(df, "follower_tier", "missing"),
        "vis": _str_col(df, "visual_type", "NONE"),
        "cr": [round(float(v), 2) if pd.notna(v) else 0.0 for v in df[rate_col]],
        "views": [int(v) if pd.notna(v) else 0 for v in df["impressions"]],
        "bmk": bmk,
        "img": [bool(v) for v in has_img],
        "snip": snips,
        "url": urls,
    }


def _html_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "<p>No rows available.</p>"
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{html.escape(str(v))}</td>" for v in row)
        + "</tr>"
        for row in df.itertuples(index=False)
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


_PAGE_CSS = """
:root { --bg:#fcfcfb; --fg:#0b0b0b; --muted:#52514e; --line:#e4e3df; --panel:#f3f2ee; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#1a1a19; --fg:#f0efec; --muted:#c3c2b7; --line:#383835; --panel:#242422; }
}
body { background:var(--bg); color:var(--fg); font:14px/1.5 system-ui,sans-serif;
  margin:0 auto; max-width:1280px; padding:22px 16px; }
h1 { font-size:21px; margin:0 0 4px; } h2 { font-size:16px; margin:22px 0 8px; }
p.note { color:var(--muted); margin:0 0 14px; }
.warn { background:var(--panel); border-left:3px solid #eb6834; padding:8px 12px;
  margin:0 0 14px; font-size:13px; }
.controls { display:flex; flex-wrap:wrap; gap:12px 18px; align-items:center;
  padding:10px 12px; background:var(--panel); border-radius:6px; margin:0 0 14px; }
.controls label { display:flex; align-items:center; gap:6px; font-size:13px; }
select { background:var(--bg); color:var(--fg); border:1px solid var(--line);
  border-radius:4px; padding:4px 8px; font:inherit; }
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(460px, 1fr));
  gap:16px; margin:0 0 20px; }
.plot { min-height:540px; border:1px solid var(--line); border-radius:6px; }
table { border-collapse:collapse; width:100%; font-size:13px; margin:0 0 18px; }
th,td { text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); }
th { color:var(--muted); font-weight:600; } .scroll { overflow-x:auto; }
a { color:inherit; }
"""

_JS_SHARED = """
const FIELD_KEY = {
  hook_archetype: "hook", framing: "framing", poster_role: "role",
  follower_tier: "tier", cr_bmk_shrunk: "cr", visual_type: "vis"
};
const PAL = [
  "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8b5cf6", "#ec4899", "#0ea5e9", "#84cc16"
];
const MUTED_CATS = new Set(["OTHER", "NONE", "none", "missing", "DECLARATIVE_OTHER"]);
const TIER_ORDER = ["<2k", "2k-20k", "20k-200k", ">200k", "missing"];
const mq = matchMedia("(prefers-color-scheme: dark)");

function hoverText(i) {
  const ownTag = D.own[i] ? ` [OWN ${D.own[i]}]` : "";
  const imgTag = D.img[i] ? " +img" : "";
  const baseTag = D.base[i] != null ? ` &middot; base ${D.base[i].toFixed(2)}x` : "";
  return `${D.cohort[i]}${ownTag} &middot; ${D.tier[i]}${imgTag}<br>`
    + `${D.hook[i]} &middot; ${D.vis[i]} &middot; ${D.framing[i]}`
    + ` &middot; role:${D.role[i]}<br>`
    + `${D.snip[i]}<br>`
    + `views ${D.views[i].toLocaleString()}${baseTag} &middot; bmk ${D.bmk[i]}`
    + ` &middot; CR_shrunk ${D.cr[i].toFixed(2)}`;
}

function buildTraces(idx, xArr, yArr, colorBy, dark) {
  const traces = [];
  const mutedHex = dark ? "#5c5b57" : "#c7c5bd";
  const surfHex = dark ? "#1a1a19" : "#fcfcfb";
  if (colorBy === "cr_bmk_shrunk") {
    const vals = idx.map(i => Math.log1p(Math.max(0, D.cr[i])));
    traces.push({
      type: "scattergl", mode: "markers", name: "log1p(CR_bmk_shrunk)",
      x: idx.map(i => xArr[i]), y: idx.map(i => yArr[i]),
      text: idx.map(hoverText), customdata: idx.map(i => D.url[i]), hoverinfo: "text",
      marker: {
        size: 5, opacity: 0.78, color: vals, colorscale: "Viridis",
        colorbar: { title: "log1p(CR)", thickness: 12, len: 0.7 }
      }
    });
  } else {
    const arr = D[FIELD_KEY[colorBy]];
    const counts = new Map();
    idx.forEach(i => counts.set(arr[i], (counts.get(arr[i]) || 0) + 1));
    const cats = Array.from(counts.keys());
    if (colorBy === "follower_tier") {
      cats.sort((a, b) => TIER_ORDER.indexOf(a) - TIER_ORDER.indexOf(b));
    } else {
      cats.sort((a, b) =>
        (MUTED_CATS.has(a) - MUTED_CATS.has(b)) || (counts.get(b) - counts.get(a))
      );
    }
    let cIdx = 0;
    for (const cat of cats) {
      const pts = idx.filter(i => arr[i] === cat);
      const isMuted = MUTED_CATS.has(cat);
      const col = isMuted ? mutedHex : PAL[cIdx++ % PAL.length];
      traces.push({
        type: "scattergl", mode: "markers", name: `${cat} (${pts.length})`,
        x: pts.map(i => xArr[i]), y: pts.map(i => yArr[i]),
        text: pts.map(hoverText), customdata: pts.map(i => D.url[i]), hoverinfo: "text",
        marker: { size: isMuted ? 4 : 5.5, opacity: isMuted ? 0.35 : 0.75, color: col }
      });
    }
  }
  if (document.getElementById("showTop").checked && idx.length > 0) {
    const sorted = idx.map(i => D.cr[i]).slice().sort((a, b) => a - b);
    const p90 = sorted[Math.floor(0.9 * (sorted.length - 1))];
    const topPts = idx.filter(i => D.cr[i] >= p90 && D.is_res[i]);
    traces.push({
      type: "scattergl", mode: "markers", name: `Top 10% CR_shrunk (>=${p90.toFixed(2)})`,
      x: topPts.map(i => xArr[i]), y: topPts.map(i => yArr[i]),
      text: topPts.map(hoverText), customdata: topPts.map(i => D.url[i]), hoverinfo: "text",
      marker: { size: 8, symbol: "circle-open", color: "#fbbf24", line: { width: 1.5 } }
    });
  }
  if (document.getElementById("showOwn").checked) {
    const ownAccs = ["@tiptreesystems", "@martincsweiss1"];
    ownAccs.forEach((h, k) => {
      const pts = idx.filter(i => D.own[i] === h);
      if (!pts.length) return;
      traces.push({
        type: "scattergl", mode: "markers", name: `${h} (${pts.length})`,
        x: pts.map(i => xArr[i]), y: pts.map(i => yArr[i]),
        text: pts.map(hoverText), customdata: pts.map(i => D.url[i]), hoverinfo: "text",
        marker: {
          size: 11, symbol: k === 0 ? "diamond" : "star",
          color: k === 0 ? "#ef4444" : (dark ? "#ffffff" : "#111111"),
          line: { color: surfHex, width: 1.2 }
        }
      });
    });
  }
  return traces;
}

function wireEvents(controlIds, divIds, drawFn) {
  controlIds.forEach(id => document.getElementById(id).addEventListener("change", drawFn));
  mq.addEventListener("change", drawFn);
  drawFn();
  divIds.forEach(id => {
    document.getElementById(id).on("plotly_click", ev => {
      const url = ev?.points?.[0]?.customdata;
      if (url) window.open(url, "_blank", "noopener");
    });
  });
}
"""


def _render_shell(
    *,
    title: str,
    note_html: str,
    controls_html: str,
    tables_html: str,
    payload: dict[str, Any],
    draw_js: str,
) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<script src="{PLOTLY}"></script>
<style>{_PAGE_CSS}</style></head><body>
<h1>{html.escape(title)}</h1>
<p class="note">{note_html}</p>
<div class="warn"><strong>Exploratory map (Decision D9):</strong> For visual inspection and
hypothesis generation only. Any cluster or skyline pattern must be tested through a
pre-registered experiment before shaping advice or templates.</div>
<div class="controls">{controls_html}</div>
<div class="grid">
  <div id="umapDiv" class="plot"></div>
  <div id="tsneDiv" class="plot"></div>
</div>
{tables_html}
<script>
const D = {json.dumps(payload)};
{_JS_SHARED}
{draw_js}
</script></body></html>"""


def _color_options() -> str:
    return "".join(
        f'<option value="{html.escape(k)}">{html.escape(lbl)}</option>'
        for k, lbl in COLOR_FIELDS
    )


def render_html(
    payload: dict[str, Any], purity_df: pd.DataFrame, own_df: pd.DataFrame
) -> str:
    """Render standalone interactive 2D UMAP + t-SNE HTML report."""
    n_total = len(payload["x_u"])
    n_res = sum(1 for v in payload["is_res"] if v)
    n_img = sum(1 for v in payload["img"] if v)
    note_html = (
        f"{n_total:,} eligible mature posts ({n_res:,} researcher-audience, "
        f"{n_img:,} photo embeddings blended with text via CLIP + BGE-small &rarr; 50D PCA). "
        'Click any point to open the post on X. <a href="embedding_impression_map.html">'
        '1D &times; Impressions skyline</a> &middot; <a href="overview.html">Back to overview</a>'
    )
    controls_html = f"""
  <label>Color by <select id="colorBy">{_color_options()}</select></label>
  <label>Subset <select id="subsetBy">
    <option value="res_own">Researcher posts + OWN</option>
    <option value="cap_own">Capped researcher corpus + OWN</option>
    <option value="all">All eligible v1 posts</option>
  </select></label>
  <label><input type="checkbox" id="showOwn" checked> Highlight OWN (@tiptree / @martin)</label>
  <label><input type="checkbox" id="showTop"> Highlight top 10% CR_bmk_shrunk</label>
  <span id="shownCount" style="color:var(--muted);font-size:12px;"></span>"""
    tables_html = (
        f"<h2>OWN neighborhood summary (k={KNN_K} nearest researcher neighbors in 50D PCA)</h2>"
        f'<div class="scroll">{_html_table(own_df)}</div>'
        f"<h2>Region structure: k={KNN_K} nearest-neighbor label purity (researcher posts)</h2>"
        f'<div class="scroll">{_html_table(purity_df)}</div>'
    )
    draw_js = """
function selectedIndices() {
  const sub = document.getElementById("subsetBy").value;
  const idx = [];
  for (let i = 0; i < D.x_u.length; i++) {
    if (sub === "res_own" && !(D.is_res[i] || D.own[i])) continue;
    if (sub === "cap_own" && !((D.is_res[i] && D.in_cap[i]) || D.own[i])) continue;
    idx.push(i);
  }
  return idx;
}
function draw() {
  const dark = mq.matches;
  const bg = dark ? "#1a1a19" : "#fcfcfb";
  const fg = dark ? "#f0efec" : "#0b0b0b";
  const grid = dark ? "#383835" : "#e4e3df";
  const colorBy = document.getElementById("colorBy").value;
  const idx = selectedIndices();
  document.getElementById("shownCount").textContent =
    `Showing ${idx.length.toLocaleString()} posts`;
  const baseLayout = (title, xt, yt) => ({
    title: { text: title, x: 0.02, font: { size: 15, color: fg } },
    paper_bgcolor: bg, plot_bgcolor: bg, font: { color: fg, size: 11 },
    margin: { l: 45, r: 16, t: 44, b: 90 }, height: 540,
    legend: { orientation: "h", y: -0.2, font: { size: 11, color: fg } },
    xaxis: { title: xt, gridcolor: grid, zeroline: false },
    yaxis: { title: yt, gridcolor: grid, zeroline: false },
    hovermode: "closest"
  });
  const cfg = { responsive: true, displayModeBar: true };
  Plotly.react("umapDiv", buildTraces(idx, D.x_u, D.y_u, colorBy, dark),
    baseLayout("UMAP 2D (cosine, 50D PCA)", "UMAP 1", "UMAP 2"), cfg);
  Plotly.react("tsneDiv", buildTraces(idx, D.x_t, D.y_t, colorBy, dark),
    baseLayout("t-SNE 2D (perplexity 35, 50D PCA)", "t-SNE 1", "t-SNE 2"), cfg);
}
wireEvents(["colorBy", "subsetBy", "showOwn", "showTop"], ["umapDiv", "tsneDiv"], draw);
"""
    return _render_shell(
        title="Tiptree X post embedding map (UMAP + t-SNE)",
        note_html=note_html,
        controls_html=controls_html,
        tables_html=tables_html,
        payload=payload,
        draw_js=draw_js,
    )


def render_impression_html(
    payload: dict[str, Any], purity_df: pd.DataFrame, skyline_df: pd.DataFrame
) -> str:
    """Render 1D UMAP / 1D t-SNE (X) vs Impressions / Normalized Reach (Y) skyline map."""
    n_total = len(payload["u1"])
    n_res = sum(1 for v in payload["is_res"] if v)
    note_html = (
        f"{n_total:,} eligible mature posts ({n_res:,} researcher-audience). "
        "X-axis compresses 50D PCA content/visual geometry to 1D UMAP or 1D t-SNE; "
        "Y-axis shows impressions (log10) or normalized reach. Click any point to open on X. "
        '<a href="embedding_map.html">2D UMAP/t-SNE map</a> &middot; '
        '<a href="overview.html">Back to overview</a>'
    )
    controls_html = f"""
  <label>Y-axis <select id="yBy">
    <option value="impressions">Impressions (log10)</option>
    <option value="baseline_ratio">Baseline ratio vs author 30d median (log10)</option>
    <option value="reach_vs_expected">Reach vs follower expectation (log10)</option>
  </select></label>
  <label>Color by <select id="colorBy">{_color_options()}</select></label>
  <label>Subset <select id="subsetBy">
    <option value="res_own">Researcher posts + OWN</option>
    <option value="cap_own">Capped researcher corpus + OWN</option>
    <option value="lt2k_own">&lt;2k follower tier + OWN</option>
    <option value="all">All eligible v1 posts</option>
  </select></label>
  <label><input type="checkbox" id="showTrend" checked> Show 12-bin median curve</label>
  <label><input type="checkbox" id="showOwn" checked> Highlight OWN (@tiptree / @martin)</label>
  <label><input type="checkbox" id="showTop"> Highlight top 10% CR_bmk_shrunk</label>
  <span id="shownCount" style="color:var(--muted);font-size:12px;"></span>"""
    tables_html = (
        "<h2>1D UMAP skyline across 8 quantile bins (researcher posts)</h2>"
        f'<div class="scroll">{_html_table(skyline_df)}</div>'
        f"<h2>2D vs 1D neighborhood structure (k={KNN_K} label purity, researcher posts)</h2>"
        f'<div class="scroll">{_html_table(purity_df)}</div>'
    )
    draw_js = """
const Y_META = {
  impressions: { key: "views", label: "Impressions (log10)", impTicks: true },
  baseline_ratio: {
    key: "base", label: "Baseline ratio (views / author 30d median, log10)", impTicks: false
  },
  reach_vs_expected: {
    key: "rve", label: "Reach vs expected (views / follower fit, log10)", impTicks: false
  }
};
function selectedIndices(yArr) {
  const sub = document.getElementById("subsetBy").value;
  const idx = [];
  for (let i = 0; i < D.u1.length; i++) {
    if (yArr[i] == null || yArr[i] <= 0) continue;
    if (sub === "res_own" && !(D.is_res[i] || D.own[i])) continue;
    if (sub === "cap_own" && !((D.is_res[i] && D.in_cap[i]) || D.own[i])) continue;
    if (sub === "lt2k_own" && !((D.is_res[i] && D.tier[i] === "<2k") || D.own[i])) continue;
    idx.push(i);
  }
  return idx;
}
function medianTrendTrace(idx, xArr, yArr, fg) {
  if (!document.getElementById("showTrend").checked || idx.length < 20) return [];
  const pairs = idx.map(i => [xArr[i], yArr[i]]).sort((a, b) => a[0] - b[0]);
  const nBins = Math.min(12, Math.max(2, Math.floor(pairs.length / 20)));
  const bx = [], by = [];
  for (let b = 0; b < nBins; b++) {
    const lo = Math.floor(b * pairs.length / nBins);
    const hi = Math.floor((b + 1) * pairs.length / nBins);
    const slice = pairs.slice(lo, hi);
    if (!slice.length) continue;
    const xs = slice.map(p => p[0]).sort((a, b) => a - b);
    const ys = slice.map(p => p[1]).sort((a, b) => a - b);
    bx.push(xs[Math.floor(xs.length / 2)]);
    by.push(ys[Math.floor(ys.length / 2)]);
  }
  return [{
    type: "scatter", mode: "lines+markers", name: "Binned median",
    x: bx, y: by, hoverinfo: "x+y",
    line: { color: fg, width: 2, dash: "dash" }, marker: { size: 5, color: fg }
  }];
}
function draw() {
  const dark = mq.matches;
  const bg = dark ? "#1a1a19" : "#fcfcfb";
  const fg = dark ? "#f0efec" : "#0b0b0b";
  const grid = dark ? "#383835" : "#e4e3df";
  const yBy = document.getElementById("yBy").value;
  const ym = Y_META[yBy];
  const yArr = D[ym.key];
  const colorBy = document.getElementById("colorBy").value;
  const idx = selectedIndices(yArr);
  document.getElementById("shownCount").textContent =
    `Showing ${idx.length.toLocaleString()} posts`;
  const shapes = ym.impTicks ? [] : [{
    type: "line", xref: "paper", x0: 0, x1: 1, y0: 1, y1: 1,
    line: { color: fg, width: 1.2, dash: "dot" }
  }];
  const yAxis = ym.impTicks
    ? { title: ym.label, type: "log", dtick: 1, tickformat: "~s", gridcolor: grid }
    : { title: ym.label, type: "log", gridcolor: grid };
  const baseLayout = (title, xt) => ({
    title: { text: title, x: 0.02, font: { size: 15, color: fg } },
    paper_bgcolor: bg, plot_bgcolor: bg, font: { color: fg, size: 11 },
    margin: { l: 55, r: 16, t: 44, b: 90 }, height: 540,
    legend: { orientation: "h", y: -0.2, font: { size: 11, color: fg } },
    xaxis: { title: xt, gridcolor: grid, zeroline: false },
    yaxis: { ...yAxis, zeroline: false },
    shapes, hovermode: "closest"
  });
  const cfg = { responsive: true, displayModeBar: true };
  Plotly.react(
    "umapDiv",
    buildTraces(idx, D.u1, yArr, colorBy, dark).concat(medianTrendTrace(idx, D.u1, yArr, fg)),
    baseLayout("1D UMAP × Reach (cosine, 50D PCA)", "UMAP 1D"),
    cfg
  );
  Plotly.react(
    "tsneDiv",
    buildTraces(idx, D.t1, yArr, colorBy, dark).concat(medianTrendTrace(idx, D.t1, yArr, fg)),
    baseLayout("1D t-SNE × Reach (perplexity 35, 50D PCA)", "t-SNE 1D"),
    cfg
  );
}
wireEvents(
  ["yBy", "colorBy", "subsetBy", "showTrend", "showOwn", "showTop"],
  ["umapDiv", "tsneDiv"],
  draw
);
"""
    return _render_shell(
        title="Tiptree X post 1D embedding × impressions skyline",
        note_html=note_html,
        controls_html=controls_html,
        tables_html=tables_html,
        payload=payload,
        draw_js=draw_js,
    )


def _save_cache(
    df: pd.DataFrame,
    pca_vecs: np.ndarray,
    umap_xy: np.ndarray,
    tsne_xy: np.ndarray,
    umap_1d: np.ndarray,
    tsne_1d: np.ndarray,
    has_img: np.ndarray,
) -> None:
    out = pd.DataFrame(
        {
            "post_id": df["post_id"].astype(str),
            "has_embedded_image": has_img,
            "umap_x": umap_xy[:, 0],
            "umap_y": umap_xy[:, 1],
            "tsne_x": tsne_xy[:, 0],
            "tsne_y": tsne_xy[:, 1],
            "umap_1d": umap_1d,
            "tsne_1d": tsne_1d,
        }
    )
    for i in range(pca_vecs.shape[1]):
        out[f"pca_{i}"] = pca_vecs[:, i]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(CACHE, index=False)


def _load_or_compute(
    df: pd.DataFrame, *, recompute: bool, media_dir: Path, embed_fn: EmbedFn | None
) -> tuple[
    np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray
]:
    if CACHE.exists() and not recompute:
        cached = pd.read_parquet(CACHE)
        wanted = set(df["post_id"].astype(str))
        if len(cached) == len(df) and set(cached["post_id"].astype(str)) == wanted:
            aligned = cached.set_index(cached["post_id"].astype(str)).loc[
                df["post_id"].astype(str)
            ]
            pca_cols = sorted(
                (c for c in aligned.columns if c.startswith("pca_")),
                key=lambda c: int(c.split("_")[1]),
            )
            if pca_cols:
                pca_vecs = aligned[pca_cols].to_numpy(dtype="float32")
                ux = aligned["umap_x"].to_numpy(dtype="float32")
                uy = aligned["umap_y"].to_numpy(dtype="float32")
                tx = aligned["tsne_x"].to_numpy(dtype="float32")
                ty = aligned["tsne_y"].to_numpy(dtype="float32")
                has_img = aligned["has_embedded_image"].to_numpy(dtype=bool)
                if {"umap_1d", "tsne_1d"} <= set(aligned.columns):
                    u1 = aligned["umap_1d"].to_numpy(dtype="float32")
                    t1 = aligned["tsne_1d"].to_numpy(dtype="float32")
                else:
                    u1, t1 = project_1d(pca_vecs)
                    _save_cache(
                        df, pca_vecs, np.column_stack([ux, uy]), np.column_stack([tx, ty]),
                        u1, t1, has_img,
                    )
                return pca_vecs, ux, uy, tx, ty, u1, t1, has_img

    pca_vecs, has_img = embed_posts(df, media_dir=media_dir, embed_fn=embed_fn)
    umap_xy, tsne_xy = project_2d(pca_vecs)
    u1, t1 = project_1d(pca_vecs)
    _save_cache(df, pca_vecs, umap_xy, tsne_xy, u1, t1, has_img)
    return pca_vecs, umap_xy[:, 0], umap_xy[:, 1], tsne_xy[:, 0], tsne_xy[:, 1], u1, t1, has_img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=SRC)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--out-imp", type=Path, default=OUT_IMP)
    ap.add_argument("--recompute", action="store_true")
    a = ap.parse_args()

    df = load_eligible(a.src)
    pca_vecs, ux, uy, tx, ty, u1, t1, has_img = _load_or_compute(
        df, recompute=a.recompute, media_dir=MEDIA_DIR, embed_fn=None
    )
    umap_xy = np.column_stack([ux, uy])
    tsne_xy = np.column_stack([tx, ty])
    purity_df, own_df = compute_region_stats(
        df, pca_vecs, umap_xy, tsne_xy, umap_1d=u1, tsne_1d=t1
    )
    skyline_df = compute_bin_skyline(df, u1)
    STATS_OUT.parent.mkdir(parents=True, exist_ok=True)
    STATS_OUT.write_text(
        json.dumps(
            {
                "purity": purity_df.to_dict("records"),
                "own": own_df.to_dict("records"),
                "skyline": skyline_df.to_dict("records"),
            },
            indent=2,
        )
    )
    payload = build_payload(df, umap_xy, tsne_xy, has_img, umap_1d=u1, tsne_1d=t1)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(render_html(payload, purity_df, own_df))
    a.out_imp.parent.mkdir(parents=True, exist_ok=True)
    a.out_imp.write_text(render_impression_html(payload, purity_df, skyline_df))
    print(f"wrote {len(df)} posts ({int(has_img.sum())} with images) -> {a.out} & {a.out_imp}")
    print(purity_df.to_string(index=False))
    if not own_df.empty:
        print("\nOWN neighborhoods:\n" + own_df.to_string(index=False))
    if not skyline_df.empty:
        print("\n1D UMAP skyline:\n" + skyline_df.to_string(index=False))


if __name__ == "__main__":
    main()
