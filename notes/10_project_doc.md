# Project doc

Living doc: the current state of the research. It is rewritten in place to stay true. The history is in [00_daily_log/](00_daily_log/), every run is in the ledger [40_experiments/results.tsv](40_experiments/results.tsv), and the way to keep this file is in [README.md](README.md).
The method rules and milestone status live in [docs/implementation-plan.md](../docs/implementation-plan.md).

## Current state

As of 2026-11-12.

- **Phase:** experiment design. No hypothesis has been tested. The only data is v0 (2,073 posts, superseded), which shows feasibility only.
- **Method settled:** plan decisions 27–32 cover the notes protocol, the hypothesis-test measures and verdict rule, the paper panel, the `framing` and `poster_role` labels, E1's scope and the new inputs. E1–E6 stay `draft` until milestones 1–3 give their feasibility counts.
- **Blocking the tests:** milestone 1 (roster collection and paper panel) and milestone 3 (validated labels, including `framing` and `poster_role`).
- **Next:**
  1. Add the paper panel's 30-paper first batch to the milestone 1 collection run.
  2. Add `framing` and `poster_role` to the rubric, the Jev call and the label sheet.
  3. Extend `experiments.py` to E1, E2, E3 and E5 once panel data exists; rerun E4 and E6 on the roster.
- **Harness:** `src/analysis/experiments.py` runs E4 and E6; dry runs on v0 (2026-11-12) passed as code checks. v0 gives 0–1 within-author strata for E4, so the real run needs the roster.

## Hypotheses

| ID | Status | Test | Latest evidence |
|---|---|---|---|
| H1 | untested | [E1](40_experiments/E1_poster_role.md) | None. Needs the paper panel and the `poster_role` label. |
| H2 | untested | [E2](40_experiments/E2_paper_matched_levers.md) | None. v0 had 3 papers with more than one poster, so it cannot hold a paper constant. |
| H3 | untested | [E3](40_experiments/E3_decision_model.md) | None. |
| H4 | untested | [E4](40_experiments/E4_framing.md) | None. v0 had no curiosity-gap phrase among 122 researcher posts; H4c may be `insufficient`. |

- **H1 (Poster Tier — Reach vs. Intent Split):** Hype explainers generate higher raw impressions and likes than paper authors or neutral curators, whereas paper authors and neutral curators achieve a higher High-Intent Score (bookmarks, quotes, and technical replies) per impression.
  - Measured as: within-paper impressions ratio (H1a) and within-paper `S_intent` rate ratios, original researcher vs non-researcher (H1b-O) and credentialed researcher vs non-researcher (H1b-C). "Poster tier" is [poster role](30_concepts/poster_role.md): original researcher, credentialed researcher, or neither. "Technical replies" is dropped; replies are counted as they are ([intent measures](30_concepts/intent_measures.md)).
- **H2 (Controllable Levers on Identical Papers):** Holding the underlying arXiv paper constant across multiple posters, posts pairing a concrete empirical artifact (benchmark table or architecture figure) with a contested-claim hook achieve a higher High-Intent Score than plain-text abstract summaries.
  - Measured as: `S_intent` rate ratio, stratified by paper, `PAPER_FIGURE` + `CONTESTED_CLAIM` vs plain-text summary, on filter-passing [paper panel](30_concepts/paper_panel.md) posts.
- **H3 (Decision Model Feasibility):** Even after normalizing for poster follower count, poster tier, and author prestige, controllable post features (paper substance, visual type, and copy framing) retain enough predictive signal to classify above-median post performance.
  - Measured as: ΔAUC of a logistic model with controllable features over a controls-only model, folds grouped by author; supported at ΔAUC ≥ 0.03 with AUC ≥ 0.60.
- **H4 (Linguistic Framing & Interaction Type):** Posts using open-ended technical questions generate a higher reply rate than declarative summaries, whereas declarative empirical claims generate a higher bookmark-to-like ratio—and generic curiosity-gap phrasing (e.g., "Do you know...") fails to lift high-intent researcher saves.
  - Measured as: within-author rate ratios for other people's replies per view (H4a), bookmarks per like (H4b), and `CR_bmk` for curiosity gap vs empirical claim, with a null prediction (H4c). Classes defined in [framing](30_concepts/framing.md).

## Open questions

- When a post about a paper spreads, what exact share of variance is attributable to each of the 5 factors (paper content, paper authors, posting account tier, post visual, and post language/copy)? → [E5](40_experiments/E5_variance_shares.md)
- Which specific linguistic patterns (e.g., direct questions, "do you know" hooks, first-person vs. third-person framing) separate high-reply posts from high-bookmark posts within the researcher audience? → [E6](40_experiments/E6_reply_vs_bookmark_language.md)
- Does the actor's `url:` search match arXiv IDs inside expanded links, and how many posters does a typical panel paper get? → the paper panel's first batch (plan decision 29)

- Is the proposed credential rule right (at least 3 papers in cs.LG, cs.CL, cs.CV or stat.ML on Semantic Scholar, or a bio that states a research position)? → Ben, before E1 is frozen

## Key findings

None yet. Each entry will give the claim, its ledger row and its data version.

## Decisions

| ID | Date | Decision | Status | Recorded in |
|---|---|---|---|---|
| D1 | 2026-11-12 | `notes/` is the research log: daily log, this doc, experiment files and a run ledger. Hypothesis tests are pre-registered and committed before they run on real data. | accepted | plan decision 27; AGENTS.md §8 |
| D2 | 2026-11-12, revised 2026-11-14 | "High-Intent Score" in H1 and H2 is `S_intent` as AGENTS.md defines it (primary), with `CR_bmk` secondary; "technical replies" is dropped and replies are counted as they are. Reply rate, bookmarks per like and `top_half` are descriptive measures. Verdicts use 99% intervals and a smallest effect of 1.2×. | accepted | plan decision 28; AGENTS.md §3 |
| D3 | 2026-11-12 | Collect a paper panel: about 300 arXiv papers with every post linking them, cohort `PANEL`, about $2. | accepted | plan decision 29; AGENTS.md §4 |
| D4 | 2026-11-12 | Add two labels: `poster_role` (H1's "poster tier": original researcher, credentialed researcher, non-researcher; revised 2026-11-14) and `framing` (H4). | accepted | plan decision 30; AGENTS.md §3 |
| D5 | 2026-11-12 | E1 uses paper-linked posts whether or not they pass the researcher filter, an exception to plan decision 22; E1 produces no templates. | accepted | plan decision 31; AGENTS.md §3 |
| D6 | 2026-11-12 | Add scikit-learn, and the arXiv and Semantic Scholar APIs for paper metadata. | accepted | plan decision 32; AGENTS.md §5; `pyproject.toml` |
