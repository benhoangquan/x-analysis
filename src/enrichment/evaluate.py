"""Agreement report: hand labels vs judge labels, per split, against the proposed bars.

Bars (held-out half): kappa >= 0.7 archetype, >= 0.8 visual type, rigor within one point on
85% of posts. The researcher filter is reported with accuracy and kappa.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

GOLD = Path("data/gold/hand_labels.csv")
LABELS = Path("data/processed/labels.parquet")
REPORT = Path("outputs/reports/label-agreement.md")
BARS = {"hook_archetype": 0.7, "visual_type": 0.8, "rigor_within_1": 0.85}


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
    return res


def report(gold: pd.DataFrame, labels: pd.DataFrame) -> str:
    lines = ["# Label agreement (hand labels vs judge)", ""]
    for split in ("tune", "heldout"):
        g = gold[gold["split"] == split]
        r = agreement(g, labels)
        lines.append(f"## {split} (n={int(r['n'])})")
        for k, v in r.items():
            if k == "n":
                continue
            bar = BARS.get(k)
            note = ""
            if split == "heldout" and bar is not None:
                note = f"  (bar {bar}: {'met' if v >= bar else 'NOT met'})"
            lines.append(f"- {k}: {v:.2f}{note}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    gold = pd.read_csv(GOLD, dtype={"post_id": str})
    gold = gold.dropna(subset=["hook_archetype", "technical_rigor_score"])
    labels = pd.read_parquet(LABELS)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report(gold, labels))
    print(REPORT.read_text())


if __name__ == "__main__":
    main()
