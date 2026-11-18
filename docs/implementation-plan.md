# Implementation Plan: Tiptree X Post Analytics

Revised 2026-11-12 (revision 3), after a review of the plan against the first full data run.

Changes in revision 3:

- Keyword discovery is replaced by a curated handle list of about 450 researcher accounts and their full timelines. The v0 discovery sample was selected on outcome (see "What the v0 data run showed").
- The researcher filter judges only who a post is written for, not its rigor or register.
- Posts are ranked by bookmark rate, not by reach. Reach is a minimum bar, measured against the author's own median.
- The hand-labelled set is 200 posts, and no lift or recommendation is produced until the agreement targets are met.
- A posting experiment on Tiptree's own accounts is added as milestone 5. The Streamlit dashboard is postponed until after it.
- AGENTS.md is updated in the same change, so the two documents agree.
- `notes/` becomes the research log, and tests E1–E6 for the hypotheses in `notes/10_project_doc.md` are drafted there. The method changes they need are decisions 28–32.

## Milestone status

| # | Milestone | Status |
|---|---|---|
| 0 | Scaffold | Done |
| 1 | Handle list and collection | Done. Test batch, 200-paper panel, own-paper search, Jev admission, two borderline top-ups, and 200-account `configs/roster_v1.csv` (`--trust-jev`, decision 59) done; `ROSTER` + `OWN` + `BENCHMARK` collected (`2026-10-08..11-07` 206/206 accounts, `2026-09-08..10-08` 206/206, `2026-08-09..09-08` 97/206 at `$4.9744` cap; `7,529` posts kept); Decision 45 panel expansion collected `115` multi-roster-poster papers (`315` seeds total, `78` papers with `>=3` posters, `40` with an author + another poster, `$0.9768` total panel spend; `$6.8684` total Apify spend of `$10.00`); `v0` raw files archived to `data/raw/_v0/`; 10/10 ingested posts spot-checked against raw JSONL. |
| 2 | Baselines | Done. `8,660` eligible mature posts (`1,780` filler dropped, `2,870` `in_author_cap`) in `data/processed/posts_enriched.parquet`; `ROSTER` reach model reliable (`slope=0.59, intercept=1.84` on `8,315` posts / `192` authors); `7,811` posts with trailing-30-day baselines; `outputs/reports/mvp-findings.md` and `outputs/reports/baselines-sanity.md` regenerated without stale text. |
| 3 | Labels v2 | Done. Audience-only rubric, `framing`, `poster_role` + S2 lookup wired (`src/enrichment/classify.py`, `s2.py`, `judge.py`), `2,711` arXiv and `2,630` S2 paper records cached, and all `8,660` eligible mature v1 posts classified with `jev-latest` (`label_version=cf3607061e63`, `role_version=55945d80ebf0`, `0` failures). Manual pilot & held-out hand-labelling waived under decision 60. |
| 4 | Analysis | Done. `E1`–`E4` & `E7` pre-registered and frozen (`869a795`), `E1`–`E7` executed on `v1-2026-11-17` into `notes/40_experiments/results.tsv` (all negative controls passed; `H1` refuted on `H1a`, `H2` `insufficient` per decision 44, `H3`/`H4`/`H5` `inconclusive`; `E5` and `E6` completed); `254` swipe-file posts written to `data/swipe_file/swipe_file.csv`; `outputs/reports/findings.md` generated via `report.py --trust-jev` (`<2k` `PAPER_FIGURE` `1.81x` recommendation + template). |
| 5 | Posting experiment | Not started. Ready for Martin's agreement and cadence execution. |
| 6 | Static overview | Done. `outputs/reports/overview.html` generated on all `8,660` v1 posts alongside `254`-row swipe file, `<2k` scorecard (`@tiptreesystems`, `@martincsweiss1`), and cross-link to the exploratory `outputs/reports/embedding_map.html` (Decision D9). Dashboard postponed. |
| 7 | Weekly refresh (optional) | Not started. |

## Decisions

Revision 2 (2026-11-10):

