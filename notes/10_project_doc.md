# Project doc

Living doc: the current state of the research. It is rewritten in place to stay true. The history is in [00_daily_log/](00_daily_log/), every run is in the ledger [40_experiments/results.tsv](40_experiments/results.tsv), and the way to keep this file is in [README.md](README.md).
The method rules and milestone status live in [docs/implementation-plan.md](../docs/implementation-plan.md).

## Current state

As of 2026-11-17 (late).

- **Phase:** Milestones 1 and 2 complete; Milestone 3 blocked on `JEV_TOKEN` `HTTP 401` (`authentication_error` from `api.typesafe.ai`) before full Jev rubric v2 labelling (`8,660` eligible posts). All `v1` data, baselines, Decision 45 panel expansion, arXiv metadata, and Semantic Scholar metadata are in place (`$6.8684` of `$10.00` Apify spend). No hypothesis has been tested on v1 data yet.
- **Method settled:** plan decisions 27–34 and 59–61 (`configs/roster_v1.csv` trusted directly without manual admission review; manual post hand-labelling waived in favor of Jev rubric v2 while keeping statistical cell gates; H5 and `E7` added). `E1`–`E7` stay `draft` until Jev labels allow outcome-blind feasibility counts and pre-registration freeze.
- **Budget:** `$6.8684` spent of `$10.00` Apify cap (`data/apify_spend.csv`), including `$4.9744` of the `$5.00` roster cap and `$0.9768` of the `$1.50` panel cap.
- **Collection & Baselines (Milestones 1–2):** `ROSTER` + `OWN` + `BENCHMARK` collected across Month 1 (`2026-10-08..11-07`: 206/206 accounts, 2,652 posts), Month 2 (`2026-09-08..10-08`: 206/206 accounts, 2,740 posts), and Month 3 (`2026-08-09..09-08`: 97/206 accounts, 2,137 posts before `$5.00` cap). Decision 45 added `115` multi-roster-poster papers (`315` seeds total; `78` with `>=3` posters, `40` with author + another poster). Ingestion (`mvp.py`, `v1-2026-11-17`) loaded `8,660` eligible mature posts (`1,780` filler dropped, `2,870` `in_author_cap`) across `407` authors into `data/processed/posts_enriched.parquet`; `ROSTER` reach model is reliable (`slope=0.59, intercept=1.84` on `8,315` posts / `192` authors); `10/10` spot-checked posts matched raw JSONL.
- **Paper Metadata (Milestone 3 prep):** `2,711` arXiv rows (`data/processed/panel_papers.csv`) and `2,630` Semantic Scholar rows (`data/processed/paper_s2_meta.csv`: `348` venue-accepted, `2,612` with author h-index) fetched and cached.
- **Blocking the runs:** `JEV_TOKEN` in `.env` returned `HTTP 401: authentication_error` on a 5-post `classify.py` smoke test (`cf3607061e63`). Needs a valid/refreshed `JEV_TOKEN` from Ben.
- **Next:**
  1. Ben refreshes `JEV_TOKEN` in `.env`.
  2. Run `uv run python -m src.enrichment.classify --model jev-latest --workers 6` on all `8,660` eligible posts.
  3. Compute outcome-blind feasibility counts, freeze `E1`–`E4` & `E7`, run `E1`–`E7` into `notes/40_experiments/results.tsv`, and build `swipe_file.csv`, `findings.md` (`--trust-jev`), and `overview.html`.
- **Harness:** `src/analysis/experiments.py` implements `E1`–`E7`; `91/91` unit tests and `ruff check` pass.

## Hypotheses

| ID | Status | Test | Latest evidence |
|---|---|---|---|
| H1 | untested | [E1](40_experiments/E1_poster_role.md) | Expanded 315-paper panel has `78` papers with `>=3` posters and `40` with an author post plus another poster (`33` in the `>=3`-poster set), clearing both cross-paper and within-paper panel thresholds pending Jev `poster_role` labels. |
| H2 | untested | [E2](40_experiments/E2_paper_matched_levers.md) | Expanded 315-paper panel has `78` papers with `>=3` posters; figure+contested-claim vs summary counts wait on Jev rubric v2 labels. |
| H3 | untested | [E3](40_experiments/E3_decision_model.md) | None. |
| H4 | untested | [E4](40_experiments/E4_framing.md) | None. v0 had no curiosity-gap phrase among 122 researcher posts; H4c may be `insufficient`. |
| H5 | untested | [E7](40_experiments/E7_small_account_breakout.md) | None. |

- **H1 (Poster Tier — Reach vs. Intent Split):** Hype explainers generate higher raw impressions and likes than paper authors or neutral curators, whereas paper authors and neutral curators achieve a higher High-Intent Score (bookmarks, quotes, and technical replies) per impression.
  - Measured as: within-paper impressions ratio (H1a) and within-paper `S_intent` rate ratios, original researcher vs non-researcher (H1b-O) and credentialed researcher vs non-researcher (H1b-C). "Poster tier" is [poster role](30_concepts/poster_role.md): original researcher, credentialed researcher, or neither. "Technical replies" is dropped; replies are counted as they are ([intent measures](30_concepts/intent_measures.md)).
