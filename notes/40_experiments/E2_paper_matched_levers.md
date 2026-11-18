# E2: Figure plus contested claim on the same paper

Status: done
Tests: H2 (wording in the project doc).

## Pre-registration

- **Data:** the [paper panel](../30_concepts/paper_panel.md): filter-passing, eligible, mature posts, at most 10 per author. H2 is about researcher intent, so the researcher filter applies.
- **Arms:**
  - T (artifact + hook): `visual_type = PAPER_FIGURE` and `hook_archetype = CONTESTED_CLAIM`. `PAPER_FIGURE` covers the benchmark tables and architecture figures H2 names, plus loss curves.
  - C (plain summary): `visual_type = NONE` and the post mainly summarises the paper. The summary class comes from the milestone 3 taxonomy revision (likely `PAPER_ANNOUNCEMENT`). If the revision creates none, a Jev yes/no question, "Is this post mainly a summary of the paper's abstract?", is validated on the hand-label set instead.
- **Strata:** paper.
- **Primary test:** H2: stratified rate ratio of `S_intent` (AGENTS.md formula, replies counted as they are) per impression, T vs C. Prediction > 1.
- **Robustness (part of the decision):** the same test with strata of paper × follower tier. If its point estimate falls on the other side of 1 from the primary, the verdict is `inconclusive`.
- **Secondary:** `CR_bmk`; the two main effects within paper, figure vs none (any hook) and contested claim vs summary (any visual); impressions ratio T vs C, since a per-impression rate can fall when a format earns more views; figure kind (table, architecture, curve) if labelled; the under-2k tier alone.
- **Decision:** README verdict rule, with the robustness condition above.
- **Feasibility gate:** at least 20 papers with both a T and a C post. In v0, T was 45 of 1,428 eligible mature posts (3%, Jev v1 labels, unvalidated). If the gate fails, the two main effects become the primary tests (each with its own verdict), decided from counts before any outcome is seen.
- **Prerequisites:** paper panel (plan decision 29); milestone 3 labels at target; the summary class.
- **Threats:**
  - Posters choose their format. Accounts that post figures may have more engaged audiences; the paper × tier check and the role mix per arm (reported) address part of this.
  - The arm definitions are only as good as the archetype and visual labels.
  - Two posts on the same paper can differ in timing; first posts per arm are reported.

## Amendments

- 2026-11-14 (draft, before freeze; plan decision 44): if the within-paper gate fails, which the panel makes likely (12 of 200 papers have 3 or more posters), the verdict is `insufficient`, H2 is reported as untestable from X search data at this budget, and the main-effects fallback is dropped. The figure-plus-contested-claim format enters the posting experiment as an untested arm.

- 2026-11-14 (draft, before freeze): primary measure changed from `CR_bmk` to `S_intent` (Ben).

- 2026-11-17 (before freeze): Milestone 3 manual hand-labelling waived under plan decision 60 (`label_version=cf3607061e63`). Outcome-blind feasibility counts on `v1-2026-11-17` (`685` filter-passing capped paper-linked posts across `336` authors and `506` papers): `T` (`PAPER_FIGURE` + `CONTESTED_CLAIM`) has `41` posts (`24` authors) and `C` (`NONE` + `OTHER`) has `160` posts (`119` authors), yielding `6` contributing `first_paper_id` strata (< `20` gate; `3` `paper_tier` strata). Per plan decision 44, `E2` stays within-paper and is frozen as-is (will record `insufficient` against the 20-paper gate).

## Runs

- 2026-11-17, commit `1e96a49`, data `v1-2026-11-17`, labels `cf3607061e63`: `685` filter-passing capped paper-linked posts; `201` posts in `T` (`41`) + `C` (`160`) across `142` authors sharing `6` papers. Log: `outputs/runs/E2_2026-11-17.log`.
  - `H2` (`S_intent` RR, within-paper `T` vs `C`): `3.5247` (`99% CI [0.8230, 6.9021]`, `n=201`, `au=142`, `n_strata=6`) → `insufficient` (20-paper gate failed).
  - Negative control `NC-H2`: `0.9060` (`99% CI [0.1479, 3.0124]`) → `control`.

## Verdict

- **`insufficient` (plan decision 44):** Only `6` papers hold both `PAPER_FIGURE + CONTESTED_CLAIM` (`T`) and plain-text `OTHER` (`C`) against the 20-paper gate (`3.52x` exploratory point estimate across those 6 papers, `99% CI [0.82, 6.90]`). Per decision 44, H2 is untestable at this budget from X search data, and the figure-plus-contested-claim format enters the Milestone 5 posting experiment as an untested arm (consistent with the descriptive `<2k` `PAPER_FIGURE` lift in `outputs/reports/findings.md`).