| # | Decision | Answer |
|---|---|---|
| 1 | Classifier | Jev, TypeSafe AI's "System One" model (https://typesafe.ai/blog/introducing-system-one-models-and-jev), model `jev-latest` |
| 2 | Apify actor | `apidojo/tweet-scraper` (https://apify.com/apidojo/tweet-scraper) |
| 3 | Hand-labeller | Ben |
| 4 | Enum additions `OTHER` and `OTHER_IMAGE` | Approved |
| 5 | Signup data | Not available. UTM links on experiment posts are the only bridge to signups. |

Revision 3 (2026-11-12):

| # | Area | Decision |
|---|---|---|
| 6 | Metric | Rank posts by `CR_bmk` within follower tier. Reach is a minimum bar, not the ranking. |
| 7 | Metric | The reach bar is `baseline_ratio` ≥ 1: the post beats its author's trailing-30-day median views. `reach_vs_expected` only describes tiers. |
| 8 | Metric | Lift tables use pooled rates (total bookmarks / total views per cell) with author-clustered bootstrap intervals. Single posts use a rate shrunk toward the tier rate. |
| 9 | Metric | At most 40 eligible posts per author enter the analysis, sampled evenly across the window. All raw posts are kept. |
| 10 | Corpus | Replace keyword discovery with a handle list of about 450 researcher accounts and their full timelines. |
| 11 | Corpus | Handle sources: the 92 authors who pass the v1 filter in v0 data, public X lists of ML researchers, and accounts that post their own arXiv papers. |
| 12 | Corpus | Jev admits a candidate after reading their bio and 5 recent posts. Ben reviews 50 admitted and 25 rejected candidates before collection. |
| 13 | Corpus | ~~Tier quotas: 150 under 2k followers, 150 at 2k–20k, 100 at 20k–200k, 50 over 200k.~~ Superseded by decision 52 (caps of 150 per tier). |
| 14 | Corpus | The five people in AGENTS.md's benchmark list join the handle list. The organisations `@elicitorg`, `@huggingface`, `@arxiv` and `@wandb` (was `@weights_biases`, see decision 37) stay as `BENCHMARK`. `@PapersWithCode` and `@OpenReviewNET` are dropped as dormant. |
| 15 | Collection | Stay on Apify. Monthly windows, several authors per query joined with `OR`, 50–90 expected posts per query; a query that returns 100 is split and rerun. Fallback: the official X API. |
| 16 | Collection | ~~Keep replies (about $28 in total instead of $10), so threads are rebuilt from real self-replies.~~ Superseded by decision 36. |
| 17 | Collection | Own and benchmark timelines are collected again with the new method. Old raw files move to `data/raw/_v0/`, unedited. |
| 18 | Labels | The researcher filter judges only the intended reader (definition below). Rigor and register are left to `technical_rigor_score` and `hook_archetype`. |
| 19 | Labels | No lift table or recommendation is produced until the held-out agreement targets are met. |
| 20 | Labels | Hand-labelled set: 200 posts from the new corpus, 50 per tier, labelled blind to Jev, 100 tuning and 100 held out. |
| 21 | Labels | Ben writes a short note on every post he labels `OTHER` in the tuning half. The enums are revised once from those notes before the held-out half is labelled. |
| 22 | Outputs | Findings, lift tables and the swipe file use only posts that pass the audience filter. The full corpus appears only in the coverage table. |
| 23 | Outputs | No fixed template count. A template exists only where a lift row passed the evidence gate. |
| 24 | Outputs | The Streamlit dashboard is postponed until after the experiment; the static overview is extended instead. |
| 25 | Experiment | Martin posts about 3 times a week across both own accounts until 20 posts per arm (about three months). A coin flip assigns each slot. One arm uses Lacuna maps. Every link carries a UTM tag. |
| 26 | Docs | This plan carries a milestone status table updated at the end of each milestone. AGENTS.md is updated in the same change as the plan. |
| 27 | Docs | `notes/` is the research log: a daily log, a project doc kept current, one file per experiment and a run ledger (`notes/40_experiments/results.tsv`). Hypothesis tests are pre-registered and committed before they run on real data. Protocol in `notes/README.md`. |
| 28 | Metric | "High-Intent Score" in H1 and H2 is `S_intent` as defined in this plan and AGENTS.md (primary), with `CR_bmk` secondary; "technical replies" is dropped and replies are counted as they are. Reply rate, bookmarks per like and `top_half` (AGENTS.md §3) are descriptive measures for the hypothesis tests; ranking stays on `CR_bmk`. Verdicts use 99% intervals and a smallest effect worth acting on of 1.2× (`notes/40_experiments/README.md`). |
| 29 | Corpus | A paper panel: about 200 arXiv papers (300 before decision 36) drawn at random from those that roster posts link, with every post that links them. Posts from accounts outside the roster get cohort `PANEL`; every paper-linked post gets `paper_id`. About 3,000 posts, about $1.50. Design in `notes/30_concepts/paper_panel.md`. |
| 30 | Labels | Two new labels, each with a Cohen's kappa target of 0.7: `framing` on every post, as a fifth field of the 200-post hand-label set, and `poster_role` (H1's "poster tier": `ORIGINAL_RESEARCHER`, `CREDENTIALED_RESEARCHER`, `NON_RESEARCHER`) on paper-linked posts, checked on 100 separate paper-linked posts. Definitions in `notes/30_concepts/`. |
| 31 | Outputs | E1 uses paper-linked posts whether or not they pass the researcher filter, because non-researchers write for the general public. This is the one exception to decision 22, and E1 produces no templates. |
| 32 | Stack | scikit-learn joins the dependencies (E3, E5). Paper metadata comes from the arXiv and Semantic Scholar APIs (free, rate-limited). |

Revision 3 addendum (2026-11-14):

