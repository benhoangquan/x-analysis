"""Agreement report: hand labels vs judge labels, per split, against the plan's bars.

Bars (held-out half only): kappa >= 0.7 archetype, >= 0.8 visual type, >= 0.8 researcher filter
(decision 34), >= 0.7 framing and poster role (decision 30); rigor within one point on 85% of
posts. Other splits (tune, pilot) are reported without bars.

    uv run python -m src.enrichment.evaluate
    uv run python -m src.enrichment.evaluate --gold data/gold/pilot_labels.csv \
        --labels data/processed/pilot_jev_labels.parquet --report outputs/reports/pilot-check.md
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import pandas as pd

GOLD = Path("data/gold/hand_labels.csv")
LABELS = Path("data/processed/labels.parquet")
REPORT = Path("outputs/reports/label-agreement.md")
BARS = {"hook_archetype": 0.7, "visual_type": 0.8, "rigor_within_1": 0.85,
        "researcher_kappa": 0.8, "framing": 0.7, "poster_role": 0.7}  # fmt: skip


def cohen_kappa(a: list, b: list) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n**2
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def agreement(gold: pd.DataFrame, labels: pd.DataFrame) -> dict[str, float]:
    m = gold.merge(labels, on="post_id", suffixes=("_gold", "_model"))
    m = m[m["error"].isna()]
    res: dict[str, float] = {"n": float(len(m))}
    if m.empty:
        return res
    for col in ("hook_archetype", "visual_type"):
        res[col] = cohen_kappa(m[f"{col}_gold"].tolist(), m[f"{col}_model"].tolist())
    r_gold = m["is_researcher_post_gold"].astype(str).str.lower().isin(["true", "1", "yes"])
    r_model = m["is_researcher_post_model"].astype(bool)
    res["researcher_accuracy"] = float((r_gold == r_model).mean())
    res["researcher_kappa"] = cohen_kappa(r_gold.tolist(), r_model.tolist())
    diff = (
        m["technical_rigor_score_gold"].astype(int) - m["technical_rigor_score_model"].astype(int)
    ).abs()
    res["rigor_within_1"] = float((diff <= 1).mean())
    for col in ("framing", "poster_role"):  # rubric v2 fields; absent on v1 labels
        g, j = f"{col}_gold", f"{col}_model"
        if g in m and j in m:
            both = m[m[g].notna() & (m[g].astype(str) != "") & m[j].notna()]
            if len(both):
                res[col] = cohen_kappa(both[g].astype(str).tolist(), both[j].astype(str).tolist())
                res[f"{col}_n"] = float(len(both))
    return res


def report(gold: pd.DataFrame, labels: pd.DataFrame) -> str:
    lines = ["# Label agreement (hand labels vs judge)", ""]
    for split in [s for s in ("pilot", "tune", "heldout") if s in set(gold["split"])]:
        g = gold[gold["split"] == split]
        r = agreement(g, labels)
        lines.append(f"## {split} (n={int(r['n'])})")
        for k, v in r.items():
            if k == "n" or k.endswith("_n"):
                continue
            bar = BARS.get(k)
            note = ""
            if split == "heldout" and bar is not None:
                note = f"  (bar {bar}: {'met' if v >= bar else 'NOT met'})"
            lines.append(f"- {k}: {v:.2f}{note}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", type=Path, default=GOLD)
    ap.add_argument("--labels", type=Path, default=LABELS)
    ap.add_argument("--report", type=Path, default=REPORT)
    a = ap.parse_args()
    gold = pd.read_csv(a.gold, dtype={"post_id": str})
    gold = gold.dropna(subset=["hook_archetype", "technical_rigor_score"])
    labels = pd.read_parquet(a.labels)
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(report(gold, labels))
    print(a.report.read_text())


if __name__ == "__main__":
    main()
