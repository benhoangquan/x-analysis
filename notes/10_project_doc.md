# Project doc

Living doc: the current state of the research. It is rewritten in place to stay true. The history is in [00_daily_log/](00_daily_log/), every run is in the ledger [40_experiments/results.tsv](40_experiments/results.tsv), and the way to keep this file is in [README.md](README.md).
The method rules and milestone status live in [docs/implementation-plan.md](../docs/implementation-plan.md).

## Current state

As of 2026-11-14.

- **Phase:** pre-run review complete (decisions 27–58). Milestone 1 in progress; waiting on Ben's admission review before roster collection. Test batch, panel, own-paper search, admission, two borderline top-ups and a draft roster done on 2026-11-14 ($1.105 spent of $10). No hypothesis has been tested. The only data is v0 (2,073 posts, superseded), which shows feasibility only.
- **Method settled:** plan decisions 27–34 cover the notes protocol, the hypothesis-test measures and verdict rule, the paper panel, the `framing` and `poster_role` labels, E1's scope, the new inputs, the $10 Apify cap and the audience-filter kappa target. E1–E6 stay `draft` until milestones 1–3 give their feasibility counts.
- **Budget:** new Apify spend is capped at $10 and enforced in `src/ingestion/apify.py`; $1.105 spent (`data/apify_spend.csv`; the test and panel runs match Apify's bill); roster collection has its own $5 cap (decision 56). Collection fits the cap with a 90-day window and no replies (plan decision 36).
- **Labelling:** a 40-post pilot sheet from v0 is with Ben (`data/gold/pilot_sheet.csv`, guide `docs/hand-labelling.md`).
- **Test batch:** `OR` joins work, v0 had lost about 90% of older posts, the item G seeds are individual researchers, and `url:` search works but random papers have a median of 1 poster (plan, What the test batch showed).
- **Paper panel:** collected ($0.188). Papers get few link posts (median 0 posters, 12 of 200 with 3 or more), so E1 and E2 cannot hold the paper constant at the planned scale. The actor pads thin queries with charged filler (67% of panel items). Plan, What the paper panel showed.
- **Roster:** 426 candidates; Jev admitted 214 after two top-ups (127 borderline stay out, 85 rejected). Draft roster 200 (130 / 48 / 17 / 5 by tier, including the 8 hand-picked accounts, organisations out), waiting on Ben's blind review of 75 (`data/gold/admission_review.csv`). Posting is heavy-tailed: a few accounts post dozens of times a week, most rarely.
- **Rubric v2:** researcher question, `framing` and `poster_role` written and tested, not run (decision 41); the Semantic Scholar paper count is not wired in.
- **Blocking the tests:** Ben's admission review, then roster collection (milestone 1, collector ready); Ben's pilot labels, then the rubric v2 check and labelling (milestone 3).
- **Next:**
  1. Ben: admission review (`data/gold/admission_review.csv`) and pilot labels (`data/gold/pilot_sheet.csv`).
  2. `roster.py --score-review --finalise`: if Ben confirms at least 43 of Jev's 50 admits, write `configs/roster_v1.csv`; then `--collect-roster` (roster, own and benchmark accounts, $5 cap).
  3. Pilot check: `classify --ids data/gold/pilot_sheet.csv --out data/processed/pilot_jev_labels.parquet`, then `evaluate --gold data/gold/pilot_labels.csv --labels …`.
  3. Add `framing` and `poster_role` to the rubric and the Jev call; extend `experiments.py` to E1, E2, E3 and E5.
- **Harness:** `src/analysis/experiments.py` runs E4 and E6; dry runs on v0 (2026-11-12) passed as code checks. v0 gives 0–1 within-author strata for E4, so the real run needs the roster.

## Hypotheses

| ID | Status | Test | Latest evidence |
|---|---|---|---|
| H1 | untested | [E1](40_experiments/E1_poster_role.md) | Feasibility: the 200-paper panel has 12 papers with 3 or more posters and 6 with an author post plus another poster; the within-paper gate needs 20. Design question in pre-run review round 3. |
| H2 | untested | [E2](40_experiments/E2_paper_matched_levers.md) | Feasibility: 12 of 200 panel papers have 3 or more posters; matched figure-vs-summary pairs on 20 papers look out of reach. Design question in round 3. |
| H3 | untested | [E3](40_experiments/E3_decision_model.md) | None. |
| H4 | untested | [E4](40_experiments/E4_framing.md) | None. v0 had no curiosity-gap phrase among 122 researcher posts; H4c may be `insufficient`. |

- **H1 (Poster Tier — Reach vs. Intent Split):** Hype explainers generate higher raw impressions and likes than paper authors or neutral curators, whereas paper authors and neutral curators achieve a higher High-Intent Score (bookmarks, quotes, and technical replies) per impression.
  - Measured as: within-paper impressions ratio (H1a) and within-paper `S_intent` rate ratios, original researcher vs non-researcher (H1b-O) and credentialed researcher vs non-researcher (H1b-C). "Poster tier" is [poster role](30_concepts/poster_role.md): original researcher, credentialed researcher, or neither. "Technical replies" is dropped; replies are counted as they are ([intent measures](30_concepts/intent_measures.md)).
- **H2 (Controllable Levers on Identical Papers):** Holding the underlying arXiv paper constant across multiple posters, posts pairing a concrete empirical artifact (benchmark table or architecture figure) with a contested-claim hook achieve a higher High-Intent Score than plain-text abstract summaries.
  - Measured as: `S_intent` rate ratio, stratified by paper, `PAPER_FIGURE` + `CONTESTED_CLAIM` vs plain-text summary, on filter-passing [paper panel](30_concepts/paper_panel.md) posts.
- **H3 (Decision Model Feasibility):** Even after normalizing for poster follower count, poster tier, and author prestige, controllable post features (paper substance, visual type, and copy framing) retain enough predictive signal to classify above-median post performance.
  - Measured as: ΔAUC of a logistic model with controllable features over a controls-only model, folds grouped by author; supported at ΔAUC ≥ 0.03 with AUC ≥ 0.60.
- **H4 (Linguistic Framing & Interaction Type):** Posts using open-ended technical questions generate a higher reply rate than declarative summaries, whereas declarative empirical claims generate a higher bookmark-to-like ratio—and generic curiosity-gap phrasing (e.g., "Do you know...") fails to lift high-intent researcher saves.
  - Measured as: within-author rate ratios for replies per view on non-thread posts (H4a), bookmarks per like (H4b), and `CR_bmk` for curiosity gap vs empirical claim, with a null prediction (H4c). Classes defined in [framing](30_concepts/framing.md).

## Open questions

- When a post about a paper spreads, what exact share of variance is attributable to each of the 5 factors (paper content, paper authors, posting account tier, post visual, and post language/copy)? → [E5](40_experiments/E5_variance_shares.md)
- Which specific linguistic patterns (e.g., direct questions, "do you know" hooks, first-person vs. third-person framing) separate high-reply posts from high-bookmark posts within the researcher audience? → [E6](40_experiments/E6_reply_vs_bookmark_language.md)
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
| D7 | 2026-11-14 | Cap new Apify spend at $10, enforced in code. | accepted | plan decision 33; AGENTS.md §5 |
| D8 | 2026-11-14 | Audience-filter target: Cohen's kappa at least 0.8 on `is_researcher_post`. | accepted | plan decision 34 |
| D15 | 2026-11-14 | Pre-run review round 6: own and benchmark timelines join the roster run under its $5 cap; Jev's admissions hold up if Ben confirms at least 85% of its admits. Pre-run review complete. | accepted | plan decisions 57–58 |
| D14 | 2026-11-14 | Pre-run review round 5: one-week top-up for the other 112 borderline accounts ($0.30); the eight hand-picked accounts join the roster, flagged; roster timelines newest month first with a $5 cap. | accepted | plan decisions 54–56 |
| D13 | 2026-11-14 | Pre-run review round 4: E1 cross-paper gate needs 5 strata; borderline candidates get a month of posts and a re-judgment ($0.50 cap); tier quotas become caps of 150; organisations left out of the roster. | accepted | plan decisions 50–53 |
| D12 | 2026-11-14 | Pre-run review round 3: E1 cross-paper (tier × category strata); E2 stays within-paper, else H2 untestable and its lever goes to the posting experiment; panel stops, reserve $2.81; own-paper search as candidate source ($1.00); admission on bio plus posts in hand, run before the pilot; ingestion drops filler. | accepted | plan decisions 43–49 |
| D11 | 2026-11-14 | Pre-run review round 2: panel seeds from Hugging Face daily papers (random draw); roster candidates from panel posters and own-paper posters; Jev labels no new data before the pilot check; panel shares the roster's window. | accepted | plan decisions 39–42 |
| D10 | 2026-11-14 | Pre-run review round 1: $10 counts new spend only; $0.50 test batch first; 90-day window, no replies, 450 authors; pilot labels kept apart from the 200; `@wandb` replaces `@weights_biases`; E1–E4 judgment calls approved. | accepted | plan decisions 35–38 |
| D9 | 2026-11-14 | Embedding map (UMAP and t-SNE of posts) kept for after V0, as a hypothesis generator only. | accepted | plan, After V0 |