| # | Area | Decision |
|---|---|---|
| 33 | Collection | New Apify spend is capped at $10 from 2026-11-14 (`APIFY_BUDGET_USD` in `src/config.py`). `src/ingestion/apify.py` refuses any run whose worst case (every query returning `max_items`) would pass the cap, sends a server-side `maxItems` limit, and appends every run to `data/apify_spend.csv` at the listed $0.40 per 1,000 posts. The estimates above ($28 roster, $2 panel) exceeded the cap; decision 36 fits collection to it. |
| 34 | Labels | Item H settled: the audience-filter target is Cohen's kappa at least 0.8 on `is_researcher_post`, on the held-out half. |
| 35 | Collection | A test batch of new data comes first, capped at $0.50: it checks `OR` joins (item E), older weeks (item F), the panel's `url:` search and the item G seed accounts before any roster spend. Work that costs nothing (pilot labels, Jev rubric v2, the harness) uses v0. Pilot labels test the guide only and do not count toward the 200-post set. |
| 36 | Collection | Fitting the cap (item N): a 90-day window ending 7 days before collection; replies dropped with `-filter:replies` (reverses decision 16); 450 authors and the tier quotas kept. Allocation: test batch $0.50, admission posts $1.50, roster about $5 (450 × 13 weeks × about 2 originals a week ≈ 12k posts), paper panel $1.50 (200 papers), reserve $1.50. Thread length comes from text cues, and H4a's reply rate leaves out thread openers. |
| 37 | Corpus | `@weights_biases` is a fan account (607 followers); the `BENCHMARK` organisation is `@wandb`. `src/config.py` follows decision 14: the five curators are roster seeds, `@PapersWithCode` and `@OpenReviewNET` are gone. |
| 38 | Experiments | The judgment calls in E1–E4 are approved as written: 99% intervals, 1.2× smallest effect, E3's ΔAUC ≥ 0.03 with AUC ≥ 0.60, and the 3-paper credential rule. Each experiment is frozen once its feasibility counts are in. |
| 39 | Corpus | Item O settled: panel seeds are drawn uniformly at random (not by upvotes) from Hugging Face daily papers listed 2026-08-09 to 2026-10-07; once the roster is in, papers with at least 2 roster posters are added. Results describe papers that drew community attention. |
| 40 | Corpus | Roster candidates come from accounts posting in the paper panel and from a search for accounts posting their own papers ("our paper" with an arXiv link), plus X lists if Ben supplies List URLs. Amends decision 11. |
| 41 | Labels | Jev labels no new data until Ben's 40 pilot labels are in and rubric v2 (audience-only researcher question, `framing`, `poster_role`) has been checked against them. The formal targets still come from the 200-post set. |
| 42 | Corpus | The panel shares the roster's window: papers listed 2026-08-09 to 2026-10-07, each paper's posts collected for 30 days from its arXiv date, ending 2026-11-07. |
| 43 | Experiments | E1's primary test compares poster roles across all paper-linked posts (roster and panel), with strata of follower tier × arXiv primary category; the within-paper comparison becomes secondary. The write-up says the paper is not held constant. |
| 44 | Experiments | E2 stays within-paper. If its gate fails, H2 is reported as untestable from X search data at this budget, and the figure-plus-contested-claim format enters the posting experiment as an untested arm. |
| 45 | Collection | Panel collection stops at 200 papers ($0.188). The unspent $1.31 of its share joins the reserve, now $2.81. Papers with at least 2 roster posters are added only if the roster has at least 20 of them. |
| 46 | Corpus | The main candidate source is a search for own-paper posts: `("our paper" OR "our new paper" OR "we introduce") url:arxiv.org`, in short date slices over the 90 days, capped at 2,500 posts ($1.00). X lists only if Ben supplies List URLs. |
| 47 | Corpus | Jev admits a candidate on the bio plus the posts already in hand (at least 1, up to 3), amending decision 12. Ben's 75-candidate review checks it; if the error rate is high, recent posts for borderline candidates come from the reserve. |
| 48 | Labels | Jev admission runs before the pilot labels are in. Decision 41's gate applies to post labels only. |
| 49 | Collection | Ingestion drops filler: items outside their query's date window, or not matching its `from:`, `url:` or phrase terms, or replies and reposts when the query excluded them. Each run's query is stored next to its raw file. Dropped counts appear in the coverage table. |
| 50 | Experiments | E1's cross-paper tests need 5 contributing strata instead of 20 (tier × category has about 30 cells); 20 posts and 10 authors per arm still apply. The README gate is unchanged for every other test. |
| 51 | Corpus | The 140 borderline candidates get one month of recent posts (2026-10-07 to 11-07, author queries grouped to expect at least 50 posts, capped at $0.50 from the reserve), and Jev re-judges them on up to 3 posts. |
| 52 | Corpus | Tier quotas (decision 13) are replaced by caps: every admitted account enters, at most 150 per tier, sampled at random above that. Tier sizes are reported with every finding. |
| 53 | Corpus | Accounts Jev rates as organisations (`p_org` ≥ 0.7) are left out of the roster, unless Ben's review notes say labs belong. Lab accounts still count in E1 through the paper data. |
| 54 | Corpus | The other 112 borderline accounts get one week of posts (2026-10-31 to 11-07, cap $0.30 from the reserve) instead of a month, and Jev re-judges them. Reason: they post about 4.4 times a week, so a week gives the 3 posts admission needs. |
| 55 | Corpus | The eight hand-picked accounts (the five curators of decision 14 and the three item G seeds) join the roster whatever Jev decided, flagged `hand_picked` so a sensitivity check can drop them. Their posts still pass the per-post researcher filter. |
| 56 | Collection | Roster timelines are collected newest month first, with their own cap of $5; if the cap is reached the oldest weeks are lost, not whole accounts, and the window actually covered is reported. Collection still waits on Ben's admission review (decision 12). |
| 57 | Collection | The own and benchmark timelines (`@tiptreesystems`, `@martincsweiss1`, `@elicitorg`, `@huggingface`, `@arxiv`, `@wandb`; decision 17) are collected in the same run as the roster, under its $5 cap. |
| 58 | Corpus | Jev's admissions hold up if Ben says yes to at least 85% of the 50 Jev admitted in the review (43 or more). Below that, the admission questions are revised and rerun before anything is collected. `roster.py --collect-roster` checks this. |
| 59 | Corpus | Ben reviewed Jev's admission output and waived the 75-candidate manual admission review (`data/gold/admission_review_done.csv`, amending decisions 12 and 58). `configs/roster_v1.csv` is finalised directly from `roster_draft.csv` via `roster.py --finalise --trust-jev`, and `--collect-roster` proceeds once `configs/roster_v1.csv` exists. |
| 60 | Labels | Ben waived Milestone 3 manual post hand-labelling (the 40-post pilot check and the 200-post / 100-post held-out human kappa gates, amending decisions 19, 20, 30, 34, and 41), trusting Jev rubric v2 (`jev-latest`) directly for V0 while keeping all statistical evidence gates (`>=20` posts, `>=10` authors, strata minimums, 99% intervals) in force. |
| 61 | Experiments | Add H5 and experiment `E7` on `<2,500`-follower breakout posts (`impressions >= 200`, `reach_vs_expected > 1.0`), comparing grounded figure+contested-claim posts (`G`) vs ungrounded hot takes (`U`) across 3 follower sub-tiers (`<500`, `500-999`, `1000-2499`) with `min_strata = 2`, `MIN_POSTS = 20`, `MIN_AUTHORS = 10`, and 99% author-clustered bootstrap intervals. |

