"""Findings report and evidence-gated post templates (Milestone 4)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.analysis.lift import analysis_corpus, lift_table
from src.config import OWN_HANDLES, QUERY_VERSION
from src.enrichment.evaluate import BARS, agreement
from src.enrichment.rules import hype_flags
from src.metrics.baselines import TIER_LABELS

LABELLED = Path("data/processed/posts_labelled.parquet")
GOLD = Path("data/gold/hand_labels.csv")
LABELS = Path("data/processed/labels.parquet")
STATS_JSON = Path("data/processed/ingestion_stats.json")
OUT_MD = Path("outputs/reports/findings.md")


def check_label_gate(
    gold_path: Path = GOLD, labels_path: Path = LABELS
) -> tuple[bool, dict[str, float]]:
    """Decision 19: held-out hand-label agreement must meet evaluate.BARS before advice."""
    if not gold_path.exists() or not labels_path.exists():
        return False, {}
    gold = pd.read_csv(gold_path, dtype={"post_id": str})
    if "split" not in gold.columns:
        return False, {}
    heldout = gold[gold["split"] == "heldout"].dropna(
        subset=["hook_archetype", "technical_rigor_score"]
    )
    if heldout.empty:
        return False, {}
    labels = pd.read_parquet(labels_path)
    scores = agreement(heldout, labels)
    if not scores.get("n"):
        return False, scores
    required = {"hook_archetype", "visual_type", "rigor_within_1", "researcher_kappa"}
    if not required <= set(scores):
        return False, scores
    if "framing" in heldout.columns and heldout["framing"].notna().any():
        required.add("framing")
    if "poster_role" in heldout.columns and heldout["poster_role"].notna().any():
        required.add("poster_role")
    passed = all(
        scores.get(k, float("nan")) >= BARS[k]
        for k in required
        if k in BARS
    )
    return passed, scores


def _md_table(df: pd.DataFrame, fmt: dict[str, str] | None = None) -> str:
    fmt = fmt or {}
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        cells = []
        for col in cols:
            v = row[col]
            cells.append(fmt.get(col, "{}").format(v) if pd.notna(v) else "n/a")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _coverage_section(df: pd.DataFrame) -> str:
    work = df.copy()
    work["_res"] = work["is_researcher_post"] == True  # noqa: E712
    cov = (
        work.groupby(["cohort", "follower_tier"], dropna=False)
        .agg(
            posts=("post_id", "count"),
            eligible=("eligible", "sum"),
            mature=("mature", "sum"),
            authors=("author_handle", "nunique"),
            researcher_posts=("_res", "sum"),
        )
        .reset_index()
    )
    rank = {t: i for i, t in enumerate(TIER_LABELS)}
    cov["_t"] = cov["follower_tier"].map(lambda t: rank.get(t, 99))
    cov = cov.sort_values(["cohort", "_t"]).drop(columns=["_t"])
    return _md_table(cov)


def _scorecard_section(df: pd.DataFrame) -> str:
    elig = df[df["eligible"].astype(bool) & df["mature"].astype(bool)]
    small = elig[elig["follower_tier"] == "<2k"]
    own = elig[elig["author_handle"].str.lower().isin(OWN_HANDLES)]
    lines = ["## Tiptree scorecard (`<2k` benchmark)", ""]
    if small.empty:
        lines.append("No mature posts in the `<2k` tier yet.")
        return "\n".join(lines)
    s_rate = small["cr_bmk_shrunk"] if "cr_bmk_shrunk" in small else small["cr_bmk"]
    q25, q50, q75, q90 = s_rate.quantile([0.25, 0.50, 0.75, 0.90]).tolist()
    lines.append(
        f"`<2k` tier distribution (`cr_bmk_shrunk`, n={len(small)}): "
        f"p25={q25:.2f}, median={q50:.2f}, p75={q75:.2f}, p90={q90:.2f} bookmarks/1k views."
    )
    lines.append("")
    if own.empty:
        lines.append("No mature eligible posts from `@tiptreesystems` or `@martincsweiss1` yet.")
        return "\n".join(lines)
    rows = []
    for h in OWN_HANDLES:
        g = own[own["author_handle"].str.lower() == h]
        if g.empty:
            continue
        has_shrunk = "cr_bmk_shrunk" in g and g["cr_bmk_shrunk"].notna().any()
        col = "cr_bmk_shrunk" if has_shrunk else "cr_bmk"
        med = float(g[col].median())
        pct = float((s_rate <= med).mean() * 100)
        rows.append({
            "account": f"@{h}",
            "mature_posts": len(g),
            "median_views": g["impressions"].median(),
            "median_cr_bmk": g["cr_bmk"].median(),
            "median_cr_bmk_shrunk": med,
            "pctile_in_under_2k": pct,
        })
    if rows:
        lines.append(_md_table(
            pd.DataFrame(rows),
            {
                "median_views": "{:,.0f}",
                "median_cr_bmk": "{:.2f}",
                "median_cr_bmk_shrunk": "{:.2f}",
                "pctile_in_under_2k": "{:.0f}%",
            },
        ))
    return "\n".join(lines)


def _format_lift_table(t: pd.DataFrame, dim_cols: list[str]) -> str:
    if t.empty:
        return "_No eligible rows._"
    disp = t[[*dim_cols, "n_posts", "n_authors", "cr_bmk", "lift_vs_tier", "evidence"]].copy()
    disp["cr_bmk_ci"] = [
        f"{r.cr_bmk:.2f} [{r.ci_low:.2f}, {r.ci_high:.2f}]"
        if r.passes_gate
        else "insufficient data"
        for r in t.itertuples()
    ]
    disp["lift_ci"] = [
        f"{r.lift_vs_tier:.2f}x [{r.lift_ci_low:.2f}, {r.lift_ci_high:.2f}]"
        if r.passes_gate
        else "insufficient data"
        for r in t.itertuples()
    ]
    disp = disp[[*dim_cols, "n_posts", "n_authors", "cr_bmk_ci", "lift_ci", "evidence"]]
    return _md_table(disp)


def _template_block(
    corpus: pd.DataFrame, row: pd.Series, dim: str
) -> list[str]:
    tier = str(row["follower_tier"])
    val = str(row[dim])
    sub = corpus[
        (corpus["follower_tier"] == tier) & (corpus[dim].astype(str) == val)
    ].sort_values(
        "cr_bmk_shrunk" if "cr_bmk_shrunk" in corpus else "cr_bmk",
        ascending=False,
    )
    examples = []
    for r in sub.head(3).itertuples():
        url = getattr(r, "url", None) or f"https://x.com/i/web/status/{r.post_id}"
        examples.append(f"[{r.post_id}]({url})")
    ex_text = ", ".join(examples) if examples else "none in slice"
    hook = (
        f"Lead with a {val.lower().replace('_', ' ')} grounded in a specific paper claim"
        if dim == "hook_archetype"
        else f"Pair a concise empirical claim with a {val.lower().replace('_', ' ')} asset"
    )
    visual = val if dim == "visual_type" else "PAPER_FIGURE or LACUNA_MAP (when matching claim)"
    evidence_slot = (
        "Cite one ablation metric, baseline comparison, or contradiction from the paper."
    )
    cta = "End with a direct link to the paper or Lacuna topology and an open technical question."
    candidate_copy = f"{hook}. {evidence_slot} {cta}"
    if hype_flags(candidate_copy):
        raise ValueError(f"Generated template failed hype lint: {candidate_copy}")
    return [
        f"### Template: `{tier}` × `{dim}={val}`",
        f"- **Hook pattern:** {hook}",
        f"- **Evidence slot:** {evidence_slot}",
        f"- **Visual spec:** {visual}",
        f"- **Call-to-action placement:** {cta}",
        f"- **Measured lift:** {row['lift_vs_tier']:.2f}x tier baseline "
        f"(95% CI [{row['lift_ci_low']:.2f}, {row['lift_ci_high']:.2f}], "
        f"pooled CR_bmk {row['cr_bmk']:.2f}, n={int(row['n_posts'])} posts, "
        f"{int(row['n_authors'])} authors)",
        f"- **Examples:** {ex_text}",
        "",
    ]


def generate_findings(
    df: pd.DataFrame,
    *,
    validated: bool,
    trust_jev: bool = False,
    query_version: str = QUERY_VERSION,
    dropped_filler: int = 0,
    n_boot: int = 1000,
) -> str:
    """Build outputs/reports/findings.md; refuse lifts/templates unless validated or trust_jev."""
    lv = (
        str(df["label_version"].dropna().iloc[0])
        if "label_version" in df.columns and df["label_version"].notna().any()
        else "-"
    )
    lines = [
        "# Tiptree X Analytics Findings",
        "",
        f"- **Query version:** `{query_version}`",
        f"- **Label version:** `{lv}`",
        f"- **Filler items dropped at ingestion:** {dropped_filler}",
        "",
    ]
    if trust_jev and not validated:
        lines += [
            "> **Note (Decision 60):** Ben waived the Milestone 3 manual post hand-labelling "
            "checks; lift tables, recommendations, and templates below use Jev rubric v2 labels "
            "directly without held-out human kappa verification. Statistical cell gates "
            "(>=20 posts, >=10 authors) remain enforced.",
            "",
        ]
    lines += [
        "## Corpus coverage",
        "",
        _coverage_section(df),
        "",
        _scorecard_section(df),
        "",
    ]
    if not (validated or trust_jev):
        lines += [
            "## Lift tables, recommendations & templates",
            "",
            "**Withheld (Decision 19 gate):** held-out hand-label agreement targets have not been "
            "met yet. No lift estimates, writing recommendations, or post templates are emitted "
            "from unvalidated labels.",
            "",
        ]
        return "\n".join(lines)

    corpus = analysis_corpus(df)
    if corpus.empty:
        lines += [
            "## Lift tables, recommendations & templates",
            "",
            "No filter-passing, eligible, mature, capped posts available.",
            "",
        ]
        return "\n".join(lines)

    dims = [c for c in ("hook_archetype", "visual_type", "framing") if c in corpus.columns]
    tables = {
        dim: lift_table(corpus, ["follower_tier", dim], n_boot=n_boot)
        for dim in dims
    }
    lines += ["## Lift tables (filter-passing, capped corpus)", ""]
    for dim, tbl in tables.items():
        tbl_md = _format_lift_table(tbl, ["follower_tier", dim])
        lines += [f"### By follower tier × `{dim}`", "", tbl_md, ""]

    winners: list[tuple[str, pd.Series]] = []
    for dim, tbl in tables.items():
        ok = tbl[tbl["passes_gate"] & (tbl["lift_ci_low"] > 1.0)]
        for _, r in ok.iterrows():
            winners.append((dim, r))
    # Prioritize <2k tier first, then highest lift CI lower bound
    winners.sort(key=lambda x: (x[1]["follower_tier"] != "<2k", -x[1]["lift_ci_low"]))

    lines += ["## Actionable recommendations for Martin", ""]
    if not winners:
        lines.append(
            "No cell passed the evidence gate (>=20 posts, >=10 authors) with a 95% lift "
            "interval strictly above 1.0x; recommendations stay withheld."
        )
        lines.append("")
    else:
        for dim, r in winners:
            lines.append(
                f"- In `{r['follower_tier']}`, posts with `{dim}={r[dim]}` achieve "
                f"**{r['lift_vs_tier']:.2f}x** higher bookmark rate "
                f"(95% CI [{r['lift_ci_low']:.2f}, {r['lift_ci_high']:.2f}], "
                f"CR_bmk={r['cr_bmk']:.2f} vs tier {r['tier_cr_bmk']:.2f}; "
                f"n={int(r['n_posts'])} posts across {int(r['n_authors'])} authors)."
            )
        lines.append("")

    lines += ["## Post templates (evidence-gated)", ""]
    if not winners:
        lines.append("No templates generated because no lift row cleared the gate above 1.0x.")
        lines.append("")
    else:
        for dim, r in winners:
            lines += _template_block(corpus, r, dim)
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=LABELLED)
    ap.add_argument("--gold", type=Path, default=GOLD)
    ap.add_argument("--labels", type=Path, default=LABELS)
    ap.add_argument("--output", type=Path, default=OUT_MD)
    ap.add_argument("--dropped-filler", type=int, default=None)
    ap.add_argument(
        "--trust-jev",
        action="store_true",
        help="use Jev v2 labels without held-out human kappa gate (decision 60)",
    )
    a = ap.parse_args()
    df = pd.read_parquet(a.data)
    validated, scores = check_label_gate(a.gold, a.labels)
    dropped = a.dropped_filler
    if dropped is None:
        dropped = (
            int(json.loads(STATS_JSON.read_text()).get("dropped_filler", 0))
            if STATS_JSON.exists()
            else 0
        )
    md = generate_findings(
        df, validated=validated, trust_jev=a.trust_jev, dropped_filler=dropped
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(md)
    print(f"wrote {a.output} (validated={validated}, trust_jev={a.trust_jev}, scores={scores})")


if __name__ == "__main__":
    main()