- **H2 (Controllable Levers on Identical Papers):** Holding the underlying arXiv paper constant across multiple posters, posts pairing a concrete empirical artifact (benchmark table or architecture figure) with a contested-claim hook achieve a higher High-Intent Score than plain-text abstract summaries.
  - Measured as: `S_intent` rate ratio, stratified by paper, `PAPER_FIGURE` + `CONTESTED_CLAIM` vs plain-text summary, on filter-passing [paper panel](30_concepts/paper_panel.md) posts.
- **H3 (Decision Model Feasibility):** Even after normalizing for poster follower count, poster tier, and author prestige, controllable post features (paper substance, visual type, and copy framing) retain enough predictive signal to classify above-median post performance.
  - Measured as: ΔAUC of a logistic model with controllable features over a controls-only model, folds grouped by author; supported at ΔAUC ≥ 0.03 with AUC ≥ 0.60.
- **H4 (Linguistic Framing & Interaction Type):** Posts using open-ended technical questions generate a higher reply rate than declarative summaries, whereas declarative empirical claims generate a higher bookmark-to-like ratio—and generic curiosity-gap phrasing (e.g., "Do you know...") fails to lift high-intent researcher saves.
  - Measured as: within-author rate ratios for replies per view on non-thread posts (H4a), bookmarks per like (H4b), and `CR_bmk` for curiosity gap vs empirical claim, with a null prediction (H4c). Classes defined in [framing](30_concepts/framing.md).
- **H5 (Small-Account Breakout vs. Polarization):** Among low-follower accounts (<2,500 followers) with >=200 impressions, high-residual breakout posts that pair a concrete empirical artifact (table/figure) with a contested claim maintain a low Quote-to-Retweet ratio and high Bookmark-to-Like ratio, whereas ungrounded hot takes exhibit high Quote-to-Retweet polarization and near-zero bookmarks.
  - Measured as: stratified rate ratios across `<2,500` follower sub-tiers (`<500`, `500-999`, `1000-2499`) on breakout posts (`impressions >= 200`, `reach_vs_expected > 1.0`): Quote-to-Retweet ratio `U` vs `G` (H5a), Bookmark-to-Like ratio `G` vs `U` (H5b), and `CR_bmk` `G` vs `U` (H5c, alongside `U` zero-bookmark share), where `G` = `PAPER_FIGURE` + `CONTESTED_CLAIM` and `U` = ungrounded hot takes (`HOT_TAKE_CULTURE` or `CONTESTED_CLAIM`, `NONE` or `OTHER_IMAGE`, `technical_rigor_score <= 2`).

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
| D18 | 2026-11-17 | Add H5 and experiment E7 on `<2,500`-follower breakout posts across 3 sub-tiers (`min_strata=2`). | accepted | plan decision 61; `E7_small_account_breakout.md` |
| D17 | 2026-11-17 | Manual post hand-labelling (40-post pilot and 200/100-post held-out validation) waived; trust Jev rubric v2 (`jev-latest`) directly while keeping statistical gates. | accepted | plan decision 60; AGENTS.md §2.4 |
| D16 | 2026-11-17 | Manual 75-candidate admission review waived; `configs/roster_v1.csv` finalised directly from Jev's draft via `roster.py --finalise --trust-jev`. | accepted | plan decision 59; AGENTS.md §4 |
| D15 | 2026-11-14 | Pre-run review round 6: own and benchmark timelines join the roster run under its $5 cap; Jev's admissions hold up if Ben confirms at least 85% of its admits. Pre-run review complete. | accepted | plan decisions 57–58 |
| D14 | 2026-11-14 | Pre-run review round 5: one-week top-up for the other 112 borderline accounts ($0.30); the eight hand-picked accounts join the roster, flagged; roster timelines newest month first with a $5 cap. | accepted | plan decisions 54–56 |
| D13 | 2026-11-14 | Pre-run review round 4: E1 cross-paper gate needs 5 strata; borderline candidates get a month of posts and a re-judgment ($0.50 cap); tier quotas become caps of 150; organisations left out of the roster. | accepted | plan decisions 50–53 |
| D12 | 2026-11-14 | Pre-run review round 3: E1 cross-paper (tier × category strata); E2 stays within-paper, else H2 untestable and its lever goes to the posting experiment; panel stops, reserve $2.81; own-paper search as candidate source ($1.00); admission on bio plus posts in hand, run before the pilot; ingestion drops filler. | accepted | plan decisions 43–49 |
| D11 | 2026-11-14 | Pre-run review round 2: panel seeds from Hugging Face daily papers (random draw); roster candidates from panel posters and own-paper posters; Jev labels no new data before the pilot check; panel shares the roster's window. | accepted | plan decisions 39–42 |
| D10 | 2026-11-14 | Pre-run review round 1: $10 counts new spend only; $0.50 test batch first; 90-day window, no replies, 450 authors; pilot labels kept apart from the 200; `@wandb` replaces `@weights_biases`; E1–E4 judgment calls approved. | accepted | plan decisions 35–38 |
| D9 | 2026-11-14 | Embedding map (UMAP and t-SNE of posts) kept for after V0, as a hypothesis generator only. | accepted | plan, After V0 |