## Still open

| # | Item | Needed by |
|---|---|---|
| G | **Which X lists.** `@junli_r84995`, `@sippeyxp` and `@qiayuanliao` join the candidate pool as seeds (2026-11-14). Still needed: the List URLs (`x.com/i/lists/<id>`) of any public ML-researcher lists they own, or 3–5 other lists; the current pool is far short of 450. | Milestone 1 |
Resolved: impressions are present (`viewCount`); Jev access and image support (1.13 and later accept PNG/JPEG); Apify paid plan. Items I–M (hypothesis-test measures, paper panel, new labels, E1 scope, new inputs) became decisions 28–32 on 2026-11-12. Item H became decision 34 and item N decision 36 on 2026-11-14. Items E and F were settled by the test batch the same day (below), and item O became decision 39.

## What the v0 data run showed

The first full collection (2026-11-11) loaded 2,073 posts. Three findings shaped this revision:

- **Discovery was selected on outcome.** Six 30-day search slices each stopped at 220 posts (with `maxItems` 500), and each slice's posts were spread across its 30 days. A "Latest" search on terms this common would have returned only the last hours of each slice. The median discovered post had 1,430 likes and 98k views. Only 88 of 1,224 labelled discovered posts passed the researcher filter: "ACL" matched knee injuries and "benchmark" matched markets.
- **Timelines have a per-query cap.** Four timelines stopped at exactly 100 posts (with `maxItems` 300). A one-week test of `@_akhaliq` on 2026-11-12 returned the same 7 posts the six-month pull had for that week, so recent weeks are complete. Older weeks are item F.
- **Tiptree's own accounts are small.** `@tiptreesystems` has 67 followers and `@martincsweiss1` 214. Their 25 eligible posts in six months have a median of 215 views, and 9 have any bookmark.

The one-week test returned 7 posts, which breaks the actor's 50-posts-per-query rule. Verification queries from now on combine authors or months so they expect at least 50 posts.

## What the test batch showed (2026-11-14)

Four one-query runs (decision 35), stored in `data/raw/_test_2026-11-14/`, checked by `scripts/test_batch.py`.

- **Cost.** 135 posts, $0.054. Apify's per-run bill matches `data/apify_spend.csv` to the cent, and runs under 50 posts carried no minimum charge.
- **Item E, `OR` joins: pass.** `(from:a OR … from:f)` over 2026-10-01 to 11-06 returned 68 posts from all six authors and none from anyone else. `-filter:replies` and `-filter:retweets` held (0 replies, 0 reposts); every post had views and bookmarks. The six authors averaged about 2 posts a week, which keeps the roster near the $5 estimate.
- **Item F, older weeks: v0 lost most of them.** For 2026-06-01 to 06-14, `@maximelabonne` and `@_akhaliq` had 31 original posts; the v0 timelines held 3. Monthly `OR`-batched queries recover what the per-timeline 100-post cap dropped.
- **Item G seeds.** All three are individual researchers: a PhD candidate at HKU MMLab visiting Berkeley (439 followers), a Gemini Robotics lead at DeepMind (1,335), a Berkeley PhD student (5,354). They join the roster candidates; they do not supply lists.
- **Paper panel `url:` search: works, but papers are thin.** The bare form `url:<id>` found 21 posts on 11 of 13 papers, all linking a queried paper (one through ModelScope, now recognised by `panel.arxiv_ids`). The quoted form `url:"arxiv.org/abs/<id>"` found 15 on 10, all also found by the bare form. Posters per paper: median 1, and 3 of 13 papers had 3 or more. Item O.
- **Maturity.** A query without `until` returned posts under 7 days old. Panel queries need `until` set 7 days back.
- **Quote posts are common.** 47 of the 68 posts in the `OR` run were quote posts, each carrying the quoted post. They are eligible; `post_kind` keeps them apart.

## What the paper panel showed (2026-11-14)

200 papers drawn at random from 1,411 on Hugging Face daily lists (decision 39), collected with `uv run python -m src.ingestion.panel --collect`: 10 runs, 467 items, $0.188.

- **Papers get few link posts.** 99 of 200 papers had any post linking them inside their 30-day window; 156 such posts in all. Posters per paper: median 0, mean 0.8, maximum 5. 12 papers had 3 or more posters, 1 had 5. Upvotes barely help (Spearman 0.27 with posters; the top quartile averages 1.2 posters, and the most upvoted paper, 207, had 4).
- **E1 and E2 gates are far off.** 17 posts by a paper author (display name matched to the arXiv author list) on 16 papers; 6 papers had an author post and another poster. Both experiments need at least 20 papers holding both arms.
- **The actor pads thin queries with unrelated posts, and charges for them.** 314 of the 467 items linked no seed paper: mostly posts from the day of collection, outside every query's date window, including 36 replies despite `-filter:replies`, and the same filler recurred across runs. Runs that matched few posts carried 16 to 62 filler items each. This is why the actor asks for at least 50 posts per query. The test batch's `from:` queries had none.
- **Candidate pool.** 71 distinct accounts posted about the seed papers: 40 under 2k, 25 at 2k–20k, 4 at 20k–200k, 2 over 200k.

## What candidate building showed (2026-11-14)

- **Own-paper search is small.** 22 four-day slices of `("our paper" OR "our new paper" OR "we introduce") url:arxiv.org lang:en` returned 331 items ($0.132), 5 to 26 per slice; the filler guard dropped 6; 264 distinct authors.
- **Candidate pool: 426.** Own-paper authors 261, v0 Jev-passing authors 73, panel posters 60, test-batch authors 18, seeds 8. By tier: 277 under 2k, 102 at 2k–20k, 38 at 20k–200k, 9 over 200k. 362 have one post in hand.
- **Admission (decision 47): 201 admit, 140 borderline, 85 reject**, no errors, about 340k Jev input tokens. Admitted by tier: 128, 49, 19 and 5, against quotas of 150, 150, 100 and 50. 131 of the 140 borderline candidates had one post in hand. 14 admitted accounts look like organisations (`p_org` ≥ 0.7).
- **Review.** `data/gold/admission_review.csv`: 50 admitted and 25 rejected, shuffled, Jev's decision kept in a separate key file.
- **Borderline top-up (decision 51) ran out early.** Borderline accounts post about 4.4 times a week (546 posts from 28 accounts in a month), not the 2 assumed, so the $0.50 covered 28 of 140 accounts (16 runs, 6 split at the cap, $0.461). Jev re-judged the 21 with new posts: 9 admitted, 12 still borderline on mixed posts.
- **Week top-up (decision 54) also ran short.** 11 runs, 5 split at the cap, $0.270: 61 accounts queried, only 19 had posts that week. Posting is heavy-tailed: a few accounts post dozens of times a week and fill the capped runs, most post rarely, so the 4.4 average misleads. Jev re-judged the 19: 4 admitted, 15 borderline. The two top-ups cost $0.73 and admitted 13; the other 127 borderline accounts stay out.
- **Draft roster (decisions 52, 53, 55): 200.** 130 under 2k, 48 at 2k–20k, 17 at 20k–200k, 5 over 200k, including the 8 hand-picked accounts (flagged `hand_picked`, outside the caps); admitted organisations left out. `data/processed/roster_draft.csv`, waiting on Ben's review. `src/ingestion/roster.py --collect-roster` refuses to run until `data/gold/admission_review_done.csv` exists.

## Corpus

Four cohorts, tagged in `cohort`:

| Cohort | Source | Purpose |
|---|---|---|
| `OWN` | Timelines of `@tiptreesystems` and `@martincsweiss1` | Scorecard for Tiptree's own posts, and the experiment |
| `ROSTER` | Timelines of about 450 researcher accounts, sampled to tier quotas | What works for researcher posts at every account size (replaces `DISCOVERED`) |
| `BENCHMARK` | Timelines of `@elicitorg`, `@huggingface`, `@arxiv`, `@wandb` | Comparison set for product posts from research-tool organisations |
| `PANEL` | Posts from accounts outside the roster that link a paper-panel paper (decision 29) | Same-paper comparisons for hypothesis tests E1, E2, E3 and E5 |

### Definition of a researcher post

> A post written for people who read or write ML research papers: faculty, PhD students, research scientists and research engineers, and practitioners sharing training or fine-tuning detail. Product posts aimed at these readers count, including Tiptree's own. Posts written for app developers, people shopping for AI tools, investors or the general public do not.

The filter judges the intended reader only. A rigorous post and a casual one can both pass; how rigorous a post is gets measured by `technical_rigor_score`, so the filter does not narrow the feature being studied.

### Building the handle list

1. **Candidates.** (Sources amended by decision 40.) The 92 authors who passed the v1 filter in v0 data (34 under 2k, 24 at 2k–20k, 26 at 20k–200k, 8 over 200k); members of 3–5 public X lists of ML researchers (item G; the actor accepts List URLs); accounts that post their own arXiv papers, found with phrases such as "our paper" plus `url:arxiv.org`. The v0 authors were found through one viral post, and search skews toward popular posts, so neither source is trusted for cross-author reach; the tier quotas offset the skew.
2. **Admission.** (Evidence amended by decision 47.) Jev reads each candidate's bio (`author.description`) and 5 recent posts and decides whether they write for ML researchers. Ben reviews 50 admitted and 25 rejected candidates (about 30 minutes) before collection; a high error rate means the admission question is revised and rerun.
3. **Sampling.** (Decision 52.) Every admitted account enters, at most 150 per tier, sampled at random above that; organisations are left out (decision 53). The five people from AGENTS.md's benchmark list are included in their tiers.

## Data source: Apify `apidojo/tweet-scraper`

What the actor page states:

- **Price:** $0.40 per 1,000 posts.
- **Input:** X advanced-search queries, handle lists, Tweet/Profile/Search/List URLs, `sort` of `Latest` or `Top`, `maxItems`.
- **Output:** `id`, `url`, `text`, `createdAt`, `viewCount`, `likeCount`, `retweetCount`, `replyCount`, `quoteCount`, `bookmarkCount`, `isReply`, `isQuote`, media; author `userName`, `followers`, `description`, `statusesCount`.
- **Rules:** every query must return at least 50 posts; one concurrent run with up to 5 queries; no repeated queries at short intervals; no single-post or conversation scraping; `customMapFunction` must not filter.

### Collection design

- One query covers one calendar month and joins several authors: `(from:a OR from:b ...) since:YYYY-MM-01 until:YYYY-MM-01 -filter:retweets -filter:replies`. Group sizes come from each author's posting rate in the candidate data and target 50–90 posts per query, between the actor's minimum and the observed 100-post cap.
- A query that returns exactly 100 posts is split into two half-month queries and rerun.
- Replies are dropped (decision 36). `thread_length` and thread openers come from text cues ("🧵", "1/").
- Window: 90 days, ending 7 days before collection so every post is mature. Estimated volume: 450 authors × 13 weeks × about 2 originals a week ≈ 12k posts ≈ $5.
- Paper panel: bare `url:<id>` queries (more recall than the quoted form in the test batch) for about 200 arXiv IDs, grouped so each expects at least 50 posts; about 3,000 posts, about $1.50. A first batch of 30 papers checks that `url:` matches arXiv IDs and counts posters per paper. Design in `notes/30_concepts/paper_panel.md`.
- The $0.50 test batch (decision 35) comes first and checks items E and F, the `url:` search and the seed accounts.

Risks specific to this route:

- **Terms of service.** X's terms prohibit scraping without consent. The official API returns the same public fields and stays available as a drop-in adapter.
- **Actors break or change output without notice.** Raw output is stored verbatim and the adapter maps field aliases, so a switch of actor only touches one module.
- **Filler on thin queries.** When a query matches few posts, the actor returns unrelated recent posts and charges for them (paper panel, 2026-11-14). Queries are grouped to expect at least 50 real posts, and ingestion drops items outside a query's window or terms.
- **No own-post click metrics.** URL and profile clicks exist only through the official API with account sign-in, and only for posts under 30 days old.

## Architecture

Data moves one way. Raw files are stored verbatim and never edited; everything downstream can be rebuilt from them. Superseded raw files move to `data/raw/_v0/`, which ingestion does not read.

```text
candidate sources ─► roster.py (Jev admission, quotas) ─► config handle list
                                                               │
Apify actor runs ─► data/raw/ ─► adapters ─► posts.parquet + account_snapshots.parquet
                                                 │
                       ┌─────────────────────────┼────────────────────────┐
                metrics + baselines        rule features          jev classifier (cached)
                       └─────────────────────────┼────────────────────────┘
                                       posts_enriched.parquet
                                                 │
                       lift tables ── swipe file ── findings + templates ── static overview
```

```text
src/
  schema.py        # Post, AccountSnapshot, PostLabels, enums: the single contract
  config.py        # handles, cohorts, tier quotas, window, thresholds
  ingestion/
    roster.py      # candidate search, pool, Jev admission runs, review sheet and gate, caps, collection
    admission.py   # admission questions and truth table (admit, reject, borderline)
    filler.py      # query sidecars and the filler guard (decision 49)
    apify.py       # the only module that talks to Apify; writes raw JSONL
    collect.py     # monthly OR-batched timeline queries, split on cap
    panel.py       # paper panel: seed IDs, url: queries, arXiv and Semantic Scholar metadata
    adapters.py    # raw actor JSON or export CSV -> Post, accepting field-name aliases
    load_raw.py    # CLI from AGENTS.md: validate, dedupe, write Parquet, add metrics
  metrics/
    formulas.py    # the AGENTS.md formulas as pure vectorised functions
    baselines.py   # maturity, trailing author medians, per-author cap, shrunk CR_bmk, reach fit
  enrichment/
    rules.py       # deterministic features and the hype lint
    rubric.py      # audience definition, archetype and rigor anchors, framing (rubric v2)
    poster_role.py # poster role request and truth table (decision 30)
    s2.py          # Semantic Scholar author paper count and paper venue/h-index lookup
    judge.py       # provider-neutral Judge interface, Jev implementation
    classify.py    # CLI from AGENTS.md: --model, resumable, cached by label version; --ids/--out for the pilot check
    label_sheet.py # stratified, blind hand-label sheet
    evaluate.py    # hand labels vs judge: agreement report
  analysis/
    lift.py        # pooled lifts, author-clustered bootstrap, evidence gate
    swipe.py       # swipe-file selection -> data/swipe_file/
    report.py      # findings and templates, generated from the lift tables
    experiments.py # E1–E7 entry points: stratified rate ratio, negative control, summary block
    charts.py      # static overview page
    embed_map.py   # multimodal UMAP + t-SNE post embedding map (After V0 / Decision D9)
    tweet_figure.py # 2-panel academic ablation figure -> outputs/reports/researcher_post_ablation.png
tests/  scripts/  configs/  notes/  outputs/reports/  docs/  data/{raw,processed,swipe_file,gold}/
```

Setup uses `uv` on Python 3.13 (`requires-python >= 3.11`). Secrets live in a git-ignored `.env`.

### Posts table

| Group | Columns |
|---|---|
| Identity | `post_id`, `author_handle`, `author_id`, `cohort`, `url`, `created_at`, `collected_at`, `source`, `paper_id` (arXiv ID, when the post links a paper) |
| Author | `followers_at_collection` (required), `follower_tier` |
| Content | `text`, `post_kind` (original, quote, thread opener), `thread_length`, `media`, `link_kinds` |
| Counts | `impressions`, `likes`, `replies`, `reposts`, `quotes`, `bookmarks` |
| Metrics | `r_out`, `s_intent`, `cr_bmk`, `cr_bmk_shrunk`, `baseline_ratio`, `reach_vs_expected`, `pctile_in_tier`, `in_author_cap` |
| Rule features | `has_media`, `media_kind`, `has_link`, `char_len`, `has_number`, `mentions_venue`, `has_arxiv_id`, `hype_flags`, `posted_hour_utc` |
| Labels | `is_researcher_post`, `hook_archetype`, `visual_type`, `technical_rigor_score`, `framing`, `poster_role`, `label_confidence`, `label_rationale`, `label_version` |

Side tables: `account_snapshots` (follower counts appended on every run), `labels` (classifier cache keyed by post and label version) and `roster` (candidate, source, admission decision, review label, tier).

A post without `followers_at_collection` is rejected at ingestion.

## Metrics and method

The three AGENTS.md formulas are implemented exactly, including the `max(followers, 100)` and `max(impressions, 1)` floors.

- **Ranking metric: `CR_bmk`**, compared within follower tier. Bookmarks are the clearest signal that a researcher wants to come back to a post.
- **Reach bar: `baseline_ratio`** = post views / the author's trailing-30-day median views over eligible posts. A post needs `baseline_ratio` ≥ 1 to enter the swipe file. Posts whose author has fewer than 3 eligible posts in the previous 30 days have no baseline; they stay out of the swipe file but count in lift tables.
- **Pooled rates for lifts.** A cell's bookmark rate is total bookmarks / total views × 1000, with a 95% interval from a bootstrap that resamples authors, not posts.
- **Shrunk rates for single posts.** `cr_bmk_shrunk` = (bookmarks + r) / (views + 1000) × 1000, where r is the tier's pooled bookmarks per 1k views. This treats each post as if it had 1,000 extra views at its tier's pooled rate. One bookmark on a 200-view post no longer outranks a large account's typical post.
- **Per-author cap.** At most 40 eligible posts per author enter the analysis, sampled evenly across the window (`in_author_cap`), so prolific authors do not dominate pooled rates.
- **`reach_vs_expected`** (log views on log followers) is refit on `ROSTER` posts and used only to describe tiers.
- **Follower tiers:** under 2k, 2k–20k, 20k–200k, over 200k. Advice for Tiptree comes from the under-2k tier first.
- **Eligible posts:** originals, quote posts and thread openers. Reposts and replies to other people are dropped.
- **Maturity:** a post is scored once it is 7 days old.
- **Follower counts are as of collection.** Each run appends a snapshot.
- **Minimum evidence:** a lift is reported only for at least 20 posts from at least 10 distinct authors (3 for within-author comparisons). Thinner cells show "insufficient data" and cannot produce a recommendation.

## Enrichment

- **Rules:** media kind, link type, length, numeric claims, venue and benchmark mentions, arXiv IDs, thread length, posting time, and a hype flag for listicle and clickbait patterns that doubles as a lint on generated text.
- **Classifier (Jev):** one call per post returns `is_researcher_post` (audience definition above), `hook_archetype`, `visual_type` for photos (Jev reads PNG/JPEG) and `technical_rigor_score`, each with its probability. Video is classified by rule. A second Jev question, on bio and 5 recent posts, admits authors to the handle list. The same per-post call also returns `framing`, and `poster_role` for posts that link a paper; `ORIGINAL_RESEARCHER` also comes from matching the display name against the arXiv author list, and `CREDENTIALED_RESEARCHER` from a Semantic Scholar publication record or a bio read (decision 30).
- **Rubric v2:** the audience-only definition, anchors for rigor scores 2–4, precedence rules for overlapping archetypes. A rubric change bumps `label_version` and relabels everything (cents).
- **Taxonomy revision.** In the v1 labels on 175 passing v0 posts, `OTHER` was 51% of archetypes and `OTHER_IMAGE` 41% of visual types; `LITERATURE_SYNTHESIS` had 0 posts and `VISUAL_MAP` 5. The most common researcher post, a paper announcement, had no archetype. Ben notes what each `OTHER` post in the tuning half is, and the enums are revised once from those notes before the held-out half (likely `PAPER_ANNOUNCEMENT`, `RESOURCE_SHARE` and a split of `OTHER_IMAGE`). `VISUAL_MAP` and `LACUNA_MAP` are kept for Tiptree's own posts; they will not reach the evidence gate in the corpus.
- **Validation:** 200 posts from the new corpus, 50 per tier, labelled by Ben on all four fields without seeing Jev's labels; 100 tuning and 100 held out. Targets on the held-out half: Cohen's kappa at least 0.7 for archetype and 0.8 for visual type, rigor within one point on 85% of posts, and Cohen's kappa at least 0.8 on `is_researcher_post` (decision 34). Classes with fewer than 10 held-out examples are reported but not held to the targets. `framing` is a fifth field on the same set. `poster_role` is checked on 100 separate paper-linked posts (about 33 per Jev class) plus 50 author-name matches. Both have a target of Cohen's kappa at least 0.7.
- **Gate:** no lift table, template or recommendation is produced from labels that have not met the targets.
- **Mechanics:** labels cached by post and `label_version` (hash of rubric and model). Failures recorded as unlabelled with a reason.

## Outputs

- **Swipe file:** top 5% of mature, filter-passing posts by `cr_bmk_shrunk` within follower tier, with `baseline_ratio` ≥ 1. Hype-flagged and rigor-1 posts are excluded, no author supplies more than 5%, and `curation.csv` lets a person drop entries.
- **Findings report (`outputs/reports/findings.md`):** a coverage table over the full corpus, then findings on filter-passing posts only, each with interval and sample size; Tiptree's two accounts placed on the under-2k distribution; recommendations for Martin, each generated from a lift row that passed the evidence gate. No inline lists of author handles.
- **Post templates:** one per lift row that passed the evidence gate, with no target count. Each has a hook pattern, evidence slot, visual spec, call-to-action placement, measured lift and three linked examples, and passes the hype lint. Ideas that did not pass may enter the experiment, labelled untested.
- **Static overview:** `outputs/reports/overview.html` extended with tier views, the archetype by visual-type lift heatmap, the swipe file and the Tiptree scorecard. A Streamlit dashboard is reconsidered after the experiment.

## Posting experiment

Correlations in the corpus suggest templates; only Tiptree posting them shows whether they work for Tiptree.

- **Accounts:** `@tiptreesystems` and `@martincsweiss1`, about 3 posts a week between them.
- **Arms:** template posts from milestone 4 against Martin's usual posts. One arm uses Lacuna maps, since the corpus has too few map posts to benchmark them.
- **Assignment:** a coin flip decides which posting slot gets a template, so topic and time of day do not line up with the arm.
- **Stopping rule:** 20 posts per arm, about three months, not a fixed date.
- **Measures:** pooled `CR_bmk` per arm and `baseline_ratio` against the account's own median. Every link carries a UTM tag (`utm_source=x`, `utm_campaign=<arm>`) so signups can be attributed if web analytics becomes available.
- **Expectation:** at these view counts only large differences will show. A null result is reported as "no large effect", not "no effect".
- **Needs:** Martin's agreement to the cadence.

## Hypothesis tests

The hypotheses (H1–H5) and open questions live in `notes/10_project_doc.md`. Their tests, E1–E7, are in `notes/40_experiments/`, which also holds the estimator (stratified rate ratio), evidence gate, verdict rule and run ledger. They run in milestone 4 on milestone 1–3 outputs, plus the paper panel (decision 29) and two new labels (decision 30). Levers that E2 and E4 support become the template arm of the posting experiment, the only causal test.

## Milestones

| # | Milestone | Needs | Done when |
|---|---|---|---|
| 0 | Scaffold | Nothing | Done |
| 1 | Handle list and collection within the $10 cap: candidate pool, Jev admission, Ben's review of 75 candidates, quota sampling, monthly `OR`-batched collection of `ROSTER`, `OWN` and `BENCHMARK`, then the paper panel (first batch of 30 papers, then the rest), v0 raw files moved to `data/raw/_v0/` | Item G | Admission review passed; coverage table per cohort and tier meets the quotas; first-batch checks for E, F and the panel recorded here; 10 posts spot-checked against X |
| 2 | Baselines: trailing author medians, per-author cap, shrunk `CR_bmk`, reach fit | Milestone 1 | Sanity table per tier reviewed; MVP and sanity reports regenerated on new data without stale text |
| 3 | Labels v2: audience rubric, 200-post hand-labelled set (with `framing`), 100 paper-linked posts for `poster_role`, taxonomy revision, relabel, agreement report | Milestone 1 | Held-out targets met and the corpus labelled |
| 4 | Analysis: lift tables, swipe file, findings, templates, hypothesis tests E1–E7 | Milestones 2–3 | Every number in the findings traces to a lift row or a ledger row |
| 5 | Posting experiment | Milestone 4, Martin's agreement | 20 posts per arm; result written up |
| 6 | Static overview extended; dashboard reconsidered | Milestone 4 | Overview runs on real data and matches the report |
| 7 | Weekly refresh (optional) | Milestone 6 | A refresh adds a week without re-collecting old posts |

## Risks

- **Association, not cause.** Lifts are correlations. The experiment is the real test, and it can only detect large effects.
- **Handle-list bias.** Public lists favour visible accounts and the v0 seeds were found through a viral post. Tier quotas limit this; the sources and admission counts are reported in the findings.
- **Unvalidated labels.** Until milestone 3, every archetype, rigor and filter label is Jev's alone.
- **Scraping route** risks are listed under Data source.

## After V0

Ideas kept for after the posting experiment. None of them feeds a recommendation in V0.

- **Embedding map (Ben, 2026-11-14; built 2026-11-17).** Embed each post (text via `BAAI/bge-small-en-v1.5`, plus cached photos blended with CLIP `Qdrant/clip-ViT-B-32` -> 50D PCA), project to 2D with UMAP and t-SNE (`src/analysis/embed_map.py` -> `outputs/reports/embedding_map.html`, plus the 1D embedding × reach skyline `outputs/reports/embedding_impression_map.html`), and colour points by `hook_archetype`, `framing`, `poster_role`, follower tier, `cr_bmk_shrunk`, and `visual_type`. Use it to see where high-intent posts sit, whether the label classes form regions, and where Tiptree's own posts fall. It is a picture for generating hypotheses only (`D9`); any pattern it shows is tested through a pre-registered experiment before it becomes advice.

## Out of scope for V0

Unsupervised clustering (the embedding map is listed under After V0), judging reply quality (replies are counted, not read), automated posting, the Streamlit dashboard (until after the experiment), and platforms other than X.
